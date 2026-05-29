"""web_scraper 插件配置。"""

from src.app.plugin_system.base import BaseConfig, Field, SectionBase, config_section


class WebScraperConfig(BaseConfig):
    """网页爬取器插件配置。"""

    config_name = "config"
    config_description = "网页爬取器插件配置"

    @config_section("scraper")
    class ScraperSection(SectionBase):
        """爬虫配置。"""

        default_timeout: int = Field(
            default=30,
            description="默认请求超时时间（秒）"
        )
        max_content_length: int = Field(
            default=50000,
            description="返回内容的最大字符数"
        )
        enable_stealth: bool = Field(
            default=True,
            description="是否启用隐身模式绕过反爬"
        )

    scraper: ScraperSection = Field(default_factory=ScraperSection)
