---
name: verified-web-research
description: 联网搜索并核验引用的工作流：只引用真正打开并读过的网页，每条关键论断附原文证据，用脚本批量检测链接是否失效（死链/软404/反爬拦截/登录墙）、抓取正文、给网页截图留证，并输出带可信度与时效标注的结构化回答；也可以对一份已有的 AI 回答或文档做"引用审计"。凡是用户要联网查资料、核实某个说法、检查回答里的网址能不能打开、担心 AI 编造链接或引用、要"带来源的答案"、要检查文档/报告里的引用是否靠谱，都应使用本技能——即使用户没有说"核验"或"验证"，只要答案会附网址或引用来源，就用它。
---

# Verified Web Research（搜索与引用核验）

## 这个技能解决什么问题

AI 联网搜索有三个常见失败：
1. **链接打不开**：URL 是凭记忆拼出来的，或早已失效。
2. **链接能打开但内容不支持论断**：只看了搜索摘要，没读正文；或把相关页面当成了支持证据。
3. **可信度是拍脑袋写的**："高/中/低"没有依据，多篇转载被算成多个独立来源，"没找到反证"被说成"没有反证"。

本技能把"搜索过""打开成功""读过正文""原文支持论断"当成四个不同的状态分别记录，最终回答只引用达到最后一个状态的来源；达不到的，明确说"未能核验"，而不是补全故事。

## 核心原则（为什么这样做）

- **搜索结果只是线索，不是证据。** 标题+摘要不能证明页面里有那句话。要引用一个页面，就要用 `fetch_page.py` 拿到正文（或截图）并真的读过相关段落。
- **URL 只能来自工具结果。** 搜索/抓取返回的 URL 才能进入回答；凭记忆写出的 URL 必须先 `check_links.py` + `fetch_page.py` 通过，否则不写。
- **HTTP 200 ≠ 内容可用，BLOCKED ≠ 死链。** 脚本会标出软 404、登录墙、JS 空壳页、反爬拦截。被拦截的页面换 `--browser` 或截图再试；仍不行就在回答里说明"未能读取"。
- **多个网址 ≠ 多份证据。** 十篇改写同一通稿的报道仍是一个来源。按"独立证据路径"分组计数（官方公告、一手采访、原始数据各算一组；转载不另算）。
- **可信度要有依据。** 由四件事决定：来源直接性（一手/二手）、独立来源组数、正文支持程度（原文直述/需推断）、时效。单一来源的说法最高只到"中"，除非它就是权威一手来源且无反证。
- **区分"官方这么说"和"已被证实"。** 厂商公告说"性能提升 2 倍"是 Reported，不是 Observed。
- **"未找到反证"要写检索范围。** 写成"在本次检索（X 个关键词、Y 个来源）中未见不同说法"，而不是"没有争议"。
- **时间要双标注。** 页面发布时间与访问时间分开记；每条时效敏感的论断写清"截至何时"。
- **存到磁盘 ≠ 已读。** 脚本把正文/截图存下来后，必须用读文件/看图片工具真正读过相关部分；截图尤其如此。

## 两种模式

| 模式 | 触发场景 | 输入 | 产出 |
|---|---|---|---|
| **研究模式** | 用户提问，需要联网查并给带来源的答案 | 问题 + 时间范围 | 结构化回答 + 来源表 + `web-evidence/` 证据目录 |
| **审计模式** | 用户给一份已有的 AI 回答/文档/报告，让检查引用 | 文本文件或粘贴内容 | 逐链接、逐论断的审计报告 + 修正建议 |

判断不清时：内容里已经有网址且用户在问"靠不靠谱/能不能打开/有没有编造"→ 审计模式；否则研究模式。

## 脚本速查

脚本都在本技能目录的 `scripts/` 下，纯标准库（截图与 `--browser` 需要 Playwright；没有时截图脚本自动退到本机 Edge/Chrome 无头模式）。用 `python scripts/xxx.py --help` 查看完整参数。

