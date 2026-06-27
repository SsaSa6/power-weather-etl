import requests
import json
from datetime import datetime, timedelta

API_KEY = "13388502bd5c89fc8a99c218e30557e8398d3ce02d3705e3db0ef95ed3038100"
STATION_ID = "108"

yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

url = "http://apis.data.go.kr/1360000/AsosHourlyInfoService/getWthrDataList"
params = {
    "serviceKey": API_KEY,
    "pageNo": "1",
    "numOfRows": "3",
    "dataType": "JSON",
    "dataCd": "ASOS",
    "dateCd": "HR",
    "startDt": yesterday,
    "startHh": "10",
    "endDt": yesterday,
    "endHh": "12",
    "stnIds": STATION_ID,
}

resp = requests.get(url, params=params)
print(f"Status: {resp.status_code}")
print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
