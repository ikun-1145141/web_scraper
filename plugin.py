"""web_scraper - 使用 Scrapling 爬取网页内容的插件。

功能：
- 自动检测消息中的链接并爬取网页内容注入到 LLM 上下文
- 提供三种网页爬取工具供 LLM 主动调用：
  - 普通模式：使用 Fetcher 进行标准 HTTP 请求
  - 隐身模式：使用 StealthyFetcher 绕过反爬保护
  - 动态模式：使用 DynamicFetcher 支持 JavaScript 渲染
"""

from __future__ import annotations

from src.app.plugin_system.api.log_api import get_logger
from src.app.plugin_system.base import BasePlugin, register_plugin

from .config import WebScraperConfig
from .handler import WebScraperHandler
from .tool import FetchWebpageTool, FetchWebpageStealthTool, FetchWebpageDynamicTool

logger = get_logger("web_scraper")


@register_plugin
class WebScraperPlugin(BasePlugin):
    """网页爬取器插件。

    使用 Scrapling 库提供网页爬取能力，支持自动检测链接、普通请求、隐身模式和动态加载。
    """

    plugin_name: str = "web_scraper"
    plugin_description: str = "使用 Scrapling 爬取网页内容的插件"
    plugin_version: str = "1.0.0"

    configs: list[type] = [WebScraperConfig]
    dependent_components: list[str] = []

    def get_components(self) -> list[type]:
        """获取插件内所有组件类。

        Returns:
            list[type]: 组件列表
        """
        return [
            WebScraperHandler,
            FetchWebpageTool,
            FetchWebpageStealthTool,
            FetchWebpageDynamicTool,
        ]
