"""小黑盒 API 签名算法 (Python 移植版)

移植自: https://github.com/luckylca/xhhBackCrack
"""

import hashlib
import random
import time


# --- 基础混淆函数 (GF(2^8) MixColumns 变体) ---

def _vm(e: int) -> int:
    if e & 128:
        return (255 & ((e << 1) ^ 27))
    else:
        return e << 1


def _qm(e: int) -> int:
    return _vm(e) ^ e


def _dollar_m(e: int) -> int:
    return _qm(_vm(e))


def _ym(e: int) -> int:
    return _dollar_m(_qm(_vm(e)))


def _gm(e: int) -> int:
    return _ym(e) ^ _dollar_m(e) ^ _qm(e)


def _km_full(e_arr: list[int]) -> list[int]:
    e = list(e_arr)
    t = [0, 0, 0, 0]
    t[0] = _gm(e[0]) ^ _ym(e[1]) ^ _dollar_m(e[2]) ^ _qm(e[3])
    t[1] = _qm(e[0]) ^ _gm(e[1]) ^ _ym(e[2]) ^ _dollar_m(e[3])
    t[2] = _dollar_m(e[0]) ^ _qm(e[1]) ^ _gm(e[2]) ^ _ym(e[3])
    t[3] = _ym(e[0]) ^ _dollar_m(e[1]) ^ _qm(e[2]) ^ _gm(e[3])
    e[0], e[1], e[2], e[3] = t[0], t[1], t[2], t[3]
    return e


# --- 字符映射函数 ---

def _av(e: str, t: str, n: int) -> str:
    i = t[:n] if n > 0 else t[:n]
    r = ""
    for char in e:
        idx = ord(char) % len(i)
        r += i[idx]
    return r


def _sv(e: str, t: str) -> str:
    n_str = ""
    for char in e:
        idx = ord(char) % len(t)
        n_str += t[idx]
    return n_str


# --- 签名核心 ---

CHARSET = "AB45STUVWZEFGJ6CH01D237IXYPQRKLMN89"


def get_hkey(url_path: str, timestamp: int, nonce: str) -> str:
    parts = [p for p in url_path.split("/") if p]
    normalized_path = "/" + "/".join(parts) + "/"

    comp1 = _av(str(timestamp), CHARSET, -2)
    comp2 = _sv(normalized_path, CHARSET)
    comp3 = _sv(nonce, CHARSET)

    comps = [comp1, comp2, comp3]
    max_len = max(len(c) for c in comps)

    interleaved = ""
    for k in range(max_len):
        for c in comps:
            if k < len(c):
                interleaved += c[k]

    i_str = interleaved[:20]

    md5_hash = hashlib.md5(i_str.encode()).hexdigest()

    o_prefix = md5_hash[:5]
    hkey_prefix = _av(o_prefix, CHARSET, -4)

    suffix_part = md5_hash[-6:]
    suffix_input = [ord(c) for c in suffix_part]
    km_output = _km_full(suffix_input)
    checksum_val = sum(km_output) % 100
    checksum_str = str(checksum_val).zfill(2)

    return hkey_prefix + checksum_str


def generate_nonce() -> str:
    random_str = str(int(time.time() * 1000)) + str(random.random())
    return hashlib.md5(random_str.encode()).hexdigest().upper()


def get_timestamp() -> int:
    return int(time.time())


# --- 路由配置 ---

ROUTES = {
    "feeds": {
        "path": "/bbs/app/feeds",
        "params": {"pull": "0", "offset": "0", "dw": "844"},
    },
    "user_profile": {
        "path": "/bbs/app/profile/user/profile",
        "params": {"userid": ""},
    },
    "link_tree": {
        "path": "/bbs/app/link/tree",
        "params": {"link_id": ""},
    },
    "comment_list": {
        "path": "/bbs/app/api/comment/list",
        "params": {"link_id": "", "offset": "0", "limit": "30"},
    },
    "news_list": {
        "path": "/bbs/app/link/news",
        "params": {"offset": "0", "limit": "20"},
    },
    "hot_topics": {
        "path": "/bbs/app/api/feed/hot",
        "params": {"offset": "0", "limit": "20"},
    },
    "topic_categories": {
        "path": "/bbs/app/topic/categories",
        "params": {},
    },
    "emojis_list": {
        "path": "/bbs/app/api/emojis/list",
        "params": {},
    },
    "search_found": {
        "path": "/bbs/app/api/search/found",
        "params": {"force_refresh": "false"},
    },
}


BASE_PARAMS = {
    "os_type": "web",
    "app": "heybox",
    "client_type": "web",
    "version": "999.0.4",
    "web_version": "2.5",
    "x_client_type": "web",
    "x_app": "heybox_website",
    "heybox_id": "",
    "x_os_type": "Windows",
    "device_info": "Chrome",
    "device_id": "2c2fef8385ccef915e3b3caf94e3aa06",
}


def build_request_url(route_name: str, custom_params: dict | None = None) -> str:
    if route_name not in ROUTES:
        raise ValueError(
            f"路由 '{route_name}' 不存在，可用: {', '.join(ROUTES.keys())}"
        )

    route = ROUTES[route_name]
    timestamp = get_timestamp()
    nonce = generate_nonce()
    hkey = get_hkey(route["path"], timestamp, nonce)

    route_params = dict(route["params"])
    all_params = {**route_params, **BASE_PARAMS, **(custom_params or {})}
    all_params["hkey"] = hkey
    all_params["_time"] = timestamp
    all_params["nonce"] = nonce

    query = "&".join(f"{k}={v}" for k, v in all_params.items())
    return f"https://api.xiaoheihe.cn{route['path']}?{query}"
