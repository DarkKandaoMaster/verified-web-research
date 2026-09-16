**结论**：Python 3.13.0 正式版于 **2024 年 10 月 7 日（周一）** 发布。按 PEP 594 在 3.13 中移除的标准库模块共 **19 个**：`aifc`、`audioop`、`cgi`、`cgitb`、`chunk`、`crypt`、`imghdr`、`mailcap`、`msilib`、`nis`、`nntplib`、`ossaudiodev`、`pipes`、`sndhdr`、`spwd`、`sunau`、`telnetlib`、`uu`、`xdrlib`。网上偶见"20 个"的说法，多出的那个是 `lib2to3`，它确实也在 3.13 被移除，但依据是 PEP 617，不属于 PEP 594。

检索范围：截至 2026-09-17；时间范围为 Python 3.13 发布前后至今（2023-05 起的实现记录到当前页面状态）；共打开 7 个来源，7 个均读到正文（其中 1 个另有截图）。

## 能确认的

- **发布日期：2024-10-07。** python.org 官方发布页写明 "Release date: Oct. 7, 2024" [S01]；What's New 文档写 "Python 3.13 was released on October 7, 2024" [S03]；PEP 719 发布时间表 "Actual" 一栏写 "3.13.0 final: Monday, 2024-10-07" [S07]；Python Insider 发布公告本身发布于 2024-10-07 [S02]。（可信度：高 — 一手官方直述，发布页/公告与文档/PEP 属不同证据路径；as of 2024-10-07。注意 S01 页顶现已提示 3.13.0 被后续 3.13.x 补丁版取代，但首发日期不变。）

- **PEP 594 在 3.13 移除的 19 个模块（完整列表）** [S03][S04][S05][S06]：

  | # | 模块 | What's New 3.13 给出的替代建议（摘要）[S03] |
  |---|---|---|
  | 1 | `aifc` | PyPI `standard-aifc` |
  | 2 | `audioop` | PyPI `audioop-lts` |
  | 3 | `cgi` | `urllib.parse.parse_qsl()` / `email.message` / PyPI `multipart`；或 `standard-cgi` |
  | 4 | `cgitb` | PyPI `standard-cgitb` |
  | 5 | `chunk` | PyPI `standard-chunk` |
  | 6 | `crypt`（及私有 `_crypt`） | `hashlib`、`bcrypt`、`argon2-cffi`、`legacycrypt`、`crypt_r`、`standard-crypt` |
  | 7 | `imghdr` | `filetype`、`puremagic`、`python-magic`；或 `standard-imghdr` |
  | 8 | `mailcap` | `mimetypes`；或 `standard-mailcap` |
  | 9 | `msilib` | （文档未给替代） |
  | 10 | `nis` | （文档未给替代） |
  | 11 | `nntplib` | PyPI `pynntp`；或 `standard-nntplib` |
  | 12 | `ossaudiodev` | `pygame`（音频播放） |
  | 13 | `pipes` | `subprocess`；`shlex.quote()` 替代 `pipes.quote`；或 `standard-pipes` |
  | 14 | `sndhdr` | `filetype`、`puremagic`、`python-magic`；或 `standard-sndhdr` |
  | 15 | `spwd` | PyPI `python-pam` |
  | 16 | `sunau` | PyPI `standard-sunau` |
  | 17 | `telnetlib` | `telnetlib3`、`Exscript`；或 `standard-telnetlib` |
  | 18 | `uu` | `base64`；或 `standard-uu` |
  | 19 | `xdrlib` | PyPI `standard-xdrlib` |

  依据：What's New 3.13 "PEP 594: Remove 'dead batteries' from the standard library" 小节原句 "PEP 594 proposed removing 19 modules from the standard library … All of the following modules were deprecated in Python 3.11, and are now removed"，随后逐个列出上述 19 个 [S03]；PEP 594 正文 Table 1 中 "To be removed = 3.13" 的正是这 19 个 [S04]；执行移除的核心开发者 Victor Stinner 在 2023-05-26 的 discuss 首帖（"Zachary Ware and me removed 19 modules in Python 3.13 stdlib"）[S05] 和 CPython 跟踪 issue #104773（附逐模块移除 PR）[S06] 列出的也是同一份 19 个。（可信度：高 — 一手直述，文档 / PEP 文本 / 开发者实现记录 3 组独立证据路径；as of 2024-10-07。）

