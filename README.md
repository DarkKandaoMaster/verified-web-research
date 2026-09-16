# verified-web-research

这是一个约束 AI 联网搜索的 Agent Skill，负责搜索之后的读取、核对与记录，解决三个常见问题：AI 给的网址打不开；网址能打开但内容并不支持它说的话；多篇转载被当成多个独立来源。

配套四个纯标准库 Python 脚本（链接检测、正文抓取、网页截图、证据台账）。

工作方式：
1. 检测链接是否有效
2. 抓取正文并核对引文是否出现在页面上
3. 截图留证
4. 将来源与论断记入证据台账并自动校验

## skill目录

```
verified-web-research/
├── SKILL.md                     # 给模型的工作流：研究模式 / 审计模式
├── scripts/
│   ├── check_links.py           # 批量检测 URL：死链 / 软404 / 登录墙 / 反爬拦截 / Wayback
│   ├── fetch_page.py            # 抓正文（含 PDF）、核对引文是否在页面上
│   ├── screenshot.py            # 截图：定位句子高亮 / 指定元素 / 整页分段；无 Playwright 时退到 Edge/Chrome CLI
│   └── ledger.py                # 证据台账：来源、论断、原文核对、validate、render
└── references/
    ├── confidence-rubric.md     # 可信度怎么定、独立来源怎么数、时间怎么标
    ├── report-templates.md      # 回答模板、审计报告模板
    └── troubleshooting.md       # 反爬 / JS 页 / 付费墙 / PDF / DNS 劫持等处理
```

## 安装

把 `verified-web-research/` 整个文件夹（打开后能看到 SKILL.md 的那个文件夹）复制到你的 skills 目录。

## 依赖

- Python 3.9+。四个脚本只用标准库，开箱即用。
- 可选：`pip install playwright && playwright install chromium`（本机有 Edge/Chrome 时可跳过下载，脚本会自动复用）→ 网页截图全部功能、JS 页面渲染抓取。
- 可选：`pip install pypdf` → PDF 抽文字。
