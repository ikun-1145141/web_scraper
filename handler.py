"""web_scraper 事件处理器 - 自动检测消息中的链接并爬取。"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from src.core.components import BaseEventHandler, EventType
from src.kernel.event import EventDecision
from src.kernel.logger import get_logger

logger = get_logger("web_scraper.handler")

URL_PATTERN = re.compile(
    r'https?://[^\s<>"\')\]]+',
    re.IGNORECASE,
)

MIN_CONTENT_LENGTH = 100


class WebScraperHandler(BaseEventHandler):
    """自动检测消息中的链接并爬取网页内容。"""

    handler_name: str = "web_scraper_handler"
    handler_description: str = "自动检测消息中的链接并爬取网页内容"
    weight: int = -10
    intercept_message: bool = False
    init_subscribe: list[EventType | str] = [EventType.ON_MESSAGE_RECEIVED]

    async def execute(
        self, event_name: str, params: dict[str, Any]
    ) -> tuple[EventDecision, dict[str, Any]]:
        """处理消息事件，检测链接并爬取。"""

        message = params.get("message")
        if message is None:
            return EventDecision.PASS, params

        text = ""
        if hasattr(message, "processed_plain_text") and message.processed_plain_text:
            text = message.processed_plain_text
        elif hasattr(message, "content") and isinstance(message.content, str):
            text = message.content

        if not text:
            return EventDecision.PASS, params

        urls = URL_PATTERN.findall(text)
        if not urls:
            return EventDecision.PASS, params

        urls = list(dict.fromkeys(urls))[:3]

        logger.info(f"检测到 {len(urls)} 个链接，开始爬取")

        scraped_contents = []
        for url in urls:
            try:
                content = await self._scrape_url(url)
                if content:
                    scraped_contents.append(f"[{url}]\n{content}")
            except Exception as e:
                logger.warning(f"爬取 {url} 失败: {e}")

        if scraped_contents:
            reminder_content = (
                "以下是从用户消息中的链接爬取到的网页内容，"
                "请根据这些内容来回应用户：\n\n"
                + "\n\n---\n\n".join(scraped_contents)
            )

            from src.app.plugin_system.api.prompt_api import add_system_reminder

            add_system_reminder(
                bucket="actor",
                name="web_scraper_content",
                content=reminder_content,
            )
            logger.info(f"已注入 {len(scraped_contents)} 个网页的爬取内容")

        return EventDecision.SUCCESS, params

    def _is_content_valid(self, text: str) -> bool:
        """检查爬取内容是否有效。"""
        if not text or len(text.strip()) < MIN_CONTENT_LENGTH:
            return False
        return True

    def _extract_page_text(self, page: Any, css_selector: str | None = None) -> str:
        """从页面提取完整文本内容。"""
        try:
            if css_selector:
                elements = page.css(css_selector)
                texts = []
                for elem in elements:
                    t = elem.get_all_text(separator="\n", strip=True)
                    if t:
                        texts.append(str(t))
                return "\n".join(texts)

            body = page.css("body")
            if body:
                text = body[0].get_all_text(separator="\n", strip=True)
                if text:
                    return str(text)

            text = page.get_all_text(separator="\n", strip=True)
            if text:
                return str(text)

            return page.text or ""
        except Exception as e:
            logger.warning(f"提取文本异常: {e}")
            return page.text or ""

    def _truncate(self, text: str) -> str:
        """截断过长内容。"""
        if len(text) > 20000:
            return text[:20000] + "\n\n[内容过长，已截断]"
        return text

    async def _scrape_url(self, url: str) -> str:
        """爬取单个URL的内容，依次尝试普通、隐身、动态模式。"""

        # 1. 普通模式
        try:
            from scrapling.fetchers import Fetcher

            page = await asyncio.to_thread(
                Fetcher.get, url, timeout=20
            )

            text = self._extract_page_text(page)
            logger.info(f"[普通模式] URL={url}, 内容长度={len(text)}, 前300字符={repr(text[:300])}")
            if self._is_content_valid(text):
                logger.info(f"普通模式爬取成功: {url}")
                return self._truncate(text)

            logger.info(f"普通模式内容无效，继续尝试隐身模式: {url}")
        except ImportError:
            logger.error("Scrapling 未安装")
            return ""
        except Exception as e:
            logger.info(f"普通模式异常: {e}，继续尝试隐身模式")

        # 2. 隐身模式
        try:
            from scrapling.fetchers import StealthyFetcher

            page = await asyncio.to_thread(
                StealthyFetcher.fetch,
                url,
                headless=True,
                solve_cloudflare=True,
            )

            text = self._extract_page_text(page)
            logger.info(f"[隐身模式] URL={url}, 内容长度={len(text)}, 前300字符={repr(text[:300])}")
            if self._is_content_valid(text):
                logger.info(f"隐身模式爬取成功: {url}")
                return self._truncate(text)

            logger.info(f"隐身模式内容无效，继续尝试动态模式: {url}")
        except Exception as e:
            logger.info(f"隐身模式异常: {e}，继续尝试动态模式")

        # 3. 动态模式
        try:
            from scrapling.fetchers import DynamicFetcher

            page = await asyncio.to_thread(
                DynamicFetcher.fetch,
                url,
                headless=True,
                network_idle=True,
            )

            text = self._extract_page_text(page)
            logger.info(f"[动态模式] URL={url}, 内容长度={len(text)}, 前300字符={repr(text[:300])}")
            if self._is_content_valid(text):
                logger.info(f"动态模式爬取成功: {url}")
                return self._truncate(text)

            logger.warning(f"所有模式均未获取到有效内容: {url}")
            return ""
        except Exception as e:
            logger.error(f"动态模式也失败: {e}")
            return ""
