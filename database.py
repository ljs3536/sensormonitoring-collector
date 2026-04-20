# sensor-collector/database.py

import influxdb_client
from influxdb_client.client.write_api import ASYNCHRONOUS
from config import settings # config.py에서 settings 객체 불러오기!

# ==========================================
# 1. InfluxDB 클라이언트 전역 연결 (가장 먼저 실행되어야 함!)
# ==========================================
client = influxdb_client.InfluxDBClient(
    url=settings.influxdb_url,
    token=settings.influxdb_token,
    org=settings.influxdb_org
)

# ==========================================
# 2. 쓰기 및 읽기 API 객체 생성 (client 생성 이후에 위치!)
# ==========================================
write_api = client.write_api(write_options=ASYNCHRONOUS)
query_api = client.query_api()


# --- [2] 데이터 저장 함수들 ---
def save_piezo_data(sensor_id: str, voltage: float, timestamp: float, label: str = "normal"):
    point = (
        influxdb_client.Point("piezo_sensor")
        .tag("sensor_id", sensor_id)
        .tag("label", label)
        .field("voltage", voltage)
        .time(int(timestamp * 1e9))
    )
    # 🌟 settings.influxdb_bucket 사용
    write_api.write(bucket=settings.influxdb_bucket, org=settings.influxdb_org, record=point)

def save_adxl_data(sensor_id: str, x: float, y: float, z: float, timestamp: float, label: str = "normal"):
    point = (
        influxdb_client.Point("adxl_sensor")
        .tag("sensor_id", sensor_id)
        .tag("label", label)
        .field("x", x)
        .field("y", y)
        .field("z", z)
        .time(int(timestamp * 1e9))
    )
    # settings.influxdb_bucket 사용
    write_api.write(bucket=settings.influxdb_bucket, org=settings.influxdb_org, record=point)

def close_db():
    write_api.close()
    client.close()