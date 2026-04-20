# 1. 베이스 이미지 (M1 Pro이므로 자동으로 arm64 버전을 가져옵니다)
FROM python:3.11-slim

# 2. 필수 패키지 설치 (필요한 경우)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 3. 작업 디렉토리
WORKDIR /app

# 4. 의존성 설치 (캐시 최적화를 위해 복사 순서 유지)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 소스 복사
COPY . .

# 6. 환경 변수 기본값 설정 (쿠버네티스 배포 시 오버라이딩 가능)
ENV MQTT_BROKER_HOST="mosquitto-svc"
ENV INFLUXDB_HOST="influxdb-svc"

# 7. 실행 명령
# Collector가 단순 스크립트라면 python main.py로 실행합니다.
CMD ["python", "main.py"]