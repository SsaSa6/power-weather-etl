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
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2023, 12, 31),
    schedule_interval="@daily",
    catchup=False,  # True로 바꾸면 2023년 전체 자동 처리
    tags=["etl", "power", "weather"],
) as dag:

    def _extract_electricity(**ctx):
        extract_electricity(ctx["ds"])

    def _extract_weather(**ctx):
        extract_weather(ctx["ds"])

    def _validate_raw(**ctx):
        if not validate_raw(ctx["ds"]):
            raise ValueError(f"품질 검증 1 실패: {ctx['ds']}")

    def _transform_electricity(**ctx):
        transform_electricity(ctx["ds"])

    def _transform_weather(**ctx):
        transform_weather(ctx["ds"])

    def _validate_staging(**ctx):
        if not validate_staging(ctx["ds"]):
            raise ValueError(f"품질 검증 2 실패: {ctx['ds']}")

    def _load_mart(**ctx):
        load_mart(ctx["ds"])

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
