import requests
import json

API_KEY = "13388502bd5c89fc8a99c218e30557e8398d3ce02d3705e3db0ef95ed3038100"

# ODCloud API - 한국전력거래소_시간별 전국 전력수요량
# UDDI 중 가장 최근 데이터로 테스트
UDDI = "uddi:e0894814-0822-4a76-9558-e035f905fe7f"

url = f"https://api.odcloud.kr/api/15065266/v1/{UDDI}"
params = {
    "page": 1,
    "perPage": 5,
    "returnType": "JSON",
    "serviceKey": API_KEY,
}

resp = requests.get(url, params=params)
print(f"Status: {resp.status_code}")
print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
