"""小黑盒摸鱼 - 配套图片查看器

轻量置顶小窗口，与 heybox-tui 联动，切换帖子时图片自动更新。

用法:
  python viewer.py          # 启动查看器（与 TUI 配合使用）
"""

from __future__ import annotations

import json
import os
import tempfile
import time
import threading
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen, Request

import tkinter as tk
from tkinter import ttk

STATE_FILE = Path(tempfile.gettempdir()) / "heybox_viewer_state.json"
POLL_INTERVAL = 0.5  # 秒


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def download_image(url: bytes | str) -> bytes | None:
    try:
        req = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.xiaoheihe.cn/",
            },
        )
        with urlopen(req, timeout=15) as resp:
            return resp.read()
    except Exception:
        return None


class ImageViewer:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("heybox 图片")
        self.root.geometry("420x420+9999+60")  # 默认右上角
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#1e1e1e")
        self.root.minsize(200, 200)

        self._images: list[str] = []
        self._index = 0
        self._photo = None  # 防止 GC
        self._last_hash = ""
        self._loading = False

        # 顶部信息栏
        self._info_var = tk.StringVar(value="等待 TUI 选择帖子...")
        info_label = tk.Label(
            self.root,
            textvariable=self._info_var,
            bg="#2d2d2d",
            fg="#cccccc",
            font=("Microsoft YaHei UI", 9),
            anchor="w",
            padx=8,
            pady=4,
        )
        info_label.pack(fill="x")

        # 图片区域
        self._canvas = tk.Canvas(self.root, bg="#1e1e1e", highlightthickness=0)
        self._canvas.pack(fill="both", expand=True)

        # 底部控制栏
        ctrl = tk.Frame(self.root, bg="#2d2d2d")
        ctrl.pack(fill="x")

        btn_style = dict(
            bg="#3c3c3c", fg="#cccccc", activebackground="#505050",
            activeforeground="#ffffff", bd=0, padx=12, pady=4,
            font=("Microsoft YaHei UI", 9),
        )

        self._btn_prev = tk.Button(ctrl, text="◀ 上一张", command=self._prev, **btn_style)
        self._btn_prev.pack(side="left", padx=4, pady=4)

        self._btn_next = tk.Button(ctrl, text="下一张 ▶", command=self._next, **btn_style)
        self._btn_next.pack(side="left", padx=4, pady=4)

        self._btn_open = tk.Button(ctrl, text="📂 打开原图", command=self._open_in_system, **btn_style)
        self._btn_open.pack(side="right", padx=4, pady=4)

        # 键盘绑定
        self.root.bind("<Left>", lambda e: self._prev())
        self.root.bind("<Right>", lambda e: self._next())
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        # 启动轮询
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self) -> None:
        while True:
            try:
                state = load_state()
                img_hash = state.get("hash", "")
                if img_hash and img_hash != self._last_hash:
                    self._last_hash = img_hash
                    urls = state.get("images", [])
                    self._images = urls
                    self._index = 0
                    self.root.after(0, self._show_current)
            except Exception:
                pass
            time.sleep(POLL_INTERVAL)

    def _show_current(self) -> None:
        if not self._images:
            self._info_var.set("该帖子没有图片")
            self._canvas.delete("all")
            self._photo = None
            return

        self._info_var.set(f"加载中... ({self._index + 1}/{len(self._images)})")
        self.root.update_idletasks()

        # 在线程中下载，避免 UI 卡顿
        url = self._images[self._index]
        threading.Thread(target=self._load_image, args=(url,), daemon=True).start()

    def _load_image(self, url: str) -> None:
        data = download_image(url)
        if data is None:
            self.root.after(0, lambda: self._info_var.set("图片加载失败"))
            return

        try:
            from PIL import Image, ImageTk
            img = Image.open(BytesIO(data))
        except ImportError:
            # 没有 Pillow，用 tkinter 自带的 PhotoImage（只支持 GIF/PGM/PPM）
            try:
                self._photo = tk.PhotoImage(data=data)
                self.root.after(0, self._display_photo)
                return
            except Exception:
                self.root.after(0, lambda: self._info_var.set("请安装 Pillow: pip install Pillow"))
                return

        self.root.after(0, lambda: self._display_pil(img))

    def _display_pil(self, img) -> None:
        """用 Pillow 缩放并显示"""
        cw = self._canvas.winfo_width() or 400
        ch = self._canvas.winfo_height() or 360

        # 计算缩放
        iw, ih = img.size
        scale = min(cw / iw, ch / ih, 1.0)
        new_w = max(1, int(iw * scale))
        new_h = max(1, int(ih * scale))
        img_resized = img.resize((new_w, new_h))

        from PIL import ImageTk
        self._photo = ImageTk.PhotoImage(img_resized)

        self._canvas.delete("all")
        x = cw // 2
        y = ch // 2
        self._canvas.create_image(x, y, anchor="center", image=self._photo)
        self._info_var.set(f"📷 {self._index + 1}/{len(self._images)}  ← → 切换")

    def _display_photo(self) -> None:
        """用 tkinter 原生 PhotoImage 显示"""
        self._canvas.delete("all")
        cw = self._canvas.winfo_width() or 400
        ch = self._canvas.winfo_height() or 360
        x = cw // 2
        y = ch // 2
        self._canvas.create_image(x, y, anchor="center", image=self._photo)
        self._info_var.set(f"📷 {self._index + 1}/{len(self._images)}  ← → 切换")

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
        url = self._images[self._index]
        # 下载并打开
        tmp_dir = Path(tempfile.mkdtemp(prefix="heybox_"))
        data = download_image(url)
        if data:
            ext = ".jpg" if "jpeg" in url or "jpg" in url else ".png"
            path = tmp_dir / f"image{ext}"
            path.write_bytes(data)
            if os.name == "nt":
                os.startfile(str(path))
            elif os.name == "posix":
                import sys
                os.system(f"open '{path}'" if sys.platform == "darwin" else f"xdg-open '{path}'")

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    app = ImageViewer()
    app.run()
