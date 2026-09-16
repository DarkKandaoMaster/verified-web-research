# 《Python 3.13 新特性简述》引用核查报告

核查日期：2026-09-17
核查方式：逐一访问 6 个引用链接（记录 HTTP 状态码），读取页面内容，与原文中对应的说法逐句比对；对存疑说法另查了官方 asyncio 文档作为旁证。

## 一、结论速览

| # | 链接 | 能否打开 | 引用是否支持原文说法 | 判定 |
|---|------|---------|----------------------|------|
| [1] | python.org/downloads/release/python-3130/ | 200 正常 | 支持（发布日期 2024-10-07） | 正确 |
| [2] | docs.python.org/3/whatsnew/3.13.html | 200 正常 | 支持（实验性自由线程模式） | 正确 |
| [3] | peps.python.org/pep-0744/ | 200 正常 | "实验性 JIT"成立；**"提速 2–3 倍"是捏造的，来源原话是"和现有解释器差不多快"** | 严重错误 |
| [4] | peps.python.org/pep-0594/ | 200 正常 | 支持（19 个模块，含 cgi/telnetlib/imghdr） | 正确 |
| [5] | docs.python.org/3/whatsnew/3.13/repl-improvements.html | **404 不存在** | 说法本身正确，但链接是编造的 | 链接失效 |
| [6] | docs.python.org/3/library/asyncio-uvloop.html | **404 不存在** | **说法是假的，链接也是编造的** | 严重错误 |

总评：6 条引用中 3 条完全正确，1 条说法正确但链接虚构，2 条含有事实性错误（其中 1 条同时链接虚构）。**[3] 的"2–3 倍"和 [6] 的"默认事件循环改为 uvloop"是典型的 AI 编造，必须删除或改写。**

## 二、逐条核查

### [1] 发布日期 —— 正确
- 原文说法：Python 3.13 于 2024 年 10 月 7 日正式发布。
- 链接状态：HTTP 200，可正常打开。
- 页面内容：明确写着 "Release date: Oct. 7, 2024"。页面列出的主要特性（新交互式解释器、实验性自由线程构建、实验性 JIT、mimalloc、dbm.sqlite3、iOS/Android Tier 3 等）也与本文其他说法一致。
- 判定：引用有效，说法准确。

### [2] 实验性自由线程模式（可选关闭 GIL）—— 正确
- 原文说法：引入了实验性的自由线程模式（可选关闭 GIL）。
- 链接状态：HTTP 200，可正常打开。
- 页面内容：What's New in 3.13 原文："CPython now has experimental support for running in a free-threaded mode, with the global interpreter lock (GIL) disabled. This is an experimental feature and therefore is not enabled by default." 需用 `--disable-gil` 构建，可执行文件为 `python3.13t`。
- 判定：引用有效，说法准确。可补充一点：页面还提示该模式会带来"substantial single-threaded performance hit"（明显的单线程性能损失）。
- 小建议：该页很长，引用时最好带上锚点 `#free-threaded-cpython`。

### [3] 实验性 JIT，"官方称提速 2–3 倍" —— 前半句正确，后半句是捏造
- 原文说法：引入实验性 JIT 编译器；"官方称 JIT 使大多数工作负载提速 2–3 倍"。
- 链接状态：HTTP 200，可正常打开。PEP 744 "JIT Compilation"，Status: Draft，Type: Informational，Python-Version: 3.13。
- 页面内容：PEP 744 关于性能的原话是——
  > "Currently, the JIT is about as fast as the existing specializing interpreter on most platforms."
  （目前 JIT 在大多数平台上的速度与现有的特化解释器**差不多**。）
  作者自己还用了 "underwhelming"（不够亮眼）来形容，并指出 JIT 目前**多消耗 10–20% 内存**。
  What's New 页面 [2] 的说法也一致："Performance improvements are modest – we expect to improve this over the next few releases."（性能提升有限。）
- 判定：**"2–3 倍"在引用来源里完全找不到，与来源结论相反。** 这是一个严重的事实错误，会误导读者。
- 另外需要注意：PEP 744 的状态是 Draft（草案）、类型为 Informational，它不是"官方宣布"性质的文档，用"官方称"措辞本身也不严谨。
- 建议改为："3.13 加入了一个实验性的 JIT 编译器，默认关闭，需以 `--enable-experimental-jit` 构建；官方明确表示目前性能提升有限，大致与现有解释器持平。"

