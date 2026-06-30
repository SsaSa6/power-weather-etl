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


def validate_staging_electricity(dt_str: str) -> bool:
    """
    staging.electricity 검증 (시각 단위)
    - 해당 시각 1건 존재 여부
    - 수요량 범위 (10,000 ~ 150,000 MW — 전국 수요 기준)
    dt_str: "YYYY-MM-DD HH:00:00"
    """
    conn = get_conn("etl_staging")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT demand_mw FROM electricity WHERE dt = %s",
                (dt_str,)
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        print(f"[validate2_electricity] {dt_str} ❌ 데이터 없음")
        return False

    demand = row[0]

    if demand < 10000:
        print(f"[validate2_electricity] {dt_str} ❌ 수요량 너무 낮음: {demand} MW")
        return False

    if demand > 150000:
        print(f"[validate2_electricity] {dt_str} ❌ 수요량 너무 높음: {demand} MW")
        return False

    print(f"[validate2_electricity] {dt_str} ✅ 통과 (수요: {demand} MW)")
    return True


def validate_staging_weather(dt_str: str) -> bool:
    """
    staging.weather 검증 (시각 단위)
    - 해당 시각 1건 존재 여부
    - 기온 범위 (-50 ~ 50°C), 습도 범위 (0 ~ 100%)
    dt_str: "YYYY-MM-DD HH:00:00"
    """
    conn = get_conn("etl_staging")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT temperature, humidity FROM weather WHERE dt = %s",
                (dt_str,)
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        print(f"[validate2_weather] {dt_str} ❌ 데이터 없음")
        return False

    temperature, humidity = row
    issues = []

    if temperature is not None and not (-50 <= float(temperature) <= 50):
        issues.append(f"기온 범위 이상: {temperature}°C")

    if humidity is not None and not (0 <= float(humidity) <= 100):
        issues.append(f"습도 범위 이상: {humidity}%")

    if issues:
        for issue in issues:
            print(f"[validate2_weather] {dt_str} ❌ {issue}")
        return False

    print(f"[validate2_weather] {dt_str} ✅ 통과 (기온: {temperature}°C, 습도: {humidity}%)")
    return True


def validate_staging_join(dt_str: str) -> bool:
    """
    교차 검증 — 해당 시각에 전력/날씨 둘 다 존재하는지 확인
    dt_str: "YYYY-MM-DD HH:00:00"
    """
    conn = get_conn("etl_staging")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM electricity WHERE dt = %s", (dt_str,))
            elec_cnt = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM weather WHERE dt = %s", (dt_str,))
            weather_cnt = cur.fetchone()[0]
    finally:
        conn.close()

    if elec_cnt == 0:
        print(f"[validate2_join] {dt_str} ❌ staging 전력 없음")
        return False

    if weather_cnt == 0:
        print(f"[validate2_join] {dt_str} ❌ staging 날씨 없음")
        return False

    print(f"[validate2_join] {dt_str} ✅ 전력·날씨 모두 존재 → mart JOIN 가능")
    return True


def validate_staging(dt_str: str) -> bool:
    """품질 검증 2 — staging 전체 검증"""
    elec_ok    = validate_staging_electricity(dt_str)
    weather_ok = validate_staging_weather(dt_str)
    join_ok    = validate_staging_join(dt_str)
    return elec_ok and weather_ok and join_ok


if __name__ == "__main__":
    from datetime import datetime
    dt_str = datetime.now().replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
    validate_staging(dt_str)
