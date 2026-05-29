# Web Scraper 插件

基于 [Scrapling](https://github.com/D4Vinci/Scrapling) 的 Neo-MoFox 网页爬取插件。

## 功能

- **自动检测链接**：监听消息事件，自动识别用户发送的 URL 并爬取内容注入到 LLM 上下文
- **三级降级策略**：普通模式 → 隐身模式 → 动态模式，确保尽可能获取到网页内容
- **LLM 主动调用**：提供三个工具供 LLM 按需爬取网页

## 组件

| 类型 | 名称 | 说明 |
|------|------|------|
| EventHandler | `web_scraper_handler` | 自动检测消息中的链接并爬取 |
| Tool | `fetch_webpage` | 自动降级爬取（推荐） |
| Tool | `fetch_webpage_stealth` | 隐身模式，绕过 Cloudflare |
| Tool | `fetch_webpage_dynamic` | 动态模式，支持 JavaScript 渲染 |

## 安装

将 `web_scraper` 文件夹复制到 Neo-MoFox 的 `plugins` 目录。

框架会自动安装依赖，也可手动安装：

```bash
uv pip install "scrapling[fetchers]"
uv run playwright install
```

## 配置

配置文件位于 `config/plugins/web_scraper/config.toml`：

```toml
[scraper]
default_timeout = 30
max_content_length = 50000
enable_stealth = true
```

## 工作流程

### 自动模式

1. 用户发送包含链接的消息
2. EventHandler 检测到 URL
3. 依次尝试三种爬取模式
4. 将内容注入 system reminder
5. LLM 回复时可参考爬取内容

### 主动调用

LLM 可通过工具主动爬取指定 URL：

```
调用 fetch_webpage(url="https://example.com")
```

支持 CSS 选择器提取特定内容：

```
调用 fetch_webpage(url="https://example.com", css_selector=".content")
```

## 降级策略

| 模式 | 适用场景 | 技术 |
|------|----------|------|
| 普通 | 静态网页 | HTTP 请求 + TLS 指纹模拟 |
| 隐身 | 有反爬保护的网站 | Headless 浏览器 + Cloudflare 绕过 |
| 动态 | SPA / 需要 JS 渲染的网站 | 完整浏览器自动化 |

内容有效性判断：提取的文本长度 ≥ 100 字符才视为有效，否则继续尝试下一模式。

## 许可证

[AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html)