| 脚本 | 作用 | 典型用法 |
|---|---|---|
| `check_links.py` | 批量检测 URL：HEAD→GET 回退、软404/登录墙/反爬识别、Wayback 快照 | `python scripts/check_links.py URL1 URL2 --json web-evidence/links.json --wayback`；审计时 `--from-text answer.md` |
| `fetch_page.py` | 抓正文（含 PDF）存为 `pages/<ID>.md`，输出质量标记；`--find` 核对原文是否在页面上 | `python scripts/fetch_page.py URL --id S01 --out web-evidence --find "要引用的原句"`；JS 页面加 `--browser` |
| `screenshot.py` | 网页截图（视口 / 整页分段 / 定位句子并高亮 / 指定元素），同时保存渲染后文本 | `python scripts/screenshot.py URL --name S01 --out web-evidence/shots --find-text "关键句"` |
| `ledger.py` | 证据台账：登记来源、记录论断与原文、`validate` 找出"引用了但没读过""原文对不上""无来源"等问题 | `python scripts/ledger.py --out web-evidence validate` |

状态含义（`check_links.py`）：`OK` 可达；`OK_REDIRECTED` 跳转后可达（确认落点仍是目标页）；`SUSPECT_SOFT404` 200 但像错误页；`LOGIN_WALL` 登录页；`BLOCKED` 401/403/429 或人机验证——**服务器拒绝脚本，不是页面不存在**；`GONE` 404/410；`SERVER_ERROR` 5xx；`UNREACHABLE` 域名不解析/超时/SSL 失败。

## 研究模式流程

不必把每一步都展示给用户；这是内部工作流，用户看到的是最后的回答。但证据目录要留下。

### 0. 建目录、定范围
```
python scripts/ledger.py --out web-evidence init --question "用户的问题" --cutoff 2026-09-17
```
明确：要回答的具体问题、时间范围（用户给了就用，没给按问题性质定，并在回答里写出来）、什么算"一手来源"。

### 1. 找源头
用可用的联网搜索工具搜索。优先级：官方公告/文档 → 当事人原话 → 原始论文/数据/代码仓库 → 一手采访 → 可信媒体报道 → 其他。避免互相转载的二手文、无出处的自媒体总结、明显过时的页面。

每找到一个打算用的 URL，立即登记，并标出你判断的独立性分组：
```
python scripts/ledger.py --out web-evidence add-source URL --title "标题" --how search --kind primary --group official
```
多搜几个角度（中英文、不同关键词、"反对/质疑/争议/更正"类关键词），专门找反证，不要只搜能证实预设的词。

### 2. 打开并读正文
先批量检测，再逐个抓正文：
```
python scripts/check_links.py --file urls.txt --json web-evidence/links.json --wayback
python scripts/ledger.py --out web-evidence import-check web-evidence/links.json
python scripts/fetch_page.py URL --id S01 --out web-evidence --find "打算引用的原句"
python scripts/ledger.py --out web-evidence import-pages
```
看 `fetch_page.py` 输出的 `warnings`：
- `looks_like_js_shell` → 加 `--browser` 重抓。
- `looks_like_blocked` / `looks_like_login_wall` → 换 `screenshot.py`（浏览器渲染常能过普通反爬）；仍失败则记 `read: none`，回答里说明未能读取。
- `truncated` → 需要的段落可能在后面，`--max-chars 0` 重抓。
- PDF → 脚本会尝试 `pypdf` 抽文字；没装就提示安装或改截图。

然后**打开 `pages/S01.md` 读相关段落**。如果联网工具已经返回了足够完整的正文，可以不重复抓取，但仍要把该来源登记为 `--how fetch` 并记录读到了什么。

### 3. 截图（什么时候截）
截图是正文抓取的补充，不是替代。以下情况截图：
- 证据在图表、图片、表格排版或页面布局里，纯文本丢失了含义。
- 正文抓取失败或被拦截，但浏览器能渲染。
- 论断有争议、页面可能变动，需要一份带时间戳的可复查快照。
- 用户明确要"截图证据"。
```
python scripts/screenshot.py URL --name S01 --out web-evidence/shots --find-text "关键句"    # 定位并高亮该句
python scripts/screenshot.py URL --name S01 --out web-evidence/shots --selector "table"       # 只截某个元素
python scripts/screenshot.py URL --name S01 --out web-evidence/shots --full-page              # 整页，自动分段
```
截完**用看图工具打开 PNG 读一遍**，然后登记：`ledger.py set-source S01 --shot shots/S01.png --shot-text shots/S01.txt --read both`。小字、缩放后的图表可能看不清，看不清就说看不清，换 `--scale 2` 或 `--selector` 局部重截。

