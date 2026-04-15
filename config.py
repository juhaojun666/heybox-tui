"""配置管理"""

from __future__ import annotations

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".heybox-tui"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def get_credential() -> dict:
    """获取登录凭证，返回 {heybox_id, pkey, ...}"""
    cfg = load_config()
    return {
        "heybox_id": cfg.get("heybox_id", ""),
        "pkey": cfg.get("pkey", ""),
    }


def is_logged_in() -> bool:
    cred = get_credential()
    return bool(cred["heybox_id"] and cred["pkey"])
