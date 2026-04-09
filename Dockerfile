# 1단계: 프론트엔드 빌드 (Node.js)
FROM node:20-slim AS frontend-builder
WORKDIR /app/web_dashboard
COPY web_dashboard/package*.json ./
RUN npm install
COPY web_dashboard/ ./
RUN npm run build

# 2단계: 백엔드 및 합계 (Python)
FROM python:3.10-slim
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 백엔드 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 빌드된 프론트엔드 결과물 복사
COPY --from=frontend-builder /app/web_dashboard/dist ./web_dashboard/dist

# 포트 설정
EXPOSE 8080

# 실행 명령
# 데이터베이스 보존을 위해 /data 디렉토리를 사용하는 것이 좋으나 실습에선 현재# 실행 명령어 (구조화된 main.py 실행)
CMD ["python", "main.py"]
