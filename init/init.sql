-- Airflow 메타데이터용 DB
CREATE DATABASE IF NOT EXISTS airflow_meta
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- ETL 파이프라인용 DB (레이어별 분리)
CREATE DATABASE IF NOT EXISTS etl_raw
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS etl_staging
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS etl_mart
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- Airflow + ETL 공통 유저 생성
CREATE USER IF NOT EXISTS 'airflow'@'%' IDENTIFIED BY 'airflow123';

GRANT ALL PRIVILEGES ON airflow_meta.* TO 'airflow'@'%';
GRANT ALL PRIVILEGES ON etl_raw.*      TO 'airflow'@'%';
GRANT ALL PRIVILEGES ON etl_staging.*  TO 'airflow'@'%';
GRANT ALL PRIVILEGES ON etl_mart.*     TO 'airflow'@'%';

FLUSH PRIVILEGES;
