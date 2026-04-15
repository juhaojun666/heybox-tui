"""小黑盒摸鱼 TUI

在终端中浏览小黑盒社区帖子，摸鱼神器。

配合 viewer.py 使用：TUI 切帖子时，图片查看器自动更新。

快捷键:
  1/2  - 切换 推荐/最新
  n/p  - 下一页/上一页
  r    - 刷新
  Enter - 查看帖子详情
  Esc  - 返回列表
  q    - 退出
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from datetime import datetime
from pathlib import Path

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static

from client import HeyBoxClient, Post
from config import get_credential, is_logged_in, save_config

# 与 viewer.py 共享的状态文件
VIEWER_STATE_FILE = Path(tempfile.gettempdir()) / "heybox_viewer_state.json"


def _notify_viewer(post: Post) -> None:
    """通知图片查看器更新，如果没在运行则启动"""
    state = {
        "images": post.images,
        "title": post.title,
        "hash": hashlib.md5(post.id.encode()).hexdigest(),
    }
    VIEWER_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    # 检查 viewer 是否还在运行，不在则重启
    if post.images:
        _ensure_viewer_running()


def _ensure_viewer_running() -> None:
    """确保 viewer 进程在运行"""
    import subprocess
    import sys

    # 用锁定文件检测 viewer 是否存活
    lock_file = Path(tempfile.gettempdir()) / "heybox_viewer.lock"
    if lock_file.exists():
        try:
            pid = int(lock_file.read_text().strip())
            # 检查进程是否还在
            import os
            try:
                os.kill(pid, 0)
                return  # 进程还活着
            except (OSError, ProcessLookupError):
                pass
        except (ValueError, OSError):
            pass

    # viewer 没在运行，启动它
    viewer_path = Path(__file__).parent / "viewer.py"
    if viewer_path.exists():
        try:
            subprocess.Popen(
                [sys.executable, str(viewer_path)],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception:
            pass


def format_time(ts: int) -> str:
    if not ts:
        return ""
    try:
        dt = datetime.fromtimestamp(ts)
        diff = (datetime.now() - dt).total_seconds()
        if diff < 60:
            return "刚刚"
        if diff < 3600:
            return f"{int(diff / 60)}分钟前"
        if diff < 86400:
            return f"{int(diff / 3600)}小时前"
        if diff < 604800:
            return f"{int(diff / 86400)}天前"
        return dt.strftime("%m-%d %H:%M")
    except Exception:
        return ""


class PostItem(ListItem):
    def __init__(self, post: Post) -> None:
        super().__init__()
        self.post = post

    def compose(self) -> ComposeResult:
        p = self.post
        cat = f"[{p.category}] " if p.category else ""
        title_text = f"{cat}{p.title}"
        meta = f"  {p.author}  👍{p.like_count}  💬{p.comment_count}  {format_time(p.create_time)}"
        yield Label(Text(title_text, style="bold"))
        yield Label(Text(meta, style="dim"))


class PostDetail(VerticalScroll):
    def show_post(self, post: Post) -> None:
        self.remove_children()
        cat = f"[{post.category}] " if post.category else ""
        self.mount(Static(Text(f"\n{cat}{post.title}\n", style="bold cyan")))
        meta = (
            f"  {post.author}    "
            f"👍 {post.like_count}    "
            f"💬 {post.comment_count}    "
            f"🕐 {format_time(post.create_time)}"
        )
        self.mount(Static(Text(meta, style="yellow")))
        if post.tags:
            tags = "  ".join(f"#{t}" for t in post.tags if t)
            self.mount(Static(Text(f"\n{tags}\n", style="green")))
        self.mount(Static(Text("─" * 50, style="dim")))
        content = post.content.strip()
        if content:
            self.mount(Static(Text(f"\n{content}\n")))
        if post.images:
            self.mount(Static(Text(f"📷 {len(post.images)}张图片 (查看器自动显示)", style="cyan")))
        self.mount(Static(Text("\n按 Esc 返回列表", style="dim italic")))
        self.scroll_home(animate=False)


class HeyBoxApp(App):
    TITLE = "小黑盒摸鱼"
    SUB_TITLE = "heybox-tui"
    CSS = """
    Screen {
        layout: horizontal;
    }

    #sidebar {
        width: 1fr;
        min-width: 28;
        max-width: 55;
        border-right: solid $primary;
    }

    #detail {
        width: 2fr;
        padding: 0 1;
    }

    PostItem {
        padding: 1 1;
    }

    PostItem :hover {
        background: $surface;
    }

    .placeholder {
        text-align: center;
        padding: 4 2;
        color: $text-muted;
    }

    #tab-bar {
        height: 1;
        dock: top;
        padding: 0 1;
    }

    #page-info {
        height: 1;
        dock: bottom;
        padding: 0 1;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "退出"),
        Binding("r", "refresh", "刷新"),
        Binding("1", "tab_recommend", "推荐"),
        Binding("2", "tab_latest", "最新"),
        Binding("n", "next_page", "下一页"),
        Binding("p", "prev_page", "上一页"),
        Binding("esc", "go_back", "返回"),
    ]

    current_tab: reactive[str] = reactive("recommend")
    is_loading: reactive[bool] = reactive(False)

    def __init__(self) -> None:
        super().__init__()
        self.client = HeyBoxClient()
        self._all_posts: list[Post] = []
        self._offset = 0
        self._page_size = 10
        self._current_post: Post | None = None

    def on_mount(self) -> None:
        self.sub_title = f"heybox-tui {'[已登录]' if self.client.is_logged_in else '[未登录]'}"

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label(self._tab_label(), id="tab-bar")
                yield ListView(id="post-list")
                yield Label("", id="page-info")
            with PostDetail(id="detail"):
                yield Label(
                    "← 选择帖子查看详情\n\n"
                    "快捷键:\n"
                    "  1/2    切换 推荐/最新\n"
                    "  n/p    下一页/上一页\n"
                    "  r      刷新\n"
                    "  Enter  查看详情\n"
                    "  Esc    返回列表\n"
                    "  q      退出\n\n"
                    "提示: 运行 python viewer.py 可打开配套图片查看器\n\n"
                    f"{'已登录 ✓' if self.client.is_logged_in else '未登录 — 配置 ~/.heybox-tui/config.json 可获得个性化推荐'}",
                    classes="placeholder",
                )
        yield Footer()

    def _tab_label(self) -> Text:
        tabs = {"recommend": "推荐", "latest": "最新"}
        parts: list[Text] = []
        for key, name in tabs.items():
            style = "bold reverse" if key == self.current_tab else ""
            parts.append(Text(f" {name} ", style=style))
            parts.append(Text("  "))
        return Text.assemble(*parts)

    def _update_page_info(self) -> None:
        page = self._offset // self._page_size + 1
        info = f"第 {page} 页 | 共 {len(self._all_posts)} 条"
        try:
            self.query_one("#page-info", Label).update(info)
        except Exception:
            pass

    def _watch_current_tab(self) -> None:
        try:
            self.query_one("#tab-bar", Label).update(self._tab_label())
        except Exception:
            pass
        self._offset = 0
        self._all_posts = []
        self._load_posts()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, PostItem):
            self._current_post = event.item.post
            self.query_one("#detail", PostDetail).show_post(event.item.post)
            _notify_viewer(event.item.post)

    def action_tab_recommend(self) -> None:
        self.current_tab = "recommend"

    def action_tab_latest(self) -> None:
        self.current_tab = "latest"

    def action_refresh(self) -> None:
        self._offset = 0
        self._all_posts = []
        self._load_posts()

    def action_next_page(self) -> None:
        if not self.is_loading:
            self._offset += self._page_size
            self._load_posts(append=True)

    def action_prev_page(self) -> None:
        if self._offset > 0 and not self.is_loading:
            self._offset = max(0, self._offset - self._page_size)
            self._all_posts = []
            self._load_posts()

    def action_go_back(self) -> None:
        self.query_one("#post-list", ListView).focus()

    @work(exclusive=True, thread=True)
    async def _load_posts(self, append: bool = False) -> None:
        if self.is_loading:
            return
        self.is_loading = True
        try:
            pull = 0 if self.current_tab == "recommend" else 1
            new_posts, _ = self.client.get_feeds(offset=self._offset, pull=pull)

            if append:
                self._all_posts.extend(new_posts)
            else:
                self._all_posts = new_posts

            self.call_from_thread(self._update_list)
        except Exception as e:
            self.call_from_thread(self._show_error, str(e))
        finally:
            self.is_loading = False

    def _update_list(self) -> None:
        post_list = self.query_one("#post-list", ListView)
        post_list.clear()
        if not self._all_posts:
            post_list.append(ListItem(Label(Text("暂无数据，按 r 刷新", style="dim"))))
        else:
            for post in self._all_posts:
                post_list.append(PostItem(post))
            post_list.focus()
        self._update_page_info()

    def _show_error(self, msg: str) -> None:
        detail = self.query_one("#detail", PostDetail)
        detail.remove_children()
        detail.mount(Static(Text(f"\n加载失败: {msg}\n按 r 重试", style="bold red")))


def main():
    import subprocess
    import sys
    from pathlib import Path

    # 自动启动图片查看器
    viewer_path = Path(__file__).parent / "viewer.py"
    if viewer_path.exists():
        try:
            subprocess.Popen(
                [sys.executable, str(viewer_path)],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception:
            pass

    app = HeyBoxApp()
    app.run()


if __name__ == "__main__":
    main()
