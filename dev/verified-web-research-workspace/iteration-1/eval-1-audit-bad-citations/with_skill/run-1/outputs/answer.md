# 引用审计：python313_answer.md（Python 3.13 新特性简述）

审计时间：2026-09-16 18:06 UTC。共提取 6 个链接、7 条附链接的关键论断、0 条无来源的关键论断。

**一句话结论**：6 个链接里 4 个能打开、2 个是不存在的页面（404，且 Wayback Machine 从未收录，基本可断定是编造的 URL）。7 条论断里 4 条完全成立、1 条基本成立但数字引错了出处、**2 条是错的**——"JIT 提速 2–3 倍"与所引 PEP 的原话相反，"asyncio 默认事件循环改为 uvloop"是无中生有。

## 1. 链接健康

| # | 链接 | 状态 | 说明 |
|---|---|---|---|
| [1] | https://www.python.org/downloads/release/python-3130/ | OK (200) | 已读正文（S01） |
| [2] | https://docs.python.org/3/whatsnew/3.13.html | OK (200) | 已读正文（S02） |
| [3] | https://peps.python.org/pep-0744/ | OK (200) | 已读正文（S03） |
| [4] | https://peps.python.org/pep-0594/ | OK (200) | 已读正文（S04） |
| [5] | https://docs.python.org/3/whatsnew/3.13/repl-improvements.html | **GONE (404)** | 页面不存在；Wayback 无任何历史快照。What's New 并没有这样的子页面，REPL 内容其实是 [2] 页面里的一个小节（S05） |
| [6] | https://docs.python.org/3/library/asyncio-uvloop.html | **GONE (404)** | 页面不存在；Wayback 无任何历史快照。Python 官方文档从来没有 asyncio-uvloop 这一页（uvloop 是第三方库）（S06） |

汇总：OK 4，GONE 2（两个 404 均无存档，属"凭记忆拼出来的 URL"）。

## 2. 逐条论断

| # | 原文中的论断 | 所附来源 | 判定 | 依据 |
|---|---|---|---|---|
| C01 | Python 3.13 于 2024 年 10 月 7 日正式发布 | [1] S01 | **支持** | 发布页原句："Release date: Oct. 7, 2024" |
| C02 | 引入实验性的自由线程模式（可选关闭 GIL） | [2] S02 | **支持** | What's New 原句："PEP 703: CPython 3.13 has experimental support for running with the global interpreter lock disabled." 发布页 S01 也写明 "An experimental free-threaded build mode, which disables the Global Interpreter Lock" |
| C03 | 引入一个实验性的 JIT 编译器 | [3] S03 | **支持** | PEP 744 原句："Until the JIT is non-experimental, it should not be used in production, and may be broken or removed at any time without warning."；S02："PEP 744: A basic JIT compiler was added." |
| C04 | 官方称 JIT 使大多数工作负载提速 2–3 倍 | [3] S03 | **不支持（页面说法相反）** | PEP 744 原句："Currently, the JIT is about as fast as the existing specializing interpreter on most platforms."（目前 JIT 在大多数平台上和现有解释器速度相当）。同页还写，JIT 要"脱离实验状态"的门槛只是 "a meaningful performance improvement for at least one popular platform (realistically, on the order of 5%)"。What's New（S02）也说 "Performance improvements are modest"。页面里根本没有 "2-3x" 字样（`--find "2-3x"` 未命中）。 |
| C05 | 移除了 19 个 "dead batteries" 标准库模块，包括 cgi、telnetlib、imghdr 等 | [4] S04 | **部分支持** | PEP 594 确实写 3.13 "All modules deprecated by this PEP are removed…"，且表格里 cgi、telnetlib、imghdr 都标为 "To be removed: 3.13"。但 **"19 个"这个数字不在 PEP 594 页面上**：PEP 的表格共列 22 个模块，其中 asynchat、asyncore、smtpd 三个已在 3.12 移除。"19" 出自 What's New（S02）原句："PEP 594: The remaining 19 'dead batteries' (legacy stdlib modules) have been removed from the standard library: aifc, audioop, cgi, cgitb, chunk, crypt, imghdr, mailcap, msilib, nis, nntplib, ossaudiodev, pipes, sndhdr, spwd, sunau, telnetlib, uu and xdrlib." 结论：说法正确，出处应改为 [2]。 |
| C06 | 默认 REPL 换成源自 PyPy 的新交互式解释器，支持多行编辑和彩色提示 | [5] S05 | **无法核验（所附链接不存在）；说法本身成立** | 链接 404 且无快照，无法作为证据。但 What's New（S02）"A better interactive interpreter" 一节原句："Python now uses a new interactive shell by default, based on code from the PyPy project." 并列出 "Multiline editing with history preservation" 与 "Prompts and tracebacks with color enabled by default"；发布页 S01 亦有同样表述。结论：内容对，链接是编的。 |
| C07 | 3.13 将 asyncio 的默认事件循环改为 uvloop | [6] S06 | **不支持（链接不存在 + 官方文档说法相反）** | 链接 404 且无快照。3.13 官方 asyncio 文档（补充来源 S07）原句："asyncio ships with two different event loop implementations: SelectorEventLoop and ProactorEventLoop." 以及 "By default asyncio is configured to use EventLoop."；Windows 上 "ProactorEventLoop, the default event loop on Windows"。What's New（S02）asyncio 小节列出的全部改动里没有一处提到 uvloop；四个可读页面加 S07 全文均无 "uvloop" 字样。uvloop 一直是第三方 PyPI 包，需要用户自己通过 `asyncio.Runner(loop_factory=uvloop.new_event_loop)` 之类方式启用。 |

