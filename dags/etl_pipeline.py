from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from tasks.extract   import extract_electricity, extract_weather
from tasks.validate  import validate_raw
from tasks.transform import transform_electricity, transform_weather
from tasks.validate2 import validate_staging
from tasks.load      import load_mart

default_args = {
    "owner": "airflow",
    "retries": 1,
}

with DAG(
    dag_id="power_weather_etl",
    default_args=default_args,
    start_date=datetime(2026, 6, 30, 1, 0),  # 키 활성화 이후 시점으로 조정
    schedule_interval="@hourly",
    catchup=False,
    tags=["etl", "power", "weather"],
) as dag:

    def _get_dt_str(ctx) -> str:
        """Airflow 실행 시각을 "YYYY-MM-DD HH:00:00" 형식으로 반환"""
        return ctx["data_interval_start"].replace(minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")

    def _extract_electricity(**_):
        # KPX 실시간 API — 항상 현재 수급 데이터를 가져옴
        extract_electricity()

    def _extract_weather(**ctx):
        extract_weather(_get_dt_str(ctx))

    def _validate_raw(**ctx):
        if not validate_raw(_get_dt_str(ctx)):
            raise ValueError(f"품질 검증 1 실패: {_get_dt_str(ctx)}")

    def _transform_electricity(**ctx):
        transform_electricity(_get_dt_str(ctx))

    def _transform_weather(**ctx):
        transform_weather(_get_dt_str(ctx))

    def _validate_staging(**ctx):
        if not validate_staging(_get_dt_str(ctx)):
            raise ValueError(f"품질 검증 2 실패: {_get_dt_str(ctx)}")

    def _load_mart(**ctx):
        load_mart(_get_dt_str(ctx))

    # 태스크 정의
    t_ext_elec    = PythonOperator(task_id="extract_electricity",    python_callable=_extract_electricity)
    t_ext_weather = PythonOperator(task_id="extract_weather",        python_callable=_extract_weather)
    t_val_raw     = PythonOperator(task_id="validate_raw",           python_callable=_validate_raw)
    t_tr_elec     = PythonOperator(task_id="transform_electricity",  python_callable=_transform_electricity)
    t_tr_weather  = PythonOperator(task_id="transform_weather",      python_callable=_transform_weather)
    t_val_staging = PythonOperator(task_id="validate_staging",       python_callable=_validate_staging)
    t_load        = PythonOperator(task_id="load_mart",              python_callable=_load_mart)

    # 의존성: 추출 병렬 → 검증1 → 변환 병렬 → 검증2 → 적재
    [t_ext_elec, t_ext_weather] >> t_val_raw >> [t_tr_elec, t_tr_weather] >> t_val_staging >> t_load
