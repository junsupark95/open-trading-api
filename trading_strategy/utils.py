from datetime import datetime, time
import pytz

def get_kst_now():
    """현재 한국 시간(KST) 반환"""
    kst = pytz.timezone('Asia/Seoul')
    return datetime.now(kst)

def is_market_open() -> bool:
    """현재 한국 시장이 장중(08:30 ~ 15:30)인지 확인"""
    now = get_kst_now()
    
    # 주말 확인 (5: 토요일, 6: 일요일)
    if now.weekday() >= 5:
        return False
        
    current_time = now.time()
    start_time = time(8, 30)
    end_time = time(15, 30)
    
    return start_time <= current_time <= end_time

def get_market_status_str() -> str:
    """현재 시장 상태 문자열 반환"""
    if not is_market_open():
        now = get_kst_now()
        if now.weekday() >= 5:
            return "WEEKEND_REST"
        if now.time() < time(8, 30):
            return "PRE_MARKET"
        return "MARKET_CLOSED"
    return "OPEN"
