import os
import json
import requests
import pymysql
from datetime import datetime, timedelta

API_KEY      = os.environ["ELECTRICITY_API_KEY"]
WEATHER_KEY  = os.environ["WEATHER_API_KEY"]
STATION_ID   = os.environ.get("WEATHER_STATION_ID", "108")

MYSQL_CONF = {
    "host":     os.environ["MYSQL_HOST"],
    "port":     int(os.environ["MYSQL_PORT"]),
    "user":     os.environ["MYSQL_USER"],
    "password": os.environ["MYSQL_PASSWORD"],
    "charset":  "utf8mb4",
}

ELEC_UDDI = "uddi:e0894814-0822-4a76-9558-e035f905fe7f"


def get_conn(db):
    return pymysql.connect(database=db, **MYSQL_CONF)


def extract_electricity(date_str: str):
    """
    전력거래소 API에서 특정 날짜 데이터를 가져와 etl_raw.electricity에 저장.
    date_str: "YYYY-MM-DD"
    """
    url = f"https://api.odcloud.kr/api/15065266/v1/{ELEC_UDDI}"
    params = {
        "page": 1,
        "perPage": 366,
        "returnType": "JSON",
        "serviceKey": API_KEY,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()

    rows = resp.json().get("data", [])
    target = next((r for r in rows if r.get("날짜") == date_str), None)

    if target is None:
        print(f"[extract_electricity] {date_str} 데이터 없음")
        return

    conn = get_conn("etl_raw")
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO electricity (date, raw_json)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE raw_json = VALUES(raw_json)
            """
            cur.execute(sql, (date_str, json.dumps(target, ensure_ascii=False)))
        conn.commit()
        print(f"[extract_electricity] {date_str} 저장 완료")
    finally:
        conn.close()


def extract_weather(date_str: str):
    """
    기상청 ASOS API에서 특정 날짜 시간별 데이터를 가져와 etl_raw.weather에 저장.
    date_str: "YYYY-MM-DD"
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    dt_str = dt.strftime("%Y%m%d")

    url = "http://apis.data.go.kr/1360000/AsosHourlyInfoService/getWthrDataList"
    params = {
        "serviceKey": WEATHER_KEY,
        "pageNo":     "1",
        "numOfRows":  "24",
        "dataType":   "JSON",
        "dataCd":     "ASOS",
        "dateCd":     "HR",
        "startDt":    dt_str,
        "startHh":    "01",
        "endDt":      dt_str,
        "endHh":      "23",
        "stnIds":     STATION_ID,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()

    items = (
        resp.json()
        .get("response", {})
        .get("body", {})
        .get("items", {})
        .get("item", [])
    )

    if not items:
        print(f"[extract_weather] {date_str} 데이터 없음")
        return

    conn = get_conn("etl_raw")
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO weather (observed_at, station_id, raw_json)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE raw_json = VALUES(raw_json)
            """
            rows = [
                (item["tm"], item["stnId"], json.dumps(item, ensure_ascii=False))
                for item in items
            ]
            cur.executemany(sql, rows)
        conn.commit()
        print(f"[extract_weather] {date_str} {len(rows)}건 저장 완료")
    finally:
        conn.close()


if __name__ == "__main__":
    # 테스트: 2023-01-02 데이터 수집
    extract_electricity("2023-01-02")
    extract_weather("2023-01-02")
