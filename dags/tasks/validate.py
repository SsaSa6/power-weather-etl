import json
import os
import pymysql

MYSQL_CONF = {
    "host":     os.environ["MYSQL_HOST"],
    "port":     int(os.environ["MYSQL_PORT"]),
    "user":     os.environ["MYSQL_USER"],
    "password": os.environ["MYSQL_PASSWORD"],
    "charset":  "utf8mb4",
}


def get_conn(db):
    return pymysql.connect(database=db, **MYSQL_CONF)


def validate_raw_electricity(dt_str: str) -> bool:
    """
    raw.electricity 품질 검증 (실시간 API 기준)
    - 해당 시각 데이터 존재 여부
    - currPwrTot 값이 0 이상
    dt_str: "YYYY-MM-DD HH:00:00"
    """
    conn = get_conn("etl_raw")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT raw_json FROM electricity WHERE observed_at = %s",
                (dt_str,)
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        print(f"[validate_electricity] {dt_str} ❌ 데이터 없음")
        return False

    data      = json.loads(row[0])
    curr_load = data.get("currPwrTot")

    if curr_load is None:
        print(f"[validate_electricity] {dt_str} ❌ currPwrTot 없음")
        return False

    if float(curr_load) <= 0:
        print(f"[validate_electricity] {dt_str} ❌ 수요량 이상값: {curr_load}")
        return False

    print(f"[validate_electricity] {dt_str} ✅ 통과 (수요: {curr_load} MW)")
    return True


def validate_raw_weather(dt_str: str) -> bool:
    """
    raw.weather 품질 검증
    - 해당 시각 데이터 존재 여부
    - 기온(ta) 값 존재 여부
    dt_str: "YYYY-MM-DD HH:00:00"
    """
    conn = get_conn("etl_raw")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT raw_json FROM weather WHERE observed_at = %s",
                (dt_str,)
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        print(f"[validate_weather] {dt_str} ❌ 데이터 없음")
        return False

    data = json.loads(row[0])
    ta   = str(data.get("ta", "")).strip()

    if not ta:
        print(f"[validate_weather] {dt_str} ⚠️ 기온(ta) 결측 — 계속 진행")

    print(f"[validate_weather] {dt_str} ✅ 통과 (기온: {ta or 'N/A'}°C)")
    return True


def validate_raw(dt_str: str) -> bool:
    """품질 검증 1 — 전력 + 날씨 둘 다 통과해야 staging으로 진행"""
    elec_ok    = validate_raw_electricity(dt_str)
    weather_ok = validate_raw_weather(dt_str)
    return elec_ok and weather_ok


if __name__ == "__main__":
    from datetime import datetime
    dt_str = datetime.now().replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
    validate_raw(dt_str)
