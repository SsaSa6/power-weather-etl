# ⚡ Power Weather ETL Pipeline

전력거래소(KPX)와 기상청(KMA) 공공 API에서 데이터를 수집해 매시간 자동으로 정제·통합하는 ETL 파이프라인입니다.

<br>

## 📌 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 목적 | 전력수요와 날씨 데이터를 자동 수집·정제·통합해 분석 가능한 형태로 적재 |
| 데이터 소스 | 전력거래소 전력수요정보 API, 기상청 ASOS 시간자료 API |
| 수집 주기 | 매시간 (Airflow 스케줄링) |
| 기간 | 2026.06 ~ 진행 중 |

<br>

## 🏗 아키텍처

```
[전력거래소 API]    [기상청 ASOS API]
        \                /
      [Extract - Python]          ← Airflow 매시간 트리거
              |
         [raw DB]                 ← 원본 그대로 저장
              |
       [품질 검증 1]               ← 결측/타입/음수/중복 체크
              |
       [staging DB]               ← 시간 정시 통일, 타입 정리
              |
       [품질 검증 2]               ← 전력↔날씨 시각 매칭, 누락 체크
              |
         [mart DB]                ← 전력 + 날씨 JOIN 통합 테이블
              |
      [Tableau 대시보드]
```

<br>

## 🛠 기술 스택

| 구분 | 기술 |
|------|------|
| 언어 | Python, SQL |
| 데이터베이스 | MySQL 8.0 |
| 오케스트레이션 | Apache Airflow 2.9 |
| 컨테이너 | Docker Compose |
| 시각화 | Tableau |

<br>

## 🗂 데이터 레이어

| 레이어 | DB | 설명 |
|--------|----|------|
| Raw | `etl_raw` | API 응답 원본 그대로 저장 (복구 기준점) |
| Staging | `etl_staging` | 시간 정시 통일, 타입 정제, 결측 처리 |
| Mart | `etl_mart` | 전력 + 날씨 시간 키로 JOIN한 통합 테이블 |

<br>

## 📁 프로젝트 구조

```
power-weather-etl/
├── docker-compose.yml       # MySQL + Airflow 컨테이너 정의
├── Dockerfile.airflow       # pymysql 포함 커스텀 Airflow 이미지
├── init/
│   └── init.sql             # DB 및 유저 초기화
├── dags/                    # Airflow DAG 파일
├── scripts/
│   └── test_weather_api.py  # API 응답 확인용 테스트 스크립트
└── .env                     # API 키, DB 접속 정보 (git 제외)
```

<br>

## 🚀 실행 방법

**1. 환경 변수 설정**

```bash
cp .env.example .env
# .env 파일에 API 키 입력
```

**2. 컨테이너 실행**

```bash
docker compose up --build -d
```

**3. Airflow UI 접속**

```
http://localhost:8080
ID: admin / PW: admin
```

<br>

## 📊 데이터 소스

| 데이터 | 제공 기관 | 항목 |
|--------|----------|------|
| 시간별 전력수요 | 전력거래소 (data.go.kr) | 수요량(MWh) |
| 시간별 날씨 | 기상청 ASOS (data.go.kr) | 기온, 습도, 풍속 |

기상청 관측소: 서울 (지점번호 108)