- **PEP 594 状态为 Final。** 其 "3.13" 条目规定："All modules deprecated by this PEP are removed from the main branch of the CPython repository and are no longer distributed as part of Python." [S04]（可信度：高 — PEP 原文即权威一手来源，问题问的就是 PEP 规定了什么；S03/S05/S06 的实现记录与之一致。）

- **PEP 594 全表其实是 22 个模块，但另外 3 个不是 3.13 移除的。** `asynchat`、`asyncore`、`smtpd` 在 PEP 594 Table 1 中 "To be removed" 标为 3.12 [S04]；Stinner 的帖子也写明 "Python 3.12 removed 5 stdlib modules: asynchat, asyncore, smtpd: PEP 594 …" [S05]。所以若问"PEP 594 总共移除了哪些"，答案是 22 个（3.12 移 3 个 + 3.13 移 19 个）；若问"3.13 按 PEP 594 移除了哪些"，答案是上表 19 个。（可信度：高；as of 2024-10-07。）

## 关于"19 个还是 20 个"的说明（表述不一致，非事实争议）

- discuss.python.org 帖子标题写 "Python 3.13 removes 20 stdlib modules"，但正文明确说是 19 个 PEP 594 模块，另加一句 "Moreover, I also removed the 2to3 program and lib2to3 module in Python 3.13, deprecated in Python 3.11: PEP 617 PEG Parser." [S05]。
- python.org 发布页与 Python Insider 公告的 "Removals and new deprecations" 一条把 `lib2to3` 直接接在 PEP 594 模块列表末尾（共 20 项）[S01][S02]，容易让人以为 lib2to3 也属 PEP 594。
- 但 What's New 把 2to3/lib2to3 放在单独的 "2to3" 小节（gh-104780），不在 PEP 594 小节 [S03]；PEP 594 正文 Table 1 也没有 lib2to3 [S04]。
- 因此："3.13 移除了 20 个模块（19 个 PEP 594 + lib2to3）"和"按 PEP 594 移除了 19 个"都对，只是口径不同。

## 还不能确认的 / 本次未做的

- 没有逐个在 Python 3.13 解释器里 `import` 验证这 19 个模块确实不存在（这是 Observed 级别的实测，本次只核对了官方文档与实现记录，属 Reported/官方直述）。
- What's New 页面截图因脚本超时未能生成（页面过长），该来源只有正文文本证据；发布页 [S01] 有截图。

## 时效复查

- 检索了 "PEP 594 module removal reverted / restored / added back"：未见任何 PEP 594 模块在 3.13.x 后续版本被加回的记录。搜索摘要提到的 "some removals present in alpha 1 were reverted in alpha 2" 是发布页里关于 **C API** 移除的那一条 [S01][S02]，与 PEP 594 模块无关。
- 在本次检索范围内（关键词：Python 3.13.0 release date、PEP 594 removed modules、19 vs 20 modules、lib2to3、reverted/restored；来源 S01–S07）未见与上述结论不同的说法。

## 来源
- [S01] Python Release Python 3.13.0 | Python.org — https://www.python.org/downloads/release/python-3130/ （发布：未知；访问：2026-09-16；链接：OK；正文+截图）
- [S02] Python 3.13.0 (final) released | Python Insider — https://blog.python.org/2024/10/python-3130-final-released/ （发布：2024-10-07T00:00:00.000Z；访问：2026-09-16；链接：OK；已读正文）
- [S03] What's New In Python 3.13 — https://docs.python.org/3/whatsnew/3.13.html （发布：未知；访问：2026-09-16；链接：OK；已读正文）
- [S04] PEP 594 – Removing dead batteries from the standard library — https://peps.python.org/pep-0594/ （发布：未知；访问：2026-09-16；链接：OK；已读正文）
- [S05] PEP 594 has been implemented: Python 3.13 removes 20 stdlib modules (discuss.python.org) — https://discuss.python.org/t/pep-594-has-been-implemented-python-3-13-removes-20-stdlib-modules/27124 （发布：2023-05-26T14:39:32+00:00；访问：2026-09-16；链接：OK；已读正文）
- [S06] PEP 594: Remove stdlib modules scheduled for deletion in Python 3.13 · Issue #104773 — https://github.com/python/cpython/issues/104773 （发布：2023-05-22T23:36:24.000Z；访问：2026-09-16；链接：OK；已读正文）
- [S07] PEP 719 – Python 3.13 Release Schedule — https://peps.python.org/pep-0719/ （发布：未知；访问：2026-09-16；链接：OK；已读正文）

证据目录：web-evidence/（ledger.json、links.json、pages/S01–S07.md、shots/S01.png）
