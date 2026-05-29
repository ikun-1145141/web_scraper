"""web_scraper 工具组件 - 使用 Scrapling 爬取网页内容。"""

from __future__ import annotations

import asyncio
from typing import Annotated, Any, cast

from src.core.components import BaseTool
from src.kernel.logger import get_logger

logger = get_logger("web_scraper.tool")

MIN_CONTENT_LENGTH = 100


def _is_content_valid(text: str) -> bool:
    """检查爬取内容是否有效。"""
    if not text or len(text.strip()) < MIN_CONTENT_LENGTH:
        return False
    return True


def _truncate(text: str) -> str:
    """截断过长内容。"""
    if len(text) > 20000:
        return text[:20000] + "\n\n[内容过长，已截断]"
    return text


def _extract_page_text(page: Any, css_selector: str | None) -> str:
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


class FetchWebpageTool(BaseTool):
    """使用 Scrapling 爬取网页内容，自动降级尝试不同模式。"""

    tool_name: str = "fetch_webpage"
    tool_description: str = (
        "爬取指定URL的网页内容并返回文本。"
        "会依次尝试普通、隐身、动态三种模式，确保获取到内容。"
        "支持CSS选择器提取特定内容。"
    )

    async def execute(
        self,
        url: Annotated[str, "要爬取的网页URL"],
        css_selector: Annotated[
            str | None,
            "可选的CSS选择器，用于提取特定元素内容"
        ] = None,
    ) -> tuple[bool, str | dict]:
        """执行网页爬取，自动降级。"""

        try:
            from scrapling.fetchers import Fetcher, StealthyFetcher, DynamicFetcher
        except ImportError:
            return False, "Scrapling 未安装，请运行: pip install scrapling[fetchers]"

        # 1. 普通模式
        try:
            page = await asyncio.to_thread(Fetcher.get, url, timeout=20)
            text = _extract_page_text(page, css_selector)
            logger.info(f"[普通模式] URL={url}, 内容长度={len(text)}, 前300字符={repr(text[:300])}")
            if _is_content_valid(text):
                logger.info(f"普通模式爬取成功: {url}")
                return True, _truncate(text)
            logger.info(f"普通模式内容无效，继续尝试隐身模式: {url}")
        except Exception as e:
            logger.info(f"普通模式异常: {e}，继续尝试隐身模式")

        # 2. 隐身模式
        try:
            page = await asyncio.to_thread(
                StealthyFetcher.fetch,
                url,
                headless=True,
                solve_cloudflare=True,
            )
            text = _extract_page_text(page, css_selector)
            logger.info(f"[隐身模式] URL={url}, 内容长度={len(text)}, 前300字符={repr(text[:300])}")
            if _is_content_valid(text):
                logger.info(f"隐身模式爬取成功: {url}")
                return True, _truncate(text)
            logger.info(f"隐身模式内容无效，继续尝试动态模式: {url}")
        except Exception as e:
            logger.info(f"隐身模式异常: {e}，继续尝试动态模式")

        # 3. 动态模式
        try:
            page = await asyncio.to_thread(
                DynamicFetcher.fetch,
                url,
                headless=True,
                network_idle=True,
            )
            text = _extract_page_text(page, css_selector)
            logger.info(f"[动态模式] URL={url}, 内容长度={len(text)}, 前300字符={repr(text[:300])}")
            if _is_content_valid(text):
                logger.info(f"动态模式爬取成功: {url}")
                return True, _truncate(text)
            logger.warning(f"所有模式均未获取到有效内容: {url}")
            return False, f"所有爬取模式均未获取到有效内容，最后获取到的内容长度: {len(text)}"
        except Exception as e:
            logger.error(f"动态模式也失败: {e}")
            return False, f"所有爬取模式均失败: {str(e)}"


class FetchWebpageStealthTool(BaseTool):
    """使用 Scrapling StealthyFetcher 隐身模式爬取网页。"""

    tool_name: str = "fetch_webpage_stealth"
    tool_description: str = (
        "使用隐身模式爬取网页，可绕过 Cloudflare 等反爬保护。"
        "适用于有反爬机制的网站。"
    )

    async def execute(
        self,
        url: Annotated[str, "要爬取的网页URL"],
        css_selector: Annotated[
            str | None,
            "可选的CSS选择器，用于提取特定元素内容"
        ] = None,
        solve_cloudflare: Annotated[
            bool,
            "是否尝试自动解决 Cloudflare 验证"
        ] = True,
    ) -> tuple[bool, str | dict]:
        """执行隐身模式网页爬取。"""

        try:
            from scrapling.fetchers import StealthyFetcher
        except ImportError:
            return False, "Scrapling 未安装，请运行: pip install scrapling[fetchers]"

        try:
            page = await asyncio.to_thread(
                StealthyFetcher.fetch,
                url,
                headless=True,
                solve_cloudflare=solve_cloudflare,
            )
            text = _extract_page_text(page, css_selector)
            logger.info(f"[隐身模式] URL={url}, 内容长度={len(text)}, 前300字符={repr(text[:300])}")
            if _is_content_valid(text):
                return True, _truncate(text)
            return False, f"爬取内容为空或无效，内容长度: {len(text)}"
        except Exception as e:
            logger.error(f"隐身爬取失败: {e}")
            return False, f"隐身爬取失败: {str(e)}"


class FetchWebpageDynamicTool(BaseTool):
    """使用 Scrapling DynamicFetcher 动态加载爬取网页。"""

    tool_name: str = "fetch_webpage_dynamic"
    tool_description: str = (
        "使用浏览器动态加载爬取网页，支持 JavaScript 渲染。"
        "适用于需要 JavaScript 才能加载内容的网站。"
    )

    async def execute(
        self,
        url: Annotated[str, "要爬取的网页URL"],
        css_selector: Annotated[
            str | None,
            "可选的CSS选择器，用于提取特定元素内容"
        ] = None,
        network_idle: Annotated[
            bool,
            "是否等待网络空闲（确保页面完全加载）"
        ] = True,
    ) -> tuple[bool, str | dict]:
        """执行动态加载网页爬取。"""

        try:
            from scrapling.fetchers import DynamicFetcher
        except ImportError:
            return False, "Scrapling 未安装，请运行: pip install scrapling[fetchers]"

        try:
            page = await asyncio.to_thread(
                DynamicFetcher.fetch,
                url,
                headless=True,
                network_idle=network_idle,
            )
            text = _extract_page_text(page, css_selector)
            logger.info(f"[动态模式] URL={url}, 内容长度={len(text)}, 前300字符={repr(text[:300])}")
            if _is_content_valid(text):
                return True, _truncate(text)
            return False, f"爬取内容为空或无效，内容长度: {len(text)}"
        except Exception as e:
            logger.error(f"动态爬取失败: {e}")
            return False, f"动态爬取失败: {str(e)}"
