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


def transform_electricity(dt_str: str):
    """
    raw.electricity → staging.electricity
    KPX 실시간 API: currPwrTot(현재수요) 추출 → 1건 저장
    dt_str: "YYYY-MM-DD HH:00:00"
    """
    raw_conn = get_conn("etl_raw")
    try:
        with raw_conn.cursor() as cur:
            cur.execute(
                "SELECT raw_json FROM electricity WHERE observed_at = %s",
                (dt_str,)
            )
            row = cur.fetchone()
    finally:
        raw_conn.close()

    if row is None:
        print(f"[transform_electricity] {dt_str} raw 데이터 없음")
        return

    data      = json.loads(row[0])
    demand_mw = int(float(data.get("currPwrTot", 0)))

    stg_conn = get_conn("etl_staging")
    try:
        with stg_conn.cursor() as cur:
            sql = """
                INSERT INTO electricity (dt, demand_mw)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE demand_mw = VALUES(demand_mw)
            """
            cur.execute(sql, (dt_str, demand_mw))
        stg_conn.commit()
        print(f"[transform_electricity] {dt_str} demand_mw={demand_mw} 저장 완료")
    finally:
        stg_conn.close()


def transform_weather(dt_str: str):
    """
    raw.weather → staging.weather
    특정 시각 1건: 기온·습도·풍속·강수량 추출
    dt_str: "YYYY-MM-DD HH:00:00"
    """
    raw_conn = get_conn("etl_raw")
    try:
        with raw_conn.cursor() as cur:
            cur.execute(
                "SELECT observed_at, station_id, raw_json FROM weather "
                "WHERE observed_at = %s",
                (dt_str,)
            )
            row = cur.fetchone()
    finally:
        raw_conn.close()

    if row is None:
        print(f"[transform_weather] {dt_str} raw 데이터 없음")
        return

    observed_at, station_id, raw_json = row
    r = json.loads(raw_json)

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
            cur.execute(sql, (
                observed_at,
                station_id,
                to_decimal(r.get("ta")),
                to_decimal(r.get("hm")),
                to_decimal(r.get("ws")),
                to_decimal(r.get("rn"), 0.0),
            ))
        stg_conn.commit()
        print(f"[transform_weather] {dt_str} 저장 완료")
    finally:
        stg_conn.close()


def transform(dt_str: str):
    transform_electricity(dt_str)
    transform_weather(dt_str)


if __name__ == "__main__":
    from datetime import datetime
    dt_str = datetime.now().replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
    transform(dt_str)
