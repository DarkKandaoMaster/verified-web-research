# 网页读取常见问题

按症状查。原则：换一种读取方式再试一次；仍失败就如实记录"未能读取"，不要用搜索摘要冒充正文。

## 症状 → 处理

| 症状 | 通常原因 | 处理 |
|---|---|---|
| `check_links` 报 `BLOCKED`（401/403/429） | 反爬、Cloudflare 人机验证、需要登录、限流 | 先 `screenshot.py`（真实浏览器内核常能通过）；429 等 30–60 秒再试；仍失败记 `read: none`，回答里写"该来源拒绝自动访问，未能读取" |
| `fetch_page` `looks_like_js_shell`（正文极短、脚本很多） | 单页应用，内容由 JS 渲染 | `fetch_page.py URL --browser`；或 `screenshot.py`（会同时存渲染后文本 `.txt`） |
| `looks_like_login_wall` | 付费墙 / 登录墙 | 找同一内容的公开版本（作者主页、预印本、官方新闻稿、Wayback）；找不到就标"付费墙后内容未读取"。不要绕过登录 |
| `SUSPECT_SOFT404` / `OK_REDIRECTED` 且 "redirected to the site root" | 页面已删，服务器把旧链接跳到首页 | 站内搜索原标题；`--wayback` 查快照；快照可以作为"当时存在"的证据，但要注明是存档 |
| `GONE` (404/410) | 链接失效或从未存在 | `--wayback` 有快照 → 说明曾存在，可引存档并注明；无快照 + 域名/路径可疑 → 很可能是编造的 URL，**不要引用**，去找真实来源 |
| `UNREACHABLE` + "DNS failure" | 域名不存在 | 编造 URL 的典型信号。注意有些网络会把不存在的域名劫持到广告页，这时会表现为 SSL 错误或 `SUSPECT_SOFT404`，同样按不存在处理 |
| `UNREACHABLE` + Timeout/SSL | 网络问题、地域封锁、证书问题 | 换 `--timeout 40` 重试一次；`screenshot.py`（浏览器有自己的证书链）；仍失败记录为"本次无法访问"，不要判死 |
| 正文抓到了但 `truncated: true` | 页面很长 | `--max-chars 0` 重抓；或 `--find` 直接核对目标句是否在完整文本中 |
| `--find` 对不上 | 引文是改写/翻译；页面是另一个版本；文本被截断 | 打开 `pages/<ID>.md` 搜关键词；看 `match_ratio` 和 `missing`；改写的引文要在回答里改回原句或写"大意" |
| PDF 没有文字 | 未装 `pypdf`；或 PDF 是扫描件 | `pip install pypdf`；扫描件用 `screenshot.py`（Chromium 内置 PDF 查看器）或告知用户需要 OCR |
| 内容在图表/表格里 | 文本抽取丢失结构 | `screenshot.py --selector "table"` 或 `--find-text "表格标题"`；看图时留意坐标轴、图例、单位 |
| 整页截图字太小看不清 | 页面太长被缩小 | 脚本默认按 1800px 分段；仍不清用 `--scale 2` 或 `--find-text` 只截相关区域 |
| 页面内容与搜索摘要不一致 | 摘要来自旧版本缓存 | 以当前页面为准，并在回答里注明"搜索摘要显示 X，实际页面（访问于 …）为 Y" |
| 同一 URL 不同时间内容不同 | 页面更新 | 以你访问时的版本为准，记录 `accessed` 和 `published`；争议内容截图留档 |
| 页面是聚合页 / 内容农场 / AI 生成 | 三手来源 | 顺着它的链接找原始出处；找不到就不引用 |
| 页面语言与问题语言不同 | — | 正常引用；`--quote` 用页面原语言的原句，回答里可附译文并标"译" |

## 什么情况下应该放弃并如实说明

- 三种方式（HTTP 抓取、`--browser`、截图）都失败。
- 内容在付费墙/登录后。
- 页面需要交互（点击展开、验证码）才能显示关键内容。

写法示例：
> S06（Reuters 报道）在本次检索中被反爬拦截，截图也仅显示验证页，未能读取正文；以下引用仅基于搜索摘要标题，**未经正文核验**。

## Playwright 安装提示

```
pip install playwright
playwright install chromium        # 下载浏览器（约 150MB）
```
如果本机已有 Edge 或 Chrome，`screenshot.py` 和 `fetch_page.py --browser` 会自动通过 `msedge`/`chrome` 通道复用它，无需下载。完全没有 Playwright 时，`screenshot.py` 会退到本机 Edge/Chrome 的命令行无头模式：能截视口，但不支持 `--find-text`/`--selector`/整页分段，也拿不到最终 URL 与标题。
