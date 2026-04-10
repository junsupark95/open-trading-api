import os
import time
import requests
import yaml
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# 재시도 가능한 HTTP 상태 코드 (서버 측 일시 오류)
_RETRYABLE_STATUS_CODES = {500, 502, 503, 504}
_MAX_RETRIES = 3
_REQUEST_TIMEOUT = 10  # seconds


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
        """접근 토큰 유효성 검증 및 자동 갱신"""
        if self.access_token and self.token_expired_at and self.token_expired_at > datetime.now() + timedelta(minutes=10):
            return self.access_token

        url = f"{self.base_url}/oauth2/tokenP"
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        response = requests.post(url, json=payload, timeout=_REQUEST_TIMEOUT)
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
        """공통 HTTP 요청 핸들러 (5xx 오류 시 지수 백오프 재시도)"""
        token = self.ensure_token()

        default_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }
        default_headers.update(headers)

        url = f"{self.base_url}{path}"
        last_exception: Optional[Exception] = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = requests.request(
                    method, url,
                    headers=default_headers,
                    params=params,
                    json=data,
                    timeout=_REQUEST_TIMEOUT,
                )

                # 재시도 가능한 서버 오류 (500/502/503/504)
                if response.status_code in _RETRYABLE_STATUS_CODES:
                    wait = 2 ** (attempt - 1)  # 1s, 2s, 4s
                    logger.warning(
                        f"🌐 KIS API 서버 오류 ({path}): HTTP {response.status_code} "
                        f"[{attempt}/{_MAX_RETRIES}회] {wait}초 후 재시도"
                    )
                    if attempt < _MAX_RETRIES:
                        time.sleep(wait)
                        continue
                    # 최대 재시도 초과 시 예외 발생
                    response.raise_for_status()

                # 4xx 등 재시도 불가 오류는 즉시 예외
                response.raise_for_status()
                return response.json()

            except requests.exceptions.Timeout as e:
                wait = 2 ** (attempt - 1)
                logger.warning(
                    f"⏱️ KIS API 타임아웃 ({path}) [{attempt}/{_MAX_RETRIES}회] {wait}초 후 재시도"
                )
                last_exception = e
                if attempt < _MAX_RETRIES:
                    time.sleep(wait)
            except requests.exceptions.ConnectionError as e:
                wait = 2 ** (attempt - 1)
                logger.warning(
                    f"🔌 KIS API 연결 오류 ({path}) [{attempt}/{_MAX_RETRIES}회] {wait}초 후 재시도"
                )
                last_exception = e
                if attempt < _MAX_RETRIES:
                    time.sleep(wait)
            except requests.exceptions.HTTPError as e:
                # 4xx는 재시도 없이 즉시 실패
                logger.error(f"🌐 KIS API 요청 오류 ({path}): {e}")
                raise
            except requests.exceptions.RequestException as e:
                logger.error(f"🌐 KIS API 요청 오류 ({path}): {e}")
                raise

        logger.error(f"🌐 KIS API 최대 재시도 초과 ({path}): {last_exception}")
        raise last_exception
