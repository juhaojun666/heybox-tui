"""小黑盒摸鱼 - 配套图片查看器

轻量置顶小窗口，与 heybox-tui 联动，切换帖子时图片自动更新。

用法:
  python app.py              # 自动启动 TUI + 查看器
  python viewer.py           # 单独启动查看器
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen, Request

import tkinter as tk

STATE_FILE = Path(tempfile.gettempdir()) / "heybox_viewer_state.json"
LOCK_FILE = Path(tempfile.gettempdir()) / "heybox_viewer.lock"
POLL_INTERVAL = 0.5

# 内存缓存：url -> PIL Image
_cache: dict[str, object] = {}
_cache_order: list[str] = []
_CACHE_MAX = 20


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def download_image(url: str, max_retries: int = 2) -> bytes | None:
    for attempt in range(max_retries + 1):
        try:
            req = Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://www.xiaoheihe.cn/",
                    "Origin": "https://www.xiaoheihe.cn",
                },
            )
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urlopen(req, timeout=15, context=ctx) as resp:
                data = resp.read()
                if len(data) < 100:
                    # 可能返回了错误页面而非图片
                    return None
                return data
        except Exception as e:
            if attempt < max_retries:
                import time
                time.sleep(1 * (attempt + 1))
            continue
    return None


def _cache_put(url: str, img) -> None:
    if url in _cache:
        return
    _cache[url] = img
    _cache_order.append(url)
    while len(_cache_order) > _CACHE_MAX:
        old = _cache_order.pop(0)
        _cache.pop(old, None)


def _cache_get(url: str):
    return _cache.get(url)


class ImageViewer:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("heybox 图片")
        self.root.geometry("420x440-10-40")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#1e1e1e")
        self.root.minsize(200, 200)

        self._images: list[str] = []
        self._originals: list[str] = []
        self._index = 0
        self._photo = None
        self._last_hash = ""

        # 顶部信息栏
        self._info_var = tk.StringVar(value="等待 TUI 选择帖子...")
        tk.Label(
            self.root,
            textvariable=self._info_var,
            bg="#2d2d2d",
            fg="#cccccc",
            font=("Microsoft YaHei UI", 9),
            anchor="w",
            padx=8,
            pady=4,
        ).pack(fill="x")

        # 图片区域
        self._canvas = tk.Canvas(self.root, bg="#1e1e1e", highlightthickness=0)
        self._canvas.pack(fill="both", expand=True)

        # 底部控制栏
        ctrl = tk.Frame(self.root, bg="#2d2d2d")
        ctrl.pack(fill="x")

        btn_kw = dict(
            bg="#3c3c3c", fg="#cccccc", activebackground="#505050",
            activeforeground="#ffffff", bd=0, padx=12, pady=4,
            font=("Microsoft YaHei UI", 9),
        )
        tk.Button(ctrl, text="◀ 上一张", command=self._prev, **btn_kw).pack(side="left", padx=4, pady=4)
        tk.Button(ctrl, text="下一张 ▶", command=self._next, **btn_kw).pack(side="left", padx=4, pady=4)
        tk.Button(ctrl, text="📂 原图", command=self._open_in_system, **btn_kw).pack(side="right", padx=4, pady=4)

        # 键盘绑定
        self.root.bind("<Left>", lambda e: self._prev())
        self.root.bind("<Right>", lambda e: self._next())
        self.root.bind("<Escape>", lambda e: self._on_close())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 写锁文件标记进程存活
        LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")

        # 禁止窗口抢占焦点
        self.root.after(50, self._set_no_activate)

        self._poll()

    def _set_no_activate(self) -> None:
        """设置窗口不抢占焦点"""
        try:
            import ctypes
            hwnd = int(self.root.winfo_id())
            GWL_EXSTYLE = -20
            WS_EX_NOACTIVATE = 0x08000000
            ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style | WS_EX_NOACTIVATE)
        except Exception:
            pass

    def _on_close(self) -> None:
        try:
            LOCK_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        self.root.destroy()

    # ─── 轮询 ───

    def _poll(self) -> None:
        try:
            state = load_state()
            img_hash = state.get("hash", "")
            if img_hash and img_hash != self._last_hash:
                self._last_hash = img_hash
                self._images = state.get("images", [])
                self._originals = state.get("originals", self._images)
                self._index = 0
                self._show_current()

            # 检测 TUI 传来的图片索引
            target_index = state.get("image_index")
            if target_index is not None and target_index != self._index:
                if 0 <= target_index < len(self._images):
                    self._index = target_index
                    self._show_current()
        except Exception:
            pass
        self.root.after(int(POLL_INTERVAL * 1000), self._poll)

    # ─── 图片显示 ───

    def _show_current(self) -> None:
        if not self._images:
            self._info_var.set("该帖子没有图片")
            self._canvas.delete("all")
            self._photo = None
            return

        url = self._images[self._index]

        # 缓存命中，直接渲染
        cached = _cache_get(url)
        if cached is not None:
            self._render_pil(cached)
            return

        self._info_var.set(f"加载中... ({self._index + 1}/{len(self._images)})")
        threading.Thread(target=self._fetch, args=(url,), daemon=True).start()

    def _fetch(self, url: str) -> None:
        """子线程：下载 + PIL 缩放，传 Image 对象回主线程"""
        data = download_image(url)
        if data is None:
            self.root.after(0, lambda: self._on_fetch_fail(url))
            return

        try:
            from PIL import Image

            img = Image.open(BytesIO(data))
            # CDN 已缩放到 500px 宽，这里只做适配窗口的微调
            cw = self._canvas.winfo_width() or 400
            ch = self._canvas.winfo_height() or 360
            iw, ih = img.size
            scale = min(cw / iw, ch / ih, 1.0)
            if scale < 0.95:
                new_w = max(1, int(iw * scale))
                new_h = max(1, int(ih * scale))
                img = img.resize((new_w, new_h))
            _cache_put(url, img)
            self.root.after(0, lambda: self._render_pil(img))
        except ImportError:
            tmp = Path(tempfile.mkdtemp(prefix="heybox_")) / "img.png"
            tmp.write_bytes(data)
            self.root.after(0, lambda: self._render_file(str(tmp)))
        except Exception:
            self.root.after(0, lambda: self._info_var.set("图片解码失败"))

    def _on_fetch_fail(self, url: str) -> None:
        """下载失败时标记并提示，可按→重试"""
        self._info_var.set(f"❌ 加载失败 {self._index + 1}/{len(self._images)}  → 重试")

    def _render_pil(self, img) -> None:
        from PIL import ImageTk

        self._photo = ImageTk.PhotoImage(img)
        self._canvas.delete("all")
        cw = self._canvas.winfo_width() or 400
        ch = self._canvas.winfo_height() or 360
        self._canvas.create_image(cw // 2, ch // 2, anchor="center", image=self._photo)
        self._info_var.set(f"📷 {self._index + 1}/{len(self._images)}  ← → 切换")

    def _render_file(self, path: str) -> None:
        try:
            self._photo = tk.PhotoImage(file=path)
            self._canvas.delete("all")
            cw = self._canvas.winfo_width() or 400
            ch = self._canvas.winfo_height() or 360
            self._canvas.create_image(cw // 2, ch // 2, anchor="center", image=self._photo)
            self._info_var.set(f"📷 {self._index + 1}/{len(self._images)}  ← → 切换")
        except Exception:
            self._info_var.set("请安装 Pillow: pip install Pillow")

    # ─── 控制按钮 ───

    def _prev(self) -> None:
        if self._images and self._index > 0:
            self._index -= 1
            self._show_current()

    def _next(self) -> None:
        if self._images and self._index < len(self._images) - 1:
            self._index += 1
            self._show_current()

    def _open_in_system(self) -> None:
        if not self._images:
            return
        # 用原图 URL
        url = self._originals[self._index] if self._originals else self._images[self._index]
        threading.Thread(target=self._download_and_open, args=(url,), daemon=True).start()

    def _download_and_open(self, url: str) -> None:
        data = download_image(url)
        if not data:
            return
        tmp_dir = Path(tempfile.mkdtemp(prefix="heybox_"))
        ext = ".jpg" if "jpeg" in url or "jpg" in url else ".png"
        path = tmp_dir / f"image{ext}"
        path.write_bytes(data)
        if os.name == "nt":
            os.startfile(str(path))

    # ─── 启动 ───

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    app = ImageViewer()
    app.run()