### [4] 移除 19 个 dead batteries 模块 —— 正确
- 原文说法：移除了 19 个"dead batteries"标准库模块，包括 cgi、telnetlib、imghdr 等。
- 链接状态：HTTP 200，可正常打开。PEP 594 "Removing dead batteries from the standard library"，Status: Final。
- 页面内容：PEP 594 原计划共 22 个模块，其中 asynchat、asyncore、smtpd 三个已提前在 3.12 移除，其余 19 个在 3.13 移除。What's New 页面 [2] 明确列出这 19 个："aifc, audioop, chunk, cgi, cgitb, crypt, imghdr, mailcap, msilib, nis, nntplib, ossaudiodev, pipes, sndhdr, spwd, sunau, telnetlib, uu and xdrlib"。cgi、telnetlib、imghdr 均在列。
- 判定：引用有效，数字和例子都准确。
- 小建议："19 个"这个数字在 What's New 页面写得更直接，若想让读者一眼验证，可同时引用 [2] 的 `#pep-594-remove-dead-batteries-from-the-standard-library` 锚点。

### [5] 新 REPL 源自 PyPy，支持多行编辑和彩色提示 —— 说法正确，但链接不存在
- 原文说法：默认 REPL 换成源自 PyPy 的新交互式解释器，支持多行编辑和彩色提示。
- 链接状态：**HTTP 404**。`https://docs.python.org/3/whatsnew/3.13/repl-improvements.html` 这个页面在官方文档中不存在——What's New 是单页文档，没有 `3.13/` 子目录。这是一个被编造出来的、看起来合理的 URL。
- 说法核实：内容本身在 [2] 页面能找到依据："Python now uses a new interactive shell by default, based on code from the PyPy project." 新特性包括 "Multiline editing with history preservation"、"Prompts and tracebacks with color enabled by default"、F1 帮助、F2 历史、F3 粘贴模式等。
- 判定：**说法准确，引用无效。** 应把链接替换为 `https://docs.python.org/3/whatsnew/3.13.html#a-better-interactive-interpreter`。

### [6] asyncio 默认事件循环改为 uvloop —— 说法虚假，链接不存在
- 原文说法：3.13 将 asyncio 的默认事件循环改为 uvloop。
- 链接状态：**HTTP 404**。`https://docs.python.org/3/library/asyncio-uvloop.html` 不存在，标准库文档中从来没有这个页面。
- 说法核实：
  - What's New 3.13 页面 [2] 全文没有任何 uvloop 或"更换默认事件循环"的内容。
  - 官方 asyncio 文档（`docs.python.org/3/library/asyncio-eventloop.html`）写明：`asyncio.EventLoop` "is an alias to SelectorEventLoop on Unix and ProactorEventLoop on Windows"，即默认事件循环仍是标准库自带的实现，全页未提及 uvloop。
  - uvloop 是 MagicStack 维护的第三方 PyPI 包，从未被并入 CPython 标准库，更不可能成为默认实现。
- 判定：**说法完全错误，链接是编造的。** 整句应删除。若想保留一条 asyncio 相关内容，3.13 实际的 asyncio 变化包括：`asyncio.as_completed()` 现在同时支持异步迭代、`asyncio.TaskGroup` 在任务被外部取消时的行为改进、新增 `asyncio.Queue.shutdown()` 等（均见 [2] 的 asyncio 小节）。

## 三、问题模式总结

1. **两条虚构 URL（[5]、[6]）都长得很"像真的"**：域名正确、路径风格符合官方文档习惯，只是页面根本不存在。这类链接光看不点是发现不了的，建议以后对 AI 给出的引用一律实际打开验证。
2. **[3] 属于"链接真、内容假"**：来源本身是真实存在的 PEP，但 AI 给它安了一个来源里没有、甚至相反的结论（来源说"差不多快"，AI 说"快 2–3 倍"）。这比链接失效更危险，因为读者点开链接看到是真的 PEP 就容易相信。
3. **[6] 属于"链接假、内容也假"**：uvloop 从来不是标准库的一部分。

## 四、修订建议（可直接替换原文）

> Python 3.13 于 2024 年 10 月 7 日正式发布[1]。本版本引入了实验性的自由线程模式（可通过 `--disable-gil` 构建，关闭 GIL）[2]，以及一个默认关闭的实验性 JIT 编译器；官方表示目前 JIT 的性能提升有限，与现有解释器大致持平[3]。此外，3.13 移除了 PEP 594 中剩余的 19 个"dead batteries"标准库模块，包括 cgi、telnetlib、imghdr 等[4]。3.13 还把默认 REPL 换成了基于 PyPy 代码的新交互式解释器，支持多行编辑、彩色提示与回溯，以及 F1/F2/F3 快捷键[5]。
>
> [1] https://www.python.org/downloads/release/python-3130/
> [2] https://docs.python.org/3/whatsnew/3.13.html#free-threaded-cpython
> [3] https://peps.python.org/pep-0744/ ；另见 https://docs.python.org/3/whatsnew/3.13.html#an-experimental-just-in-time-jit-compiler
> [4] https://peps.python.org/pep-0594/ ；另见 https://docs.python.org/3/whatsnew/3.13.html#pep-594-remove-dead-batteries-from-the-standard-library
> [5] https://docs.python.org/3/whatsnew/3.13.html#a-better-interactive-interpreter

（原 [6] 关于 uvloop 的说法及链接已删除。）
