from __future__ import annotations
import os
import logging
import requests
from requests.adapters import HTTPAdapter
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv
from urllib3.util.retry import Retry

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

DEFAULT_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "15"))


@dataclass(frozen=True)
class Config:
    ANIME_PADRAO: str
    SEARCH_URL: str
    EPISODIO_FILE: str

    QB_URL: str
    USERNAME: str
    PASSWORD: str
    SAVE_PATH: str

    CHECK_INTERVAL: int = int(os.getenv("CHECK_INTERVAL", "300"))
    HTTP_TIMEOUT: int = DEFAULT_TIMEOUT

    @staticmethod
    def load_from_env() -> "Config":
        missing = []

        def need(name: str) -> Optional[str]:
            val = os.getenv(name)
            if not val:
                missing.append(name)
            return val

        cfg = Config(
            ANIME_PADRAO=need("ANIME_PADRAO"),
            SEARCH_URL=need("SEARCH_URL"),
            EPISODIO_FILE=need("EPISODIO_FILE"),
            QB_URL=need("QB_URL"),
            USERNAME=need("QB_USERNAME"),
            PASSWORD=need("QB_PASSWORD"),
            SAVE_PATH=need("SAVE_PATH"),
            CHECK_INTERVAL=int(os.getenv("CHECK_INTERVAL", "300")),
            HTTP_TIMEOUT=int(os.getenv("HTTP_TIMEOUT", str(DEFAULT_TIMEOUT))),
        )
        if missing:
            raise ValueError(f"[ERROR] Variáveis de ambiente ausentes: {', '.join(missing)}")
        return cfg


def make_session(total_retries: int = 3, backoff_factor: float = 0.5) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=total_retries,
        read=total_retries,
        connect=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["HEAD", "GET", "OPTIONS", "POST"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    session.headers.update({
        "User-Agent": "anime-monitor/1.0 (+github.com/your-org) requests"
    })
    return session