判定标准：支持＝原文直述；部分支持＝方向一致但程度/数字/出处不同；不支持＝页面没提或说法相反；无法核验＝读不到页面。

## 3. 修正建议

- **C04（JIT 提速 2–3 倍）：删除或改写。** 建议改为："官方称 JIT 目前在大多数平台上与现有的专用化解释器速度相当，性能提升有限（modest），后续版本才会逐步改进[3][2]。" 不要保留 "2–3 倍"——这不是官方说过的话，找不到任何官方出处。
- **C07（asyncio 默认 uvloop）：整句删除。** 这条既没有来源也与官方文档相反。若要保留 asyncio 相关内容，可改为 3.13 实际的 asyncio 变化（如 `asyncio.as_completed()` 改动、`Queue.shutdown`、`TaskGroup` 取消行为改进等），引用 [2]；如要提 uvloop，只能说"uvloop 是第三方可选的事件循环实现"，引 https://docs.python.org/3.13/library/asyncio-eventloop.html（S07）说明默认实现是 SelectorEventLoop / ProactorEventLoop。
- **C06 的引用 [5]：替换。** 把 `https://docs.python.org/3/whatsnew/3.13/repl-improvements.html` 换成 `https://docs.python.org/3/whatsnew/3.13.html#a-better-interactive-interpreter`（已验证可打开，HTTP 200）；或直接并入 [2]。
- **C05 的 "19 个"：出处改为 [2]。** PEP 594 [4] 可以继续作为"哪些模块、为什么移除"的来源，但 "19 个" 与完整名单应引 What's New。
- 引用 [6] 删除（页面不存在）。
- 顺带一提：本次审计时 3.13.0 已被 3.13.15 取代（发布页顶部提示 "Python 3.13.0 has been superseded by Python 3.13.15"），如文中要给版本号建议写清"3.13.0 首发于 2024-10-07"。

## 4. 总体评价

这份回答的骨架是对的——发布日期、自由线程、实验性 JIT、dead batteries、新 REPL 五个要点都能在官方一手来源里找到直述，前四个链接也都是真实、恰当的官方页面。问题集中在两类：

1. **编造 URL**：[5] 和 [6] 都是"看起来很像官方文档"的路径，但从未存在过（Wayback 也从未收录）。[5] 至少内容是对的，只是链接指错；[6] 则是连内容都是编的。
2. **过度解读/无中生有的数字与结论**：把 "JIT 目前与解释器速度相当" 说成 "提速 2–3 倍"，方向完全相反，而且还挂在恰恰反驳它的 PEP 744 上；"默认事件循环改为 uvloop" 没有任何依据。

受影响的结论：读者若据此认为 3.13 的 JIT 能带来 2–3 倍性能、或升级到 3.13 就自动得到 uvloop，都是错误预期。其余四条（C01、C02、C03、C06 的内容）可放心使用；C05 只需改出处。

检索范围说明：本次共打开 5 个官方页面并读取正文（S01–S04、S07），未做截图（页面均为纯文本文档，正文抓取无拦截、无截断）；另用一次网页搜索（关键词 "Python 3.13 asyncio default event loop uvloop"）核对 C07，搜索结果同样指向 uvloop 为第三方替代实现，未见任何来源称其成为默认。所有可信度评级只依赖官方一手来源（1 组独立来源），这在"官方是否这样说"的问题上是足够的。

## 来源

- [S01] Python Release Python 3.13.0 | Python.org — https://www.python.org/downloads/release/python-3130/ （发布：未知；访问：2026-09-16；链接：OK；已读正文）
- [S02] What's New In Python 3.13 — https://docs.python.org/3/whatsnew/3.13.html （发布：未知；访问：2026-09-16；链接：OK；已读正文）
- [S03] PEP 744 – JIT Compilation — https://peps.python.org/pep-0744/ （发布：未知；访问：2026-09-16；链接：OK；已读正文）
- [S04] PEP 594 – Removing dead batteries from the standard library — https://peps.python.org/pep-0594/ （发布：未知；访问：2026-09-16；链接：OK；已读正文）
- [S05] https://docs.python.org/3/whatsnew/3.13/repl-improvements.html （访问：2026-09-16；链接：GONE 404，无 Wayback 快照；未读取）
- [S06] https://docs.python.org/3/library/asyncio-uvloop.html （访问：2026-09-16；链接：GONE 404，无 Wayback 快照；未读取）
- [S07] Event Loop — Python 3.13 documentation（审计者补充）— https://docs.python.org/3.13/library/asyncio-eventloop.html （发布：未知；访问：2026-09-16；链接：OK；已读正文）

证据目录：web-evidence/（ledger.json、links.json、links_extra.json、pages/S01–S04、S07 的正文）
