"""小黑盒数据获取层"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx
import urllib3

from hkey import build_request_url

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class Post:
    id: str
    title: str
    content: str
    author: str
    category: str
    like_count: int
    comment_count: int
    view_count: int
    create_time: int
    images: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


class HeyBoxClient:
    """小黑盒 API 客户端

    可用接口:
    - feeds: 动态流 (pull=0 推荐, pull=1 最新, 支持分页)
    - topic_categories: 话题分类

    暂不可用:
    - link_tree: 帖子详情 (触发验证码)
    - comment_list: 评论列表 (接口已变更)
    """

    def __init__(self) -> None:
        self._client = httpx.Client(
            timeout=15.0,
            verify=False,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.xiaoheihe.cn/",
                "Origin": "https://www.xiaoheihe.cn",
            },
        )
        self._last_request_time = 0.0
        self._min_interval = 1.0
        self._max_retries = 3

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def _get(self, route: str, params: dict | None = None) -> dict:
        url = build_request_url(route, params)
        last_error = None
        for attempt in range(self._max_retries):
            self._throttle()
            try:
                resp = self._client.get(url)
                resp.raise_for_status()
                data = resp.json()
                status = data.get("status")
                if status == "show_captcha":
                    raise RuntimeError("触发验证码，请稍后再试")
                if status != "ok":
                    raise RuntimeError(f"API 错误: status={status}, msg={data.get('msg', '')}")
                return data.get("result", data)
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"连接失败，重试 {self._max_retries} 次后仍报错: {last_error}")

    def get_feeds(self, offset: int = 0, pull: int = 0) -> tuple[list[Post], int]:
        """获取动态流帖子列表

        Args:
            offset: 分页偏移量
            pull: 0=推荐, 1=最新
        """
        result = self._get("feeds", {"offset": str(offset), "pull": str(pull)})
        links = result.get("links", [])
        posts = [p for item in links if (p := self._parse_post(item)) is not None]
        return posts, len(links)

    def get_topic_categories(self) -> list[dict]:
        """获取话题分类"""
        result = self._get("topic_categories")
        categories = result.get("list", result.get("categories", []))
        return categories if isinstance(categories, list) else []

    @staticmethod
    def _parse_post(item: dict) -> Post | None:
        if not item:
            return None
        try:
            post_id = str(item.get("linkid", item.get("link_id", "")))
            title = item.get("title", "")
            content = item.get("description", item.get("text", item.get("content", "")))

            user_obj = item.get("user", {})
            if isinstance(user_obj, dict):
                author = user_obj.get("username", user_obj.get("nickname", "匿名"))
            else:
                author = "匿名"

            topics = item.get("topics", [])
            if isinstance(topics, list) and topics:
                topic = topics[0] if isinstance(topics[0], dict) else {}
                category = topic.get("name", "")
            else:
                category = item.get("category", "")
                if isinstance(category, dict):
                    category = category.get("name", "")

            imgs = item.get("imgs", item.get("images", []))
            images = []
            for img in imgs:
                if isinstance(img, dict):
                    images.append(img.get("url", img.get("thumb", "")))
                elif isinstance(img, str):
                    images.append(img)

            hashtags = item.get("hashtags", item.get("tags", []))
            tags = []
            for h in hashtags:
                if isinstance(h, dict):
                    tags.append(h.get("name", h.get("title", "")))
                elif isinstance(h, str):
                    tags.append(h)

            return Post(
                id=post_id,
                title=title or "(无标题)",
                content=content or "",
                author=author,
                category=category,
                like_count=item.get("link_award_num", item.get("like_num", 0)),
                comment_count=item.get("comment_num", 0),
                view_count=item.get("view_num", item.get("down", 0)),
                create_time=item.get("create_at", item.get("create_time", 0)),
                images=images,
                tags=tags,
            )
        except Exception:
            return None
