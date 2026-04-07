import sys
import os
import asyncio
import logging
import yaml
import argparse
import threading
import json
import websockets

sys.path.extend(['.', 'examples_user', 'examples_user/domestic_stock', 'examples_user/auth'])

import kis_auth as ka
from domestic_stock_functions import inquire_price, order_cash
from domestic_stock_functions_ws import ccnl_krx

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# 로깅 설정
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 설정 로드
config_root = ka.config_root
try:
    with open(f'{os.path.expanduser("~")}/KIS/config/kis_devlp.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
except Exception as e:
    logger.error("kis_devlp.yaml 파일을 파싱하지 못했습니다: " + str(e))
    # fallback
    try:
        with open('kis_devlp.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except:
        sys.exit(1)

TELEGRAM_TOKEN = config.get("telegram_token", "")
ALLOWED_CHAT_ID = str(config.get("telegram_chat_id", ""))

# 글로벌 거래 환경 변수
TRADING_ENV = "vps"  # "prod" 또는 "vps"

# 글로벌 상태: 텔레그램 애플리케이션 및 웹소켓
telegram_app = None
ws_connection = None

# 모니터링 왓치리스트 (동시성 제어를 위한 Lock 사용)
# 형식: {"005930": {"target_price": 80000.0, "action": "buy", "triggered": False}}
watchlist = {}
watchlist_lock = threading.Lock()

def init_kis_api():
    logger.info(f"KIS API 인증 초기화 (환경: {TRADING_ENV})")
    try:
        val = "01"
        if TRADING_ENV == "prod":
            ka.auth(svr="prod", product=val)
            ka.auth_ws(svr="prod", product=val)
        else:
            ka.auth(svr="vps", product=val)
            ka.auth_ws(svr="vps", product=val)
        return True
    except Exception as e:
        logger.error(f"인증 실패: {e}")
        return False

# ==========================================
# 실시간 웹소켓 엔진 (백그라운드 비동기 태스크)
# ==========================================
async def process_price_update(stock_code: str, current_price: float):
    """ 웹소켓을 통해 실시간 가격이 들어오면 평가하여 조건 도달 시 자동 주문 실행 """
    triggered_action = None
    with watchlist_lock:
        if stock_code in watchlist:
            item = watchlist[stock_code]
            if not item["triggered"]:
                target_price = item["target_price"]
                # 설정 타겟 도달 시 (현재는 단순 '돌파' 기준 가상 구현)
                if current_price >= target_price:
                    item["triggered"] = True
                    triggered_action = item["action"]
                    
    # 락 밖에서 텔레그램 메시지 발송 및 주문 처리
    if triggered_action:
        msg = f"🔥 [모니터링 알림] {stock_code} 종목이 목표가 {item['target_price']}원에 도달했습니다! (현재가: {current_price}원) -> [{triggered_action}] 실행"
        logger.info(msg)
        if telegram_app and ALLOWED_CHAT_ID:
            await telegram_app.bot.send_message(chat_id=ALLOWED_CHAT_ID, text=msg)
            
            if triggered_action in ["buy", "sell"]:
                 await execute_trade_action(stock_code, triggered_action)

async def execute_trade_action(stock_code: str, action: str):
    """ 주문 실행 헬퍼 (테스트를 위해 기본 1주 시장가 주문) """
    qty = "1"
    env_dv = "real" if TRADING_ENV == "prod" else "demo"
    trenv = ka.getTREnv()

    try:
        # 안전한 동기 함수 호출
        df = await asyncio.to_thread(
            order_cash,
            env_dv=env_dv,
            ord_dv=action,
            cano=trenv.my_acct,
            acnt_prdt_cd=trenv.my_prod,
            pdno=stock_code,
            ord_dvsn="01", # 01: 시장가
            ord_qty=qty,
            ord_unpr="0",
            excg_id_dvsn_cd="4"
        )
        msg = f"✅ 자동 {action} 주문 결과 ({qty}주):\n{df.to_string() if hasattr(df, 'to_string') else str(df)}"
        await telegram_app.bot.send_message(chat_id=ALLOWED_CHAT_ID, text=msg)
    except Exception as e:
        logger.error(f"주문 실패: {e}")
        await telegram_app.bot.send_message(chat_id=ALLOWED_CHAT_ID, text=f"❌ 주문 실패: {e}")

async def ws_monitor_loop():
    """ KIS 실시간 체결가 웹소켓 수신 루프 """
    global ws_connection
    url = f"{ka.getTREnv().my_url_ws}/tryitout"
    
    logger.info("웹소켓 백그라운드 태스크 시작")
    
    while True:
        try:
            async with websockets.connect(url, ping_interval=60) as ws:
                ws_connection = ws
                logger.info("웹소켓 KIS 연결 성공")
                
                # 기존 왓치리스트에 있던 종목 구독 전송
                with watchlist_lock:
                    for stock_code in watchlist:
                        msg, _ = ccnl_krx("1", stock_code, env_dv=("real" if TRADING_ENV == "prod" else "demo"))
                        await ws.send(json.dumps(msg))
                
                async for raw in ws:
                    if raw[0] in ["0", "1"]:
                        d1 = raw.split("|")
                        if len(d1) >= 4:
                            tr_id = d1[1]
                            d = d1[3]
                            # H0STCNT0 (체결가) 파싱
                            cols = d.split("^")
                            if len(cols) >= 3:
                                stock_code = cols[0]
                                current_price = float(cols[2])
                                await process_price_update(stock_code, current_price)
                    elif raw.startswith("{"):
                        js = json.loads(raw)
                        # PINGPONG 처리
                        if js.get("header", {}).get("tr_id") == "PINGPONG":
                            await ws.pong(raw)
        except Exception as e:
            logger.error(f"웹소켓 연결 오류 (재연결 시도): {e}")
            ws_connection = None
            await asyncio.sleep(3)


# ==========================================
# 텔레그램 명령어 핸들러
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if ALLOWED_CHAT_ID and chat_id != ALLOWED_CHAT_ID: return
    
    welcome_msg = (
        f"🚀 KIS 자동매매 봇 시작 (환경: {TRADING_ENV})\n"
        "추가 명령어:\n"
        "/monitor [종목코드] [목표가] [동작(기본값:buy)] - 목표가 터치 시 자동 시장가 주문 (1주)\n"
        "예: /monitor 005930 85000 buy"
    )
    await update.message.reply_text(welcome_msg)

async def monitor_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if ALLOWED_CHAT_ID and chat_id != ALLOWED_CHAT_ID: return

    if len(context.args) < 2:
        await update.message.reply_text("사용법: /monitor [종목코드] [목표단가] [동작:buy/sell/alert]")
        return
        
    stock_code = context.args[0]
    target_price = float(context.args[1])
    action = context.args[2].lower() if len(context.args) > 2 else "buy"
    
    with watchlist_lock:
        watchlist[stock_code] = {
            "target_price": target_price,
            "action": action,
            "triggered": False
        }
    
    await update.message.reply_text(f"[{stock_code}] {target_price}원 도달 시 '{action}' 실행을 모니터링합니다.")
    
    # 웹소켓이 연결되어 있으면 해당 종목 동적 구독 전송
    global ws_connection
    if ws_connection:
        env_dv = "real" if TRADING_ENV == "prod" else "demo"
        msg, _ = ccnl_krx("1", stock_code, env_dv=env_dv)
        try:
            await ws_connection.send(json.dumps(msg))
        except Exception as e:
            logger.error(f"동적 구독 전송 실패: {e}")

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 기존 코드 동일
    chat_id = str(update.effective_chat.id)
    if ALLOWED_CHAT_ID and chat_id != ALLOWED_CHAT_ID: return
    if len(context.args) == 0: return

    stock_code = context.args[0]
    try:
        env_dv = "real" if TRADING_ENV == "prod" else "demo"
        df = await asyncio.to_thread(inquire_price, env_dv=env_dv, fid_cond_mrkt_div_code="J", fid_input_iscd=stock_code)
        if hasattr(df, 'empty') and not df.empty:
            current_price = df['stck_prpr'].iloc[0]
            await update.message.reply_text(f"[{stock_code}] 현재가: {current_price}원")
    except Exception as e:
        await update.message.reply_text(f"시세 조회 오류: {e}")


def main():
    parser = argparse.ArgumentParser(description='Telegram Trading Bot with WS Monitor')
    parser.add_argument('--env', choices=['prod', 'vps'], default='vps', help='Trading environment (default: vps)')
    args = parser.parse_args()

    global TRADING_ENV
    TRADING_ENV = args.env

    if not init_kis_api():
        return

    if not TELEGRAM_TOKEN:
        logger.error("텔레그램 토큰이 없습니다. 종료합니다.")
        return

    global telegram_app
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("monitor", monitor_stock))
    telegram_app.add_handler(CommandHandler("price", price))

    logger.info(f"봇 시작 (환경: {TRADING_ENV})")
    
    # 텔레그램루프 시작 전, 웹소켓 태스크 등록
    # 방법: post_init 훅을 사용하여루프 구동 직후 태스크 시작
    async def post_init(application: Application):
        asyncio.create_task(ws_monitor_loop())

    telegram_app.post_init = post_init
    telegram_app.run_polling()

if __name__ == '__main__':
    main()
