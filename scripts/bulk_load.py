"""
2016-01-01 ~ 2025-12-31 전체 데이터 벌크 적재 스크립트
실행: docker exec etl_airflow_scheduler python /opt/airflow/dags/../../../scripts/bulk_load.py
"""
import calendar
import json
import math
import os
import sys
import time
from datetime import date, timedelta

import pymysql
import requests

sys.path.insert(0, "/opt/airflow/dags")
from tasks.transform import transform_electricity, transform_weather
from tasks.load import load_mart

API_KEY     = os.environ["ELECTRICITY_API_KEY"]
WEATHER_KEY = os.environ["WEATHER_API_KEY"]
STATION_ID  = os.environ.get("WEATHER_STATION_ID", "108")

MYSQL_CONF = {
    "host":     os.environ["MYSQL_HOST"],
    "port":     int(os.environ["MYSQL_PORT"]),
    "user":     os.environ["MYSQL_USER"],
    "password": os.environ["MYSQL_PASSWORD"],
    "charset":  "utf8mb4",
}

# 연도별 UDDI 매핑 (시작일, 종료일, uddi)
UDDI_RANGES = [
    ("2016-01-01", "2020-12-31", "uddi:2fdba185-7174-4b2a-b324-acdeab2ee056"),
    ("2021-01-01", "2021-12-31", "uddi:c84898e7-9f0d-43cb-8b48-9c46cfd44b5f"),
    ("2022-01-01", "2022-12-31", "uddi:3d65661c-ebab-4e63-ace7-e6f41b826d00"),
    ("2023-01-01", "2023-12-31", "uddi:e0894814-0822-4a76-9558-e035f905fe7f"),
    ("2024-01-01", "2024-12-31", "uddi:159ec977-0b24-4550-9308-bc5c851804f2"),
    ("2025-01-01", "2025-12-31", "uddi:6ade08d2-0014-4d22-b10c-c811e3273c70"),
]

START_DATE = date(2016, 1, 1)
END_DATE   = date(2025, 12, 31)


def get_conn(db):
    return pymysql.connect(database=db, **MYSQL_CONF)


# ──────────────────────────────────────────
# STEP 1: 전력 raw 적재
# ──────────────────────────────────────────
def load_electricity_raw():
    print("\n[STEP 1] 전력 raw 적재 시작")
    conn = get_conn("etl_raw")
    total = 0

    for start_str, end_str, uddi in UDDI_RANGES:
        url = f"https://api.odcloud.kr/api/15065266/v1/{uddi}"
        per_page = 400
        page = 1

        while True:
            resp = requests.get(url, params={
                "page": page, "perPage": per_page,
                "returnType": "JSON", "serviceKey": API_KEY,
            }, timeout=30).json()

            rows = resp.get("data", [])
            if not rows:
                break

            # 2016-01-01 이후 데이터만 필터
            rows = [r for r in rows if r.get("날짜", "") >= "2016-01-01"]

            if rows:
                with conn.cursor() as cur:
                    sql = """
                        INSERT INTO electricity (date, raw_json)
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE raw_json = VALUES(raw_json)
                    """
                    cur.executemany(sql, [
                        (r["날짜"], json.dumps(r, ensure_ascii=False))
                        for r in rows if "날짜" in r
                    ])
                conn.commit()
                total += len(rows)

            if len(resp.get("data", [])) < per_page:
                break
            page += 1

        print(f"  {start_str[:4]}~{end_str[:4]} 완료")

    conn.close()
    print(f"[STEP 1] 전력 raw 적재 완료 — 총 {total}건")


# ──────────────────────────────────────────
# STEP 2: 날씨 raw 적재 (월별 배치)
# ──────────────────────────────────────────
def load_weather_raw():
    print("\n[STEP 2] 날씨 raw 적재 시작")
    url = "http://apis.data.go.kr/1360000/AsosHourlyInfoService/getWthrDataList"
    conn = get_conn("etl_raw")
    total = 0

    cur_year  = START_DATE.year
    cur_month = START_DATE.month

    while date(cur_year, cur_month, 1) <= END_DATE:
        _, last_day = calendar.monthrange(cur_year, cur_month)
        m_start = f"{cur_year}{cur_month:02d}01"
        m_end   = f"{cur_year}{cur_month:02d}{last_day:02d}"
        num_rows = last_day * 23 + 50  # 여유분 포함

        resp = requests.get(url, params={
            "serviceKey": WEATHER_KEY,
            "pageNo": "1", "numOfRows": str(num_rows),
            "dataType": "JSON", "dataCd": "ASOS", "dateCd": "HR",
            "startDt": m_start, "startHh": "01",
            "endDt": m_end,   "endHh": "23",
            "stnIds": STATION_ID,
        }, timeout=60).json()

        items = resp.get("response", {}).get("body", {}).get("items", {}).get("item", [])

        if items:
            with conn.cursor() as cur:
                sql = """
                    INSERT INTO weather (observed_at, station_id, raw_json)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE raw_json = VALUES(raw_json)
                """
                cur.executemany(sql, [
                    (item["tm"], item["stnId"], json.dumps(item, ensure_ascii=False))
                    for item in items
                ])
            conn.commit()
            total += len(items)

        print(f"  {cur_year}-{cur_month:02d} 완료 ({len(items)}건)")
        time.sleep(0.5)  # API 부하 방지

        cur_month += 1
        if cur_month > 12:
            cur_month = 1
            cur_year += 1

    conn.close()
    print(f"[STEP 2] 날씨 raw 적재 완료 — 총 {total}건")


# ──────────────────────────────────────────
# STEP 3 & 4: Transform + Load (날짜별 루프)
# ──────────────────────────────────────────
def transform_and_load_all():
    print("\n[STEP 3+4] Transform & Load 시작")
    cur = START_DATE
    done = 0

    while cur <= END_DATE:
        date_str = cur.strftime("%Y-%m-%d")
        transform_electricity(date_str)
        transform_weather(date_str)
        load_mart(date_str)
        done += 1

        if done % 100 == 0:
            print(f"  진행: {done}일 처리 완료 (현재: {date_str})")

        cur += timedelta(days=1)

    print(f"[STEP 3+4] 완료 — 총 {done}일 처리")


if __name__ == "__main__":
    load_electricity_raw()
    load_weather_raw()
    transform_and_load_all()
    print("\n전체 벌크 적재 완료!")
