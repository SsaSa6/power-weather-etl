import json
import os
import pymysql
from datetime import datetime

MYSQL_CONF = {
    "host":     os.environ["MYSQL_HOST"],
    "port":     int(os.environ["MYSQL_PORT"]),
    "user":     os.environ["MYSQL_USER"],
    "password": os.environ["MYSQL_PASSWORD"],
    "charset":  "utf8mb4",
}


def get_conn(db):
    return pymysql.connect(database=db, **MYSQL_CONF)


def to_decimal(value, default=None):
    """빈 문자열·None → None(NULL). 강수량처럼 기본값 필요한 경우 default 사용"""
    if value is None or str(value).strip() == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def transform_electricity(date_str: str):
    """
    raw.electricity → staging.electricity
    1일 1행(wide) → 23행(long) 피벗
    1시~23시만 사용 (날씨 데이터가 23시까지라 24시 제외)
    """
    raw_conn = get_conn("etl_raw")
    try:
        with raw_conn.cursor() as cur:
            cur.execute("SELECT raw_json FROM electricity WHERE date = %s", (date_str,))
            row = cur.fetchone()
    finally:
        raw_conn.close()

    if row is None:
        print(f"[transform_electricity] {date_str} raw 데이터 없음")
        return

    data = json.loads(row[0])

    rows = []
    for h in range(1, 24):  # 1시~23시
        col = f"{h}시"
        if col not in data:
            continue
        dt = datetime.strptime(f"{date_str} {h:02d}:00:00", "%Y-%m-%d %H:%M:%S")
        rows.append((dt, int(data[col])))

    stg_conn = get_conn("etl_staging")
    try:
        with stg_conn.cursor() as cur:
            sql = """
                INSERT INTO electricity (dt, demand_mw)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE demand_mw = VALUES(demand_mw)
            """
            cur.executemany(sql, rows)
        stg_conn.commit()
        print(f"[transform_electricity] {date_str} {len(rows)}건 저장 완료")
    finally:
        stg_conn.close()


def transform_weather(date_str: str):
    """
    raw.weather → staging.weather
    - JSON에서 기온·습도·풍속·강수량만 추출
    - 빈 문자열 → None(NULL), 강수량 빈 값 → 0.0
    """
    raw_conn = get_conn("etl_raw")
    try:
        with raw_conn.cursor() as cur:
            cur.execute(
                "SELECT observed_at, station_id, raw_json FROM weather "
                "WHERE DATE(observed_at) = %s",
                (date_str,)
            )
            rows = cur.fetchall()
    finally:
        raw_conn.close()

    if not rows:
        print(f"[transform_weather] {date_str} raw 데이터 없음")
        return

    staging_rows = []
    for observed_at, station_id, raw_json in rows:
        r = json.loads(raw_json)
        staging_rows.append((
            observed_at,
            station_id,
            to_decimal(r.get("ta")),       # 기온(°C)
            to_decimal(r.get("hm")),       # 습도(%)
            to_decimal(r.get("ws")),       # 풍속(m/s)
            to_decimal(r.get("rn"), 0.0),  # 강수량(mm) — 비 없으면 0.0
        ))

    stg_conn = get_conn("etl_staging")
    try:
        with stg_conn.cursor() as cur:
            sql = """
                INSERT INTO weather (dt, station_id, temperature, humidity, wind_speed, precipitation)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    temperature   = VALUES(temperature),
                    humidity      = VALUES(humidity),
                    wind_speed    = VALUES(wind_speed),
                    precipitation = VALUES(precipitation)
            """
            cur.executemany(sql, staging_rows)
        stg_conn.commit()
        print(f"[transform_weather] {date_str} {len(staging_rows)}건 저장 완료")
    finally:
        stg_conn.close()


def transform(date_str: str):
    """staging Transform 실행"""
    transform_electricity(date_str)
    transform_weather(date_str)


if __name__ == "__main__":
    transform("2023-01-02")
