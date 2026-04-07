import logging
import math

logger = logging.getLogger(__name__)

# --- 설정 사항 ---
# 최대 종목 수 (요구사항: 3종목 제한)
MAX_HOLDINGS = 3
# 한 종목당 투입 가능한 계좌 비중 (요구사항: 최대 40%)
MAX_ALLOCATION_RATIO = 0.40

def check_risk_and_get_qty(current_price: float, total_balance: float, current_holdings_count: int) -> int:
    """
    리스크 관리 룰을 평가하여 진입 가능 여부 및 매수 수량을 반환합니다.
    Total Balance 기준 40% 이하만 허용하며, 현재 보유 종목이 3개 이상이면 0을 반환합니다.
    """
    if current_holdings_count >= MAX_HOLDINGS:
        logger.warning(f"최대 보유 종목 수({MAX_HOLDINGS}) 초과. 진입 금지.")
        return 0
        
    if total_balance <= 0 or current_price <= 0:
        return 0
        
    allocation_limit = total_balance * MAX_ALLOCATION_RATIO
    
    # 구매 가능 수량 계산 (수수료 제외 단순 계산, 안전하게 내림)
    allowable_qty = math.floor(allocation_limit / current_price)
    
    return allowable_qty
