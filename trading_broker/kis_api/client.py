import os
import requests
import yaml
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class KISClient:
    """한국투자증권 API 통신을 담당하는 기본 클라이언트"""
    
    def __init__(self, is_paper: bool = True):
        self.is_paper = is_paper
        self.base_url = "https://openapivts.koreainvestment.com:29443" if is_paper else "https://openapi.koreainvestment.com:9443"
        self._load_config()
        self.access_token: Optional[str] = None
        self.token_expired_at: Optional[datetime] = None
        
    def _load_config(self):
        """환경 변수 및 YAML 설정 로드"""
        self.app_key = os.environ.get("KIS_APP_KEY")
        self.app_secret = os.environ.get("KIS_SECRET")
        self.account_no = os.environ.get("KIS_ACCOUNT_NO")
        self.account_prod = os.environ.get("KIS_ACCOUNT_PROD", "01")
        
        # YAML 파일 보조 로드
        config_path = os.environ.get("KIS_CONFIG_PATH", "kis_devlp.yaml")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
                if cfg:
                    self.app_key = self.app_key or (cfg.get("paper_app") if self.is_paper else cfg.get("my_app"))
                    self.app_secret = self.app_secret or (cfg.get("paper_sec") if self.is_paper else cfg.get("my_sec"))
                    self.account_no = self.account_no or (cfg.get("my_paper_stock") if self.is_paper else cfg.get("my_acct_stock"))

    def ensure_token(self):
        """접근 토큰 유효성 검행 및 자동 갱신"""
        if self.access_token and self.token_expired_at and self.token_expired_at > datetime.now() + timedelta(minutes=10):
            return self.access_token
            
        url = f"{self.base_url}/oauth2/tokenP"
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            # 형식: "2026-04-09 13:17:15"
            self.token_expired_at = datetime.strptime(data["access_token_token_expired"], "%Y-%m-%d %H:%M:%S")
            logger.info(f"🔑 KIS 토큰 갱신 완료 (만료: {self.token_expired_at})")
            return self.access_token
        else:
            logger.error(f"❌ KIS 토큰 발급 실패: {response.text}")
            raise Exception("KIS API 인증 실패")

    def request(self, method: str, path: str, headers: Dict[str, str] = {}, params: Dict[str, Any] = {}, data: Dict[str, Any] = {}):
        """공통 HTTP 요청 핸들러 (Rate Limit 처리 및 재시도 포함 가능)"""
        token = self.ensure_token()
        
        default_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }
        default_headers.update(headers)
        
        url = f"{self.base_url}{path}"
        
        try:
            response = requests.request(method, url, headers=default_headers, params=params, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"🌐 KIS API 요청 오류 ({path}): {e}")
            raise
