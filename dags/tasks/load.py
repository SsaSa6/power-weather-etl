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


def load_mart(date_str: str):
    """
    staging.electricity + staging.weather → mart.hourly
    dt 기준 INNER JOIN — 둘 다 있는 시각만 mart에 적재
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
        WHERE DATE(e.dt) = %s
        ORDER BY e.dt
    """

    stg_conn = get_conn("etl_staging")
    try:
        with stg_conn.cursor() as cur:
            cur.execute(sql_join, (date_str,))
            rows = cur.fetchall()
    finally:
        stg_conn.close()

    if not rows:
        print(f"[load_mart] {date_str} JOIN 결과 없음")
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
            cur.executemany(sql_insert, rows)
        mart_conn.commit()
        print(f"[load_mart] {date_str} {len(rows)}건 mart 적재 완료")
    finally:
        mart_conn.close()


if __name__ == "__main__":
    load_mart("2023-01-02")
