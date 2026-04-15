"""配置管理"""

from __future__ import annotations

import json
from pathlib import Path

CONFIG_DIR = Path(__file__).parent
CONFIG_FILE = CONFIG_DIR / "config.json"

_DEFAULT_CONFIG = {
    "heybox_id": "",
    "pkey": "",
}


def _ensure_config() -> None:
    """首次运行时创建示例配置文件"""
    if CONFIG_FILE.exists():
        return
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps(_DEFAULT_CONFIG, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_config() -> dict:
    _ensure_config()
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return dict(_DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def get_credential() -> dict:
    """获取登录凭证，返回 {heybox_id, pkey}"""
    cfg = load_config()
    return {
        "heybox_id": cfg.get("heybox_id", ""),
        "pkey": cfg.get("pkey", ""),
    }


def is_logged_in() -> bool:
    cred = get_credential()
    return bool(cred["heybox_id"] and cred["pkey"])
