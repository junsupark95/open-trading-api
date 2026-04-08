import sys
import os
import asyncio
import logging
import yaml
import json
import pandas as pd
from datetime import datetime, time
import pytz
from logging.handlers import RotatingFileHandler
from contextlib import asynccontextmanager

# 타임존 설정 (KST)
KST = pytz.timezone('Asia/Seoul')

# FastAPI 관련
from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
import uvicorn

# Google Gemini AI 신규 SDK 관련
from google import genai
from google.genai import types

sys.path.extend(['.', 'examples_user', 'examples_user/domestic_stock', 'examples_user/auth'])

import kis_auth as ka
from domestic_stock_functions import inquire_price, order_cash, volume_rank, inquire_balance, inquire_daily_ccld
import database
from risk_manager import check_risk_and_get_qty

# 로깅 설정 (파일 로테이션 추가)
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_file = 'ai_engine.log'
file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
file_handler.setFormatter(log_formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(log_formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# 설정 로드 통합: kis_auth에서 로드한 설정을 기반으로 Gemini/Telegram 키 추출
# kis_auth가 먼저 실행되어야 함 (ka.getEnv() 사용 가능)
_cfg = ka.getEnv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", _cfg.get("gemini_api_key"))
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", _cfg.get("telegram_token"))
ALLOWED_CHAT_ID = str(os.environ.get("TELEGRAM_CHAT_ID", _cfg.get("telegram_chat_id", "")))

if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY가 설정되지 않았습니다. 환경 변수나 kis_devlp.yaml을 확인하세요.")
    sys.exit(1)

# 제미나이 클라이언트 초기화 (신규 SDK 형식)
client = genai.Client(api_key=GEMINI_API_KEY)
GEN_MODEL = 'gemini-3.1-flash-lite-preview' # 일일 500회 무료 한도를 제공하는 최신 Lite 탑재

TRADING_ENV = os.environ.get("TRADING_ENV", "vps")

from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info(f"🚀 NeuroTrade AI 엔진 서버 시작 (환경: {TRADING_ENV})")
    if init_kis_api():
        system_status["is_running"] = True
        # 백그라운드 태스크 시작
        scan_task = asyncio.create_task(scan_and_trade_loop())
        report_task = asyncio.create_task(hourly_balance_report())
        await send_telegram_alert(f"🚀 NeuroTrade AI 엔진 서버가 시작되었습니다. (환경: {TRADING_ENV})")
        yield
        # Shutdown logic
        system_status["is_running"] = False
        scan_task.cancel()
        report_task.cancel()
        logger.info("🛑 NeuroTrade AI 엔진 서버 종료")
    else:
        logger.critical("❌ KIS API 인증 실패로 서버를 시작할 수 없습니다.")
        yield

app = FastAPI(title="NeuroTrade AI API Server", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우트 등록 후 정적 파일(React) 마운트
# /api 로 시작하는 요청은 FastAPI가 처리하고, 나머지는 React dist 서빙
@app.get("/api/status")
async def get_status():
    return system_status

@app.get("/api/scans")
async def get_scans(limit: int = 15):
    return database.get_recent_scans(limit)

@app.get("/api/trades")
async def get_trades(limit: int = 15):
    return database.get_recent_trades(limit)

@app.get("/api/logs")
async def get_logs():
    try:
        with open('ai_engine.log', 'r') as f:
            lines = f.readlines()
            return Response(content="".join(lines[-100:]), media_type="text/plain")
    except:
        return "No logs found."

# 빌드된 React 파일을 서빙 (dist 폴더가 존재할 때만)
if os.path.exists("web_dashboard/dist"):
    app.mount("/", StaticFiles(directory="web_dashboard/dist", html=True), name="static")

system_status = {
    "is_running": False,
    "market_mode": "STANDBY", # STANDBY, PRE_MARKET, ACTIVE
    "last_scan_time": None,
    "total_scans": 0,
    "total_trades": 0,
    "current_balance": 0,
    "p_l_ratio": 0.0
}

def _is_valid_trading_env(trenv) -> bool:
    required_fields = ("my_url", "my_acct", "my_prod")
    return all(hasattr(trenv, field) for field in required_fields)

def ensure_kis_auth() -> bool:
    """KIS 인증 상태를 검증하고 필요 시 재인증한다. (kis_auth.py의 내부 방어 로직 활용)"""
    try:
        if ka._ensure_trenv(): # kis_auth 내부의 자동 복구 기능 활용
            return True
        return False
    except Exception as e:
        logger.error(f"KIS 인증 검증 실패: {e}")
        return False

def init_kis_api():
    """시스템 초기화 시 KIS API 인증 및 DB 연결"""
    logger.info("KIS API 및 데이터베이스 초기화 중...")
    try:
        database.init_db()
        # ka.auth() 내부에서 이미 환경변수를 우선 참조함
        ka.auth(svr=TRADING_ENV, product="01")
        return ensure_kis_auth()
    except Exception as e:
        logger.error(f"초기화 실패: {e}")
        return False

async def send_telegram_alert(msg: str):
    if not TELEGRAM_TOKEN or not ALLOWED_CHAT_ID:
        return
    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": ALLOWED_CHAT_ID, "text": msg}
    try:
         await asyncio.to_thread(requests.post, url, json=payload)
    except Exception as e:
         logger.error(f"Telegram 전송 실패: {e}")

def get_market_mode():
    now = datetime.now(KST).time()
    if now >= time(8, 30) and now < time(9, 0):
        return "PRE_MARKET"
    elif now >= time(9, 0) and now < time(15, 30):
        return "ACTIVE"
    else:
        return "STANDBY"

# 무료 티어 관리를 위한 일일 요청 횟수 카운터
daily_ai_requests = 0
last_request_date = datetime.now(KST).date()

async def evaluate_stock_with_ai(stock_code: str, stock_name: str, price: float, vol: float, vol_ratio: str, is_pre_market=False) -> dict:
    global daily_ai_requests, last_request_date
    
    # 자정이 지나면 카운터 초기화
    current_date = datetime.now(KST).date()
    if current_date != last_request_date:
        daily_ai_requests = 0
        last_request_date = current_date
        
    # 구글 무료티어(하루 1500회) 안전선인 하루 1000회 초과 시 완전 차단
    if daily_ai_requests >= 1000:
        logger.warning("일일 AI 무료 API 호출 한도(1000회)를 초과하여 매매 판단을 보류(HOLD)합니다.")
        return {"action": "HOLD", "reason": "일일 무료 AI 호출 한도 도달로 인한 매수 보류"}

    mode_str = "장전 예상체결가" if is_pre_market else "장중 거래량 급증"
    prompt = f"""
    당신은 세계 최고의 '로스카메론(Ross Cameron)'식 모멘텀 데이트레이딩 전문가입니다.
    현재 KIS {mode_str} 스캐너에 다음 종목이 포착되었습니다.
    
    종목명: {stock_name} (코드: {stock_code})
    현재가(또는 예상가): {price}원
    거래량 증가율: {vol_ratio}%
    
    로스카메론 돌파 기법(Gap and Go, 상대거래량 폭발 등) 기준에 의거하여, 추격 매수(BUY)를 하는 것이 좋은지 관망(HOLD)하는 것이 좋은지 결정하세요.
    응답은 오직 아래 JSON 양식으로만 반환하세요.
    {{"action": "BUY" 또는 "HOLD", "reason": "이유 요약 (충분한 설명 포함)"}}
    """
    try:
        daily_ai_requests += 1 # 요청 카운트 증가
        # 신규 SDK (google-genai) 방식으로 변경
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=GEN_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json'
            )
        )
        result = json.loads(response.text)
        return result
    except Exception as e:
        logger.error(f"AI 평가 실패 ({stock_code}): {e}")
        return {"action": "HOLD", "reason": f"AI 통신 오류: {e}"}

async def verify_trade_completion(trade_id, stock_code, odno):
    if not ensure_kis_auth():
        logger.error("체결 확인 중단: KIS 인증 상태가 유효하지 않습니다.")
        return
    trenv = ka.getTREnv()
    today = datetime.now(KST).strftime("%Y%m%d")
    
    # 최대 5번, 2초 간격으로 체결 확인 (총 10초)
    for i in range(5):
        await asyncio.sleep(2)
        try:
            # inquire_daily_ccld 호출 (odno 필터링)
            df1, _ = await asyncio.to_thread(
                inquire_daily_ccld,
                env_dv="demo", pd_dv="inner", cano=trenv.my_acct, acnt_prdt_cd=trenv.my_prod,
                inqr_strt_dt=today, inqr_end_dt=today, 
                sll_buy_dvsn_cd="00", pdno=stock_code, ccld_dvsn="01", 
                inqr_dvsn="00", inqr_dvsn_3="00", odno=odno
            )
            
            if df1 is not None and not df1.empty:
                # 해당 주문번호의 체결 수량이 존재하면 완료 처리
                ccld_qty = int(df1.iloc[0]['tot_ccld_qty'])
                if ccld_qty > 0:
                    database.update_trade_status(trade_id, "SUCCESS")
                    logger.info(f"✅ [주문번호:{odno}] 체결 완료 확인!")
                    return
        except Exception as e:
            logger.error(f"체결 확인 중 에러: {e}")
            
    # 시간 초과 시에도 일단 로그는 남김 (데이터가 늦게 올라올 수 있음)
    logger.warning(f"⚠️ [주문번호:{odno}] 10초 내 체결 미확인 (지연 가능성)")

async def execute_trade(stock_code: str, stock_name: str, price: float, ai_reason: str, ord_dvsn="01"):
    if not ensure_kis_auth():
        logger.error("주문 중단: KIS 인증 상태가 유효하지 않습니다.")
        return
    trenv = ka.getTREnv()
    # 1. 먼저 DB에 PENDING 상태로 로깅 (매수중 표시)
    trade_id = database.log_trade(stock_code, stock_name, "BUY", price, 0, "PENDING", ai_reason)
    
    try:
        bal_res1, bal_res2 = await asyncio.to_thread(
            inquire_balance, env_dv="demo", cano=trenv.my_acct, acnt_prdt_cd=trenv.my_prod,
            afhr_flpr_yn="N", inqr_dvsn="01", unpr_dvsn="01", fund_sttl_icld_yn="N", 
            fncg_amt_auto_rdpt_yn="N", prcs_dvsn="00"
        )
        holdings = len(bal_res1) if not bal_res1.empty else 0
        total_balance = float(bal_res2['tot_evlu_amt'].iloc[0]) if not bal_res2.empty and 'tot_evlu_amt' in bal_res2.columns else 10000000.0
        system_status["current_balance"] = total_balance
    except Exception as e:
        logger.error(f"잔고 조회 실패: {e}")
        database.update_trade_status(trade_id, "FAILED")
        return

    buy_qty = check_risk_and_get_qty(price, total_balance, holdings)
    if buy_qty <= 0:
        logger.info(f"[{stock_name}] 리스크 관리: 매수 불가. 사유: {ai_reason}")
        database.update_trade_status(trade_id, "FAILED")
        return
        
    logger.info(f"[{stock_name}] 주문 진행 ({buy_qty}주) - 사유: {ai_reason}")
    try:
        df = await asyncio.to_thread(
            order_cash, env_dv="demo", ord_dv="buy", cano=trenv.my_acct, acnt_prdt_cd=trenv.my_prod,
            pdno=stock_code, ord_dvsn=ord_dvsn, ord_qty=str(buy_qty), ord_unpr="0", excg_id_dvsn_cd="4"
        )
        if not df.empty and 'odno' in df.columns:
            order_no = df['odno'].iloc[0]
            # DB 업데이트 (수량 및 주문번호 기록, 상태는 여전히 PENDING일 수 있음)
            # 여기서는 SUCCESS를 바로 주지 않고 비동기 체크 태스크 실행
            database.log_trade(stock_code, stock_name, "BUY", price, buy_qty, "PENDING", ai_reason, order_no)
            # 중복 제거를 위해 위에서 만든 초기 trade_id 사용 (실제로는 database.py 구조에 따라 조정)
            
            system_status["total_trades"] += 1
            msg = f"🏃 [{system_status['market_mode']}] 매수 주문 전송: {stock_name} ({buy_qty}주)"
            await send_telegram_alert(msg)
            
            # 별도의 체결 확인 태스크 실행
            asyncio.create_task(verify_trade_completion(trade_id, stock_code, order_no))
        else:
             database.update_trade_status(trade_id, "FAILED")
    except Exception as e:
        logger.error(f"매수 에러: {e}")
        database.update_trade_status(trade_id, "FAILED")

async def hourly_balance_report():
    while True:
        await asyncio.sleep(3600)
        try:
            if not ensure_kis_auth():
                logger.error("리포트 중단: KIS 인증 상태가 유효하지 않습니다.")
                continue
            trenv = ka.getTREnv()
            _, bal_res2 = await asyncio.to_thread(
                inquire_balance, env_dv="demo", cano=trenv.my_acct, acnt_prdt_cd=trenv.my_prod,
                afhr_flpr_yn="N", inqr_dvsn="01", unpr_dvsn="01", fund_sttl_icld_yn="N", 
                fncg_amt_auto_rdpt_yn="N", prcs_dvsn="00"
            )
            if not bal_res2.empty:
                total_amt = float(bal_res2['tot_evlu_amt'].iloc[0])
                p_l = float(bal_res2['evlu_pfls_smtl_amt'].iloc[0])
                msg = f"📊 [정기 잔고 리포트]\n총 평가액: {total_amt:,.0f}원\n수익금: {p_l:,.0f}원"
                await send_telegram_alert(msg)
        except Exception as e:
            logger.error(f"리포트 에러: {e}")

async def scan_and_trade_loop():
    logger.info("거래 루프 시작")
    has_done_premarket = False
    
    while system_status["is_running"]:
        current_mode = get_market_mode()
        system_status["market_mode"] = current_mode
        
        if current_mode == "STANDBY":
            if has_done_premarket: # 장 마감 직후 보고서
                await send_telegram_alert("🏁 장이 마감되었습니다. 봇이 대기 상태로 전환됩니다.")
                has_done_premarket = False
            await asyncio.sleep(60)
            continue
            
        try:
            if not ensure_kis_auth():
                logger.error("루프 일시중단: KIS 인증 상태가 유효하지 않습니다.")
                await asyncio.sleep(60)
                continue
            # 08:51 장전 예상체결가 분석
            now = datetime.now(KST)
            if current_mode == "PRE_MARKET" and now.hour == 8 and now.minute == 51 and not has_done_premarket:
                logger.info("08:51 장전 예상체결가 스캔 중...")
                # 예상체결가도 volume_rank 에서 어느 정도 필터링 가능 (혹은 시가총액 순)
                df_results = await asyncio.to_thread(volume_rank, "J", "20171", "0000", "0", "1", "000000", "000000", "1000", "200000", "0", "")
                if df_results is not None and not df_results.empty:
                    top = df_results.iloc[0]
                    # AI 분석 후 바로 시가 매수 전략
                    res = await evaluate_stock_with_ai(str(top['mksc_shrn_iscd']), str(top['hts_kor_isnm']), float(top['stck_prpr']), 0, str(top['vol_inrt']), True)
                    if res['action'] == "BUY":
                        await execute_trade(str(top['mksc_shrn_iscd']), str(top['hts_kor_isnm']), float(top['stck_prpr']), res['reason'])
                has_done_premarket = True
                
            # 정규장 스캐닝 (1분 간격)
            if current_mode == "ACTIVE":
                df_results = await asyncio.to_thread(volume_rank, "J", "20171", "0000", "0", "1", "000000", "000000", "1000", "150000", "50000", "")
                system_status["last_scan_time"] = datetime.now(KST).isoformat()
                system_status["total_scans"] += 1
                
                if df_results is not None and not df_results.empty:
                    ts = df_results.iloc[0]
                    ai_res = await evaluate_stock_with_ai(str(ts['mksc_shrn_iscd']), str(ts['hts_kor_isnm']), float(ts['stck_prpr']), float(ts['acml_vol']), str(ts['vol_inrt']))
                    database.log_scan(str(ts['mksc_shrn_iscd']), f"증가율 {ts['vol_inrt']}%", ai_res['action'], ai_res['reason'])
                    if ai_res['action'] == "BUY":
                        await execute_trade(str(ts['mksc_shrn_iscd']), str(ts['hts_kor_isnm']), float(ts['stck_prpr']), ai_res['reason'])

        except Exception as e:
            logger.error(f"루프 에러: {e}")
        await asyncio.sleep(60)

# 기존 on_event 핸들러는 lifespan으로 대체되었으므로 삭제

if __name__ == "__main__":
    # access_log=False 설정을 통해 대시보드 폴링 로그(소음) 제거
    uvicorn.run("ai_trading_engine:app", host="0.0.0.0", port=8080, reload=False, access_log=False)
