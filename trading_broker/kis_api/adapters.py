from typing import List, Dict, Any, Optional
import logging
from .client import KISClient

logger = logging.getLogger(__name__)

class KISAdapter:
    """KIS API와 도메인 모델 간의 어댑터 계층"""
    
    def __init__(self, client: KISClient):
        self.client = client
        
    def get_balance(self) -> Dict[str, Any]:
        """계좌 잔고 조회 및 공통 포맷 변환"""
        path = "/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = {
            "tr_id": "VTTC8434R" if self.client.is_paper else "TTTC8434R",
            "custtype": "P"
        }
        params = {
            "CANO": self.client.account_no,
            "ACNT_PRDT_CD": self.client.account_prod,
            "AFHR_FLPR_YN": "N",
            "O_PRCS_DVSN": "01", # 01: 단가조회
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00"
        }
        
        try:
            res = self.client.request("GET", path, headers=headers, params=params)
            # KIS 응답을 내부 표준 형식으로 매핑
            output2 = res.get('output2', [{}])[0]
            return {
                "total_asset": float(output2.get('tot_evlu_amt', 0)),
                "pnl_amt": float(output2.get('evlu_pfls_smtl_amt', 0)),
                "cash": float(output2.get('dnca_tot_amt', 0)),
                "holdings": res.get('output1', [])
            }
        except Exception as e:
            logger.error(f"❌ 잔고 조회 실패: {e}")
            raise

    def get_stock_price(self, symbol: str) -> float:
        """종목 현재가 조회"""
        path = "/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = {
            "tr_id": "FHKST01010100",
            "custtype": "P"
        }
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": symbol
        }
        
        try:
            res = self.client.request("GET", path, headers=headers, params=params)
            return float(res.get('output', {}).get('stck_prpr', 0))
        except Exception as e:
            logger.error(f"❌ 시세 조회 실패 ({symbol}): {e}")
            raise

    def place_order(self, symbol: str, qty: int, price: float = 0, action: str = "BUY") -> Dict[str, Any]:
        """매수/매도 주문 실행"""
        # tr_id: VTTC0802U (모의 매수), VTTC0801U (모의 매도)
        # 실전: TTTC0802U (매수), TTTC0801U (매도)
        if action == "BUY":
            tr_id = "VTTC0802U" if self.client.is_paper else "TTTC0802U"
        else:
            tr_id = "VTTC0801U" if self.client.is_paper else "TTTC0801U"
            
        path = "/uapi/domestic-stock/v1/trading/order-cash"
        headers = {
            "tr_id": tr_id,
            "custtype": "P"
        }
        data = {
            "CANO": self.client.account_no,
            "ACNT_PRDT_CD": self.client.account_prod,
            "PDNO": symbol,
            "ORD_DVSN": "01", # 01: 시장가
            "ORD_QTY": str(qty),
            "ORD_UNPR": str(int(price)) if price > 0 else "0",
        }
        
        try:
            res = self.client.request("POST", path, headers=headers, data=data)
            return {
                "order_no": res.get('output', {}).get('ODNO'),
                "status": "SUCCESS" if res.get('rt_cd') == '0' else "FAILED",
                "msg": res.get('msg1')
            }
        except Exception as e:
             logger.error(f"❌ 주문 제출 실패 ({symbol}): {e}")
             raise

    def get_volume_rank(self) -> List[Dict[str, Any]]:
        """거래량 급증 종목 순위 조회 (실시간 스캐너용)"""
        path = "/uapi/domestic-stock/v1/quotations/volume-rank"
        headers = {
            "tr_id": "FHPST01710000",
            "custtype": "P"
        }
        params = {
            "FID_COND_MRKT_DIV_CODE": "J", # 주식
            "FID_COND_SCR_DIV_CODE": "20171",
            "FID_INPUT_ISCD": "0000",
            "FID_DIV_CLS_CODE": "0",
            "FID_BLNG_CLS_CODE": "1",
            "FID_TRGT_CLS_CODE": "000000",
            "FID_TRGT_EXLS_CLS_CODE": "000000",
            "FID_INPUT_PRICE_1": "1000",
            "FID_INPUT_PRICE_2": "200000",
            "FID_VOL_CNT": "50000",
            "FID_INPUT_DATE_1": ""
        }
        
        try:
            res = self.client.request("GET", path, headers=headers, params=params)
            return res.get('output', [])
        except Exception as e:
            logger.error(f"❌ 거래량 순위 조회 실패: {e}")
            return []
