from __future__ import annotations
import json
import logging
import os
import re
import tempfile
import time
import requests
from pathlib import Path
from typing import Iterable, Optional
from bs4 import BeautifulSoup
from config import Config, make_session

logger = logging.getLogger("anime-monitor")


def carregar_proximo_episodio(episodio_file: str) -> int:
    try:
        with open(episodio_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            n = int(data.get("proximo_episodio", 1))
            return n if n >= 1 else 1
    except FileNotFoundError:
        logger.info("[INFO] Arquivo de episódio não encontrado. Iniciando do episódio 1.")
        return 1
    except (json.JSONDecodeError, ValueError):
        logger.warning("[ERROR] Arquivo de episódio inválido/corrompido. Iniciando do episódio 1.")
        return 1


def salvar_proximo_episodio(episodio_file: str, n: int) -> None:
    Path(os.path.dirname(episodio_file) or ".").mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(prefix=".episodio_", suffix=".json", dir=os.path.dirname(episodio_file) or ".")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump({"proximo_episodio": n}, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, episodio_file)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


class AnimeScraper:
    def __init__(self, session: requests.Session, search_url: str, http_timeout: int, anime_padrao: str):
        self.session = session
        self.search_url = search_url
        self.http_timeout = http_timeout
        self.anime_padrao = anime_padrao

    def _get_soup(self, url: str) -> BeautifulSoup:
        resp = self.session.get(url, timeout=self.http_timeout)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")

    def obter_lista_torrents(self) -> Iterable:
        soup = self._get_soup(self.search_url)
        return soup.select("table.torrent-list tbody tr")

    def encontrar_pagina_do_episodio(self, episodio: int) -> Optional[str]:
        logger.info("[INFO] Procurando episódio %02d", episodio)
        pattern_raw = self.anime_padrao.format(ep=episodio)
        try:
            pattern = re.compile(pattern_raw)
        except re.error:
            logger.warning("[ERROR] Regex ANIME_PADRAO inválida. Usando busca simples.")
            pattern = None

        for row in self.obter_lista_torrents():
            tag = row.select_one("td:nth-of-type(2) a[href^='/view/']:not(.comments)")
            if not tag:
                continue
            titulo = tag.text.strip()
            if (pattern and pattern.search(titulo)) or (not pattern and pattern_raw in titulo):
                logger.info("[OK] Encontrado: %s", titulo)
                return f"https://nyaa.si{tag['href']}"
        return None

    def extrair_magnet(self, page_url: str) -> Optional[str]:
        logger.info("[INFO] Acessando: %s", page_url)
        soup = self._get_soup(page_url)
        tag = soup.find("a", href=re.compile(r"^magnet:\?xt=urn:btih:"))
        return tag["href"] if tag else None


class QBittorrentClient:
    def __init__(self, session: requests.Session, base_url: str, username: str, password: str, http_timeout: int):
        self.session = session
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.http_timeout = http_timeout

    def autenticar(self) -> None:
        url = f"{self.base_url}/api/v2/auth/login"
        resp = self.session.post(url, data={"username": self.username, "password": self.password},
                                 timeout=self.http_timeout)
        if resp.status_code != 200 or "Ok." not in resp.text:
            raise RuntimeError(f"[ERROR] Falha ao autenticar no qBittorrent: {resp.status_code} - {resp.text}")
        logger.info("[AUTH_OK] Login bem-sucedido no qBittorrent")

    def adicionar_magnet(self, magnet_link: str, save_path: str) -> None:
        Path(save_path).mkdir(parents=True, exist_ok=True)
        payload = {
            "urls": magnet_link,
            "paused": "false",
            "savepath": save_path
        }
        url = f"{self.base_url}/api/v2/torrents/add"
        resp = self.session.post(url, data=payload, timeout=self.http_timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"[ERROR] Erro ao enviar torrent: {resp.status_code} - {resp.text}")
        logger.info("[OK] Magnet enviado ao qBittorrent (diretório: %s)", save_path)


def monitorar():
    cfg = Config.load_from_env()
    session = make_session()
    scraper = AnimeScraper(session, cfg.SEARCH_URL, cfg.HTTP_TIMEOUT, cfg.ANIME_PADRAO)
    qb = QBittorrentClient(session, cfg.QB_URL, cfg.USERNAME, cfg.PASSWORD, cfg.HTTP_TIMEOUT)

    episodio = carregar_proximo_episodio(cfg.EPISODIO_FILE)

    while True:
        try:
            pagina_torrent = scraper.encontrar_pagina_do_episodio(episodio)
            if pagina_torrent:
                magnet = scraper.extrair_magnet(pagina_torrent)
                if magnet:
                    logger.info("[INFO] Enviando para o qBittorrent: %s", magnet)
                    qb.autenticar()
                    qb.adicionar_magnet(magnet, cfg.SAVE_PATH)
                    salvar_proximo_episodio(cfg.EPISODIO_FILE, episodio + 1)
                    logger.info("[OK] Processo finalizado.")
                    break
                else:
                    logger.info("[ERROR] Magnet não encontrado.")
        except Exception as e:
            logger.error("[ERROR] Exceção no ciclo: %s", e)

        logger.info("[WAIT] Tentando novamente em %.1f minutos...", cfg.CHECK_INTERVAL / 60)
        time.sleep(cfg.CHECK_INTERVAL)


if __name__ == "__main__":
    monitorar()