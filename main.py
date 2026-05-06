import json
import time
import paho.mqtt.client as mqtt
from config import settings
from database import save_piezo_data, save_adxl_data # InfluxDB 저장 함수들
import numpy as np
from database_rdb import save_fft_to_rdb # 새로 만든 RDB 저장 함수

MQTT_TOPIC = "sensor/data"

# 기존에 있던 파싱 함수 그대로 가져오기
def parse_samples(hex_str: str):
    samples = []
    for i in range(0, len(hex_str), 4):
        chunk = hex_str[i:i+4]
        if len(chunk) != 4: continue
        value = int(chunk, 16)
        if value >= 0x8000: value -= 0x10000
        samples.append(value)
    return samples

# FFT 변환 및 파이프 문자열 생성 함수
def process_fft_and_format(real_vals):
    # 1. 실수형 1D 배열을 FFT 변환 (rfft는 실수 입력에 최적화됨)
    fft_result = np.abs(np.fft.rfft(real_vals))
    
    # [중요 포인트] 기존 AI 모델이 기대하는 배열 길이(Dimension)나 
    # 특정 주파수 대역(예: 25kHz~88kHz)이 있다면 여기서 슬라이싱을 해야 합니다.
    # 예시: fft_result = fft_result[start_index:end_index]
    
    # 2. 소수점 8자리까지 표현하여 파이프(|)로 연결
    str_data = "|".join([f"{val:.8f}" for val in fft_result])
    return str_data

# MQTT 메시지를 받을 때 실행되는 콜백 함수 (오직 저장만!)
def on_message(client, userdata, msg):
    try:
        raw_payload = json.loads(msg.payload.decode('utf-8'))
        sensor_type = raw_payload.get("sensor")
        sensor_id = raw_payload.get("sensor_id")
        hex_data = raw_payload.get("hex_data")
        ts = raw_payload.get("timestamp", time.time())
        label = raw_payload.get("label", "normal") 

        # RDB 저장을 위한 추가 메타데이터 (Payload에 없으면 기본값 사용)
        battery = str(raw_payload.get("battery", "100"))
        leak_yn = "Y" if label == "leak" else "N"

        if not hex_data: return
        samples = parse_samples(hex_data)

        if sensor_type == "piezo":
            time_step = 1.0 / len(samples) if len(samples) > 0 else 0
            real_vals = [round(val / 1000.0, 4) for val in samples]

            for i, real_val in enumerate(real_vals):
                current_ts = ts + (i * time_step)
                # 웹소켓이나 deque 로직 없이 바로 InfluxDB로 직행!
                save_piezo_data(sensor_id, real_val, current_ts, label) 

            # 3. FFT 변환 및 통문자열 생성
            fft_string = process_fft_and_format(real_vals)
            
            # 4. RDB 저장 (AI 모델용 데이터)
            save_fft_to_rdb(
                mac_addr=sensor_id,
                sensor_data_str=fft_string,
                battery=battery,
                leak_prob="0", # 수집 단계이므로 초기값 세팅, AI 추론 후 업데이트 됨
                leak_yn=leak_yn
            )
                
        elif sensor_type == "adxl":
            num_records = len(samples) // 3
            time_step = 1.0 / num_records if num_records > 0 else 0
            for i in range(0, len(samples), 3):
                if i+2 >= len(samples): break
                x_val = round(samples[i]/1000.0, 4)
                y_val = round(samples[i+1]/1000.0, 4)
                z_val = round(samples[i+2]/1000.0, 4)
                current_ts = ts + ((i//3) * time_step)
                
                # 웹소켓이나 deque 로직 없이 바로 InfluxDB로 직행!
                save_adxl_data(sensor_id, x_val, y_val, z_val, current_ts, label)

    except Exception as e:
        print(f"❌ 콜렉터 데이터 저장 에러: {e}")

def main():
    print("🚀 Sensor Collector 시작됨... InfluxDB 저장 대기 중")
    
    # MQTT 클라이언트 설정 (Backend와 다른 고유한 client_id를 써야 합니다)
    mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id="Data_Collector_Worker")
    
    # 연결 성공 시 구독
    mqtt_client.on_connect = lambda c, u, f, r, p: c.subscribe(MQTT_TOPIC) if r==0 else None
    mqtt_client.on_message = on_message
    
    # 브로커 연결
    mqtt_client.connect(settings.mqtt_broker, settings.mqtt_port)
    
    # FastAPI 없이 단독으로 실행되므로 무한 루프(loop_forever)를 돌립니다.
    mqtt_client.loop_forever()

if __name__ == "__main__":
    main()