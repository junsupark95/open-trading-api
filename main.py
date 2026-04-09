import sys
import os
import asyncio
import logging

# [배포용 고도화] 현재 디렉토리를 Python Path에 명시적으로 추가
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from contextlib import asynccontextmanager

from trading_broker.kis_api.client import KISClient
from trading_broker.kis_api.adapters import KISAdapter
from trading_strategy.models import StrategyConfig, RiskConfig
from trading_strategy.ai_evaluator import AIEvaluator
from trading_execution.trading_engine import TradingEngine
import trading_data.db as db_module

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 환경 변수 로드
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TRADING_ENV = os.environ.get("TRADING_ENV", "vps") # vps(모의) or prod(실전)

# 프로젝트 인스턴스 초기화
kis_client = KISClient(is_paper=(TRADING_ENV == "vps"))
kis_adapter = KISAdapter(kis_client)
ai_evaluator = AIEvaluator(api_key=GEMINI_API_KEY)
strategy_cfg = StrategyConfig()
risk_cfg = RiskConfig()
engine = TradingEngine(kis_adapter, ai_evaluator, strategy_cfg, risk_cfg)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: DB 초기화 및 엔진 구동
    logger.info("🎬 NeuroTrade 시스템 초기화 중...")
    db_module.init_db()
    
    # 엔진을 백그라운드 태스크로 시작
    engine_task = asyncio.create_task(engine.start())
    
    yield
    
    # Shutdown: 엔진 정지
    engine.stop()
    engine_task.cancel()
    logger.info("🛑 NeuroTrade 시스템 종료")

app = FastAPI(title="NeuroTrade Professional AI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Endpoints ---

@app.get("/api/status")
async def get_status():
    return engine.get_status()

@app.get("/api/scans")
async def get_scans(limit: int = 15):
    with db_module.get_db() as session:
        return db_module.get_recent_scans(session, limit)

@app.get("/api/trades")
async def get_trades(limit: int = 15):
    with db_module.get_db() as session:
        return db_module.get_recent_trades(session, limit)

@app.get("/api/logs")
async def get_logs():
    try:
        # 로그 파일 경로 (기본 ai_engine.log 사용)
        log_file = 'ai_engine.log'
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                lines = f.readlines()
                return Response(content="".join(lines[-100:]), media_type="text/plain")
        return "No logs found."
    except:
        return "Error reading logs."

# React 정적 파일 서빙
if os.path.exists("web_dashboard/dist"):
    app.mount("/", StaticFiles(directory="web_dashboard/dist", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, access_log=False)
