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


def validate_staging_electricity(date_str: str) -> bool:
    """
    staging.electricity 검증
    - 23건 존재 여부
    - 수요량 범위 (10,000 ~ 150,000 MWh — 전국 수요 기준)
    """
    conn = get_conn("etl_staging")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*), MIN(demand_mw), MAX(demand_mw) "
                "FROM electricity WHERE DATE(dt) = %s",
                (date_str,)
            )
            count, min_val, max_val = cur.fetchone()
    finally:
        conn.close()

    issues = []

    if count == 0:
        print(f"[validate2_electricity] {date_str} ❌ 데이터 없음")
        return False

    if count < 23:
        issues.append(f"건수 부족: {count}건 (기대 23건)")

    if min_val is not None and min_val < 10000:
        issues.append(f"수요량 너무 낮음: 최솟값 {min_val} MWh")

    if max_val is not None and max_val > 150000:
        issues.append(f"수요량 너무 높음: 최댓값 {max_val} MWh")

    if issues:
        for issue in issues:
            print(f"[validate2_electricity] {date_str} ❌ {issue}")
        return False

    print(f"[validate2_electricity] {date_str} ✅ 통과 ({count}건, {min_val}~{max_val} MWh)")
    return True


def validate_staging_weather(date_str: str) -> bool:
    """
    staging.weather 검증
    - 23건 존재 여부
    - 기온 범위 (-50 ~ 50°C)
    - 습도 범위 (0 ~ 100%)
    """
    conn = get_conn("etl_staging")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*), MIN(temperature), MAX(temperature), "
                "MIN(humidity), MAX(humidity) "
                "FROM weather WHERE DATE(dt) = %s",
                (date_str,)
            )
            count, min_t, max_t, min_h, max_h = cur.fetchone()
    finally:
        conn.close()

    issues = []

    if count == 0:
        print(f"[validate2_weather] {date_str} ❌ 데이터 없음")
        return False

    if count < 23:
        issues.append(f"건수 부족: {count}건 (기대 23건)")

    if min_t is not None and not (-50 <= float(min_t) <= 50):
        issues.append(f"기온 범위 이상: {min_t}°C")

    if max_t is not None and not (-50 <= float(max_t) <= 50):
        issues.append(f"기온 범위 이상: {max_t}°C")

    if min_h is not None and float(min_h) < 0:
        issues.append(f"습도 음수: {min_h}%")

    if max_h is not None and float(max_h) > 100:
        issues.append(f"습도 100% 초과: {max_h}%")

    if issues:
        for issue in issues:
            print(f"[validate2_weather] {date_str} ❌ {issue}")
        return False

    print(f"[validate2_weather] {date_str} ✅ 통과 ({count}건, 기온 {min_t}~{max_t}°C)")
    return True


def validate_staging_join(date_str: str) -> bool:
    """
    교차 검증 — 전력과 날씨 시각(dt)이 일치하는지 확인
    매칭 안 되는 시각이 있으면 mart JOIN에서 누락됨
    """
    conn = get_conn("etl_staging")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT dt FROM electricity WHERE DATE(dt) = %s", (date_str,)
            )
            elec_dts = {r[0] for r in cur.fetchall()}

            cur.execute(
                "SELECT dt FROM weather WHERE DATE(dt) = %s", (date_str,)
            )
            weather_dts = {r[0] for r in cur.fetchall()}
    finally:
        conn.close()

    only_elec    = elec_dts - weather_dts
    only_weather = weather_dts - elec_dts

    if only_elec:
        print(f"[validate2_join] {date_str} ⚠️ 전력에만 있는 시각: {sorted(only_elec)}")
    if only_weather:
        print(f"[validate2_join] {date_str} ⚠️ 날씨에만 있는 시각: {sorted(only_weather)}")

    matched = len(elec_dts & weather_dts)
    print(f"[validate2_join] {date_str} ✅ 매칭 가능한 시각: {matched}건")
    return matched > 0


def validate_staging(date_str: str) -> bool:
    """품질 검증 2 — staging 전체 검증"""
    elec_ok    = validate_staging_electricity(date_str)
    weather_ok = validate_staging_weather(date_str)
    join_ok    = validate_staging_join(date_str)
    return elec_ok and weather_ok and join_ok


if __name__ == "__main__":
    validate_staging("2023-01-02")
