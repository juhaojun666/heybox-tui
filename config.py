"""配置管理"""

from __future__ import annotations

import json
from pathlib import Path

CONFIG_DIR = Path(__file__).parent
CONFIG_FILE = CONFIG_DIR / "config.json"

_DEFAULT_CONFIG = {
    "cookie": "",
}


def _ensure_config() -> None:
    """首次运行时创建示例配置文件"""
    if CONFIG_FILE.exists():
        return
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
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def get_cookie() -> str:
    """获取登录 cookie"""
    cfg = load_config()
    return cfg.get("cookie", "")


def is_logged_in() -> bool:
    return bool(get_cookie())
