import os
import pymysql

MYSQL_CONF = {
    "host":     os.environ["MYSQL_HOST"],
    "port":     int(os.environ["MYSQL_PORT"]),
    "user":     os.environ["MYSQL_USER"],
    "password": os.environ["MYSQL_PASSWORD"],
    "charset":  "utf8mb4",
}


def get_conn(db):
    return pymysql.connect(database=db, **MYSQL_CONF)


def load_mart(dt_str: str):
    """
    staging.electricity + staging.weather → mart.hourly (시각 단위 1건)
    dt_str: "YYYY-MM-DD HH:00:00"
    """
    sql_join = """
        SELECT
            e.dt,
            e.demand_mw,
            w.temperature,
            w.humidity,
            w.wind_speed,
            w.precipitation
        FROM etl_staging.electricity e
        INNER JOIN etl_staging.weather w ON e.dt = w.dt
        WHERE e.dt = %s
    """

    stg_conn = get_conn("etl_staging")
    try:
        with stg_conn.cursor() as cur:
            cur.execute(sql_join, (dt_str,))
            row = cur.fetchone()
    finally:
        stg_conn.close()

    if not row:
        print(f"[load_mart] {dt_str} JOIN 결과 없음")
        return

    mart_conn = get_conn("etl_mart")
    try:
        with mart_conn.cursor() as cur:
            sql_insert = """
                INSERT INTO hourly
                    (dt, demand_mw, temperature, humidity, wind_speed, precipitation)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    demand_mw     = VALUES(demand_mw),
                    temperature   = VALUES(temperature),
                    humidity      = VALUES(humidity),
                    wind_speed    = VALUES(wind_speed),
                    precipitation = VALUES(precipitation)
            """
            cur.execute(sql_insert, row)
        mart_conn.commit()
        print(f"[load_mart] {dt_str} mart 적재 완료")
    finally:
        mart_conn.close()


if __name__ == "__main__":
    from datetime import datetime
    dt_str = datetime.now().replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
    load_mart(dt_str)