### 4. 逐条核验论断
把准备写进回答的每个关键说法拆成原子论断，逐条记录：
```
python scripts/ledger.py --out web-evidence add-claim "论断" --support S01,S03 --contra S02 \
  --quote "页面上的原句" --quote-from S01 --confidence medium --as-of 2026-09-10 --basis "官方公告直述；一组独立来源；无反证"
```
`--quote` 会自动核对原句是否真的出现在抓取的正文里；对不上就是改写或记错，去页面重新找。每条论断问四个问题：证据是哪几段原文？有没有来源给出不同说法？这条信息是什么时候的？多少个独立来源组？
可信度评定规则见 [references/confidence-rubric.md](references/confidence-rubric.md)。

### 5. 时效复查
写回答前，再搜一次"最近几天/官方更新/更正/撤回"类关键词：官方说法有没有更新？旧报道有没有被后续推翻？引用的数据是不是最新版本？有新信息就更新对应论断（`set-claim`），并在回答里指出哪里变了。

### 6. 校验并写回答
```
python scripts/ledger.py --out web-evidence validate
python scripts/ledger.py --out web-evidence render --cited-only
```
`validate` 报 ERROR 的必须处理：要么补证据，要么把该说法移到"不能确认"。回答格式见 [references/report-templates.md](references/report-templates.md)。要点：答案先行；只引用 `read` 不为 `none` 的来源；每个关键事实后附 `[S01]`；推测就写"这是推测"；资料不足就写资料不足。来源表来自 `render` 的输出，不要手工编号。

## 审计模式流程

1. 把待审内容存成文件（如 `answer.md`），建证据目录：`ledger.py init --question "审计: <文件名>"`。
2. 提取并检测全部链接：`check_links.py --from-text answer.md --json web-evidence/links.json --wayback`，然后 `ledger.py import-check web-evidence/links.json --add-missing`。
3. 逐个抓正文（`fetch_page.py`），BLOCKED/JS 页面用 `--browser` 或截图；`import-pages`。
4. 把待审内容里的论断与它所附的链接配对，逐条 `add-claim`，`--quote` 填待审内容声称的引文或最接近的原句。判定每条：**支持 / 部分支持 / 不支持 / 无法核验**（页面打不开或读不到）。"不支持"要说清是"页面没提到"还是"页面说法相反"。
5. 没有附链接的关键论断也列出来，标"无来源"。
6. `validate` 后按 [references/report-templates.md](references/report-templates.md) 的审计报告模板输出：链接健康汇总、逐条论断判定、修正建议（可替换的正确来源、应删除或改写的句子）。

## 常见陷阱

- 把 `BLOCKED` 当死链删掉一个其实正常的官方链接。先截图确认。
- 把 `OK` 当"已核验"。可达只说明服务器活着。
- 引用页面里"相关但不等于"的句子：页面说"计划在 Q4 推出"，回答写成"已推出"。`--quote` 对不上就是信号。
- 用一篇综述转述的数字代替原始论文的数字。找到原始出处再引；找不到就标"转引自 S0x"。
- 官方页面改版后旧 URL 跳转到首页（`OK_REDIRECTED` + "redirected to the site root"），内容其实已不在。
- 一个来源多次被引就以为证据充分。看独立组数。
- 忘记标日期，把 2023 年的价格/版本/政策当成现在的。
- 截了图但没看；或看了缩小到不可读的整页图就下结论。

## 环境

- Python 3.9+；四个脚本只用标准库。
- 可选：`pip install playwright` 后 `playwright install chromium`（或直接复用本机 Edge/Chrome，无需下载）→ 启用 `screenshot.py` 全部功能与 `fetch_page.py --browser`；`pip install pypdf` → PDF 抽文字。
- Windows 下脚本已强制 UTF-8 输出；路径含中文没问题。
- 证据目录默认 `./web-evidence/`（`ledger.json`、`links.json`、`pages/`、`shots/`、`raw/`）。可用 `--out` 改到用户指定位置。
- 网页读取常见问题（反爬、登录墙、软404、PDF、动态页、DNS 劫持）见 [references/troubleshooting.md](references/troubleshooting.md)。
