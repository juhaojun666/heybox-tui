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
import time
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen, Request

import tkinter as tk

STATE_FILE = Path(tempfile.gettempdir()) / "heybox_viewer_state.json"
POLL_INTERVAL = 0.5


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def download_image(url: str) -> bytes | None:
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
        self.root.geometry("420x440+9999+60")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#1e1e1e")
        self.root.minsize(200, 200)

        self._images: list[str] = []
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
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        # 用 root.after 做轮询，避免线程问题
        self._poll()

    # ─── 轮询 ───

    def _poll(self) -> None:
        try:
            state = load_state()
            img_hash = state.get("hash", "")
            if img_hash and img_hash != self._last_hash:
                self._last_hash = img_hash
                self._images = state.get("images", [])
                self._index = 0
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

        self._info_var.set(f"加载中... ({self._index + 1}/{len(self._images)})")
        # 在子线程下载，完成后回调主线程渲染
        url = self._images[self._index]
        threading.Thread(target=self._fetch_and_render, args=(url,), daemon=True).start()

    def _fetch_and_render(self, url: str) -> None:
        """子线程：下载图片，解码为 PhotoImage，再切回主线程显示"""
        data = download_image(url)
        if data is None:
            self.root.after(0, lambda: self._info_var.set("图片加载失败"))
            return

        try:
            from PIL import Image, ImageTk

            img = Image.open(BytesIO(data))
            # 缩放
            cw = self._canvas.winfo_width() or 400
            ch = self._canvas.winfo_height() or 360
            iw, ih = img.size
            scale = min(cw / iw, ch / ih, 1.0)
            new_w = max(1, int(iw * scale))
            new_h = max(1, int(ih * scale))
            img_resized = img.resize((new_w, new_h))
            photo = ImageTk.PhotoImage(img_resized)
        except ImportError:
            try:
                photo = tk.PhotoImage(data=data)
            except Exception:
                self.root.after(0, lambda: self._info_var.set("请安装 Pillow: pip install Pillow"))
                return
        except Exception:
            self.root.after(0, lambda: self._info_var.set("图片解码失败"))
            return

        # 切回主线程渲染
        self.root.after(0, lambda: self._render(photo))

    def _render(self, photo) -> None:
        """主线程：把 PhotoImage 挂到 Canvas 上"""
        self._photo = photo  # 防 GC
        self._canvas.delete("all")
        cw = self._canvas.winfo_width() or 400
        ch = self._canvas.winfo_height() or 360
        self._canvas.create_image(cw // 2, ch // 2, anchor="center", image=self._photo)
        self._info_var.set(f"📷 {self._index + 1}/{len(self._images)}  ← → 切换")

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
        url = self._images[self._index]
        threading.Thread(target=self._download_and_open, args=(url,), daemon=True).start()

    def _download_and_open(self, url: str) -> None:
        """子线程：下载图片并用系统查看器打开"""
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
