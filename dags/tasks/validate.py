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

HOUR_COLS = [f"{h}시" for h in range(1, 25)]  # 1시~24시


def get_conn(db):
    return pymysql.connect(database=db, **MYSQL_CONF)


def validate_raw_electricity(date_str: str) -> bool:
    """
    raw.electricity 품질 검증
    - 데이터 존재 여부
    - 결측 시간 컬럼 (1시~24시)
    - 음수 수요량
    """
    conn = get_conn("etl_raw")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT raw_json FROM electricity WHERE date = %s", (date_str,))
            row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        print(f"[validate_electricity] {date_str} ❌ 데이터 없음")
        return False

    data = json.loads(row[0])
    issues = []

    # 결측 컬럼 체크
    missing_cols = [col for col in HOUR_COLS if col not in data]
    if missing_cols:
        issues.append(f"결측 시간 컬럼: {missing_cols}")

    # 음수 수요량 체크
    negative = [col for col in HOUR_COLS if col in data and data[col] < 0]
    if negative:
        issues.append(f"음수 수요량 발견: {negative}")

    if issues:
        for issue in issues:
            print(f"[validate_electricity] {date_str} ❌ {issue}")
        return False

    print(f"[validate_electricity] {date_str} ✅ 통과")
    return True


def validate_raw_weather(date_str: str) -> bool:
    """
    raw.weather 품질 검증
    - 데이터 건수 (23건 기대)
    - 시간 연속성 (01~23시 빠짐없이)
    - 기온(ta) 결측 비율 10% 초과 여부
    """
    conn = get_conn("etl_raw")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT observed_at, raw_json FROM weather "
                "WHERE DATE(observed_at) = %s ORDER BY observed_at",
                (date_str,)
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        print(f"[validate_weather] {date_str} ❌ 데이터 없음")
        return False

    issues = []
    parsed = [json.loads(r[1]) for r in rows]

    # 건수 체크
    if len(rows) < 20:
        issues.append(f"건수 부족: {len(rows)}건 (기대 23건)")

    # 시간 연속성 체크
    observed_hours = {r[0].hour for r in rows}
    missing_hours = set(range(1, 24)) - observed_hours
    if missing_hours:
        issues.append(f"누락 시간: {sorted(missing_hours)}시")

    # 기온 결측 비율 체크
    missing_ta = sum(1 for r in parsed if not str(r.get("ta", "")).strip())
    if missing_ta / len(rows) > 0.1:
        issues.append(f"기온(ta) 결측률 {missing_ta}/{len(rows)} ({missing_ta/len(rows)*100:.0f}%)")

    if issues:
        for issue in issues:
            print(f"[validate_weather] {date_str} ❌ {issue}")
        return False

    print(f"[validate_weather] {date_str} ✅ 통과 ({len(rows)}건)")
    return True


def validate_raw(date_str: str) -> bool:
    """품질 검증 1 — 전력 + 날씨 둘 다 통과해야 staging으로 진행"""
    elec_ok    = validate_raw_electricity(date_str)
    weather_ok = validate_raw_weather(date_str)
    return elec_ok and weather_ok


if __name__ == "__main__":
    validate_raw("2023-01-02")
