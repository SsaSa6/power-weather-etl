import os
import json
import requests
import pymysql
from datetime import datetime

API_KEY      = os.environ["ELECTRICITY_API_KEY"]
WEATHER_KEY  = os.environ["WEATHER_API_KEY"]
STATION_ID   = os.environ.get("WEATHER_STATION_ID", "108")
ELEC_RT_URL  = os.environ.get(
    "ELECTRICITY_RT_URL",
    "https://openapi.kpx.or.kr/openapi/sukub5mToday/getSukub5mToday"
)

MYSQL_CONF = {
    "host":     os.environ["MYSQL_HOST"],
    "port":     int(os.environ["MYSQL_PORT"]),
    "user":     os.environ["MYSQL_USER"],
    "password": os.environ["MYSQL_PASSWORD"],
    "charset":  "utf8mb4",
}


def get_conn(db):
    return pymysql.connect(database=db, **MYSQL_CONF)


def extract_electricity():
    """
    전력거래소 실시간 수급 API 호출 → etl_raw.electricity 저장
    baseDatetime을 정시로 내림(floor)해서 observed_at에 저장
    """
    params = {"ServiceKey": API_KEY, "type": "json"}
    resp = requests.get(ELEC_RT_URL, params=params, timeout=30)
    resp.raise_for_status()

    body  = resp.json().get("response", {}).get("body", {})
    items = body.get("items", {}).get("item", [])

    if not items:
        print("[extract_electricity] 데이터 없음")
        return

    item    = items[0] if isinstance(items, list) else items
    base_dt = item.get("baseDatetime", "")

    if not base_dt:
        print("[extract_electricity] baseDatetime 없음")
        return

    # "202601011205" (년월일시분) → 정시로 내림
    dt          = datetime.strptime(base_dt[:12], "%Y%m%d%H%M")
    observed_at = dt.replace(minute=0, second=0)

    conn = get_conn("etl_raw")
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO electricity (observed_at, raw_json)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE raw_json = VALUES(raw_json)
            """
            cur.execute(sql, (observed_at, json.dumps(item, ensure_ascii=False)))
        conn.commit()
        print(f"[extract_electricity] {observed_at} 저장 완료 (수요: {item.get('currPwrTot')} MW)")
    finally:
        conn.close()


def extract_weather(dt_str: str):
    """
    기상청 ASOS API에서 특정 시각의 날씨 데이터를 가져와 etl_raw.weather에 저장.
    dt_str: "YYYY-MM-DD HH:00:00"
    """
    dt       = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    date_str = dt.strftime("%Y%m%d")
    hour_str = dt.strftime("%H")

    url = "http://apis.data.go.kr/1360000/AsosHourlyInfoService/getWthrDataList"
    params = {
        "serviceKey": WEATHER_KEY,
        "pageNo":     "1",
        "numOfRows":  "1",
        "dataType":   "JSON",
        "dataCd":     "ASOS",
        "dateCd":     "HR",
        "startDt":    date_str,
        "startHh":    hour_str,
        "endDt":      date_str,
        "endHh":      hour_str,
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
    if isinstance(items, dict):
        items = [items]

    if not items:
        print(f"[extract_weather] {dt_str} 데이터 없음")
        return

    item = items[0]
    conn = get_conn("etl_raw")
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO weather (observed_at, station_id, raw_json)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE raw_json = VALUES(raw_json)
            """
            cur.execute(sql, (item["tm"], item["stnId"], json.dumps(item, ensure_ascii=False)))
        conn.commit()
        print(f"[extract_weather] {dt_str} 저장 완료")
    finally:
        conn.close()


if __name__ == "__main__":
    extract_electricity()
