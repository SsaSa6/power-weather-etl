-- =============================================
-- RAW 레이어: API 응답 원본 그대로 저장
-- =============================================

-- 전력: 1행 = 1일 (API 응답 그대로, JSON 보존)
CREATE TABLE IF NOT EXISTS etl_raw.electricity (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date         DATE      NOT NULL,
    raw_json     JSON      NOT NULL,
    UNIQUE KEY uq_date (date)
);

-- 날씨: 1행 = 1시간 (API 응답 주요 필드 + JSON 보존)
CREATE TABLE IF NOT EXISTS etl_raw.weather (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    observed_at  DATETIME  NOT NULL,
    station_id   VARCHAR(10) NOT NULL,
    raw_json     JSON      NOT NULL,
    UNIQUE KEY uq_obs (observed_at, station_id)
);


-- =============================================
-- STAGING 레이어: 정제 + 타입 통일
-- =============================================

-- 전력: 피벗 완료 (1행 = 1시간)
CREATE TABLE IF NOT EXISTS etl_staging.electricity (
    id        BIGINT AUTO_INCREMENT PRIMARY KEY,
    dt        DATETIME NOT NULL,
    demand_mw INT      NOT NULL,
    UNIQUE KEY uq_dt (dt)
);

-- 날씨: 필요한 컬럼만, 타입 정제
CREATE TABLE IF NOT EXISTS etl_staging.weather (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    dt            DATETIME       NOT NULL,
    station_id    VARCHAR(10)    NOT NULL,
    temperature   DECIMAL(5,1),
    humidity      DECIMAL(5,1),
    wind_speed    DECIMAL(5,1),
    precipitation DECIMAL(5,1),
    UNIQUE KEY uq_dt_stn (dt, station_id)
);


-- =============================================
-- MART 레이어: 전력 + 날씨 JOIN 통합 테이블
-- =============================================

CREATE TABLE IF NOT EXISTS etl_mart.hourly (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    dt            DATETIME       NOT NULL,
    demand_mw     INT,
    temperature   DECIMAL(5,1),
    humidity      DECIMAL(5,1),
    wind_speed    DECIMAL(5,1),
    precipitation DECIMAL(5,1),
    UNIQUE KEY uq_dt (dt)
);
