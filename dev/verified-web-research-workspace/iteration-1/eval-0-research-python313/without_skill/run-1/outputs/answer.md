# Python 3.13 发布日期与 PEP 594 移除的标准库模块

## 1. 正式发布日期

**Python 3.13.0 于 2024 年 10 月 7 日正式发布。**

- python.org 官方发布页面写明 "Release date: Oct. 7, 2024"：
  https://www.python.org/downloads/release/python-3130/
- 官方文档《What's New In Python 3.13》开头写明 "Python 3.13 was released on October 7, 2024."：
  https://docs.python.org/3/whatsnew/3.13.html

## 2. Python 3.13 按 PEP 594 移除的标准库模块（完整列表，共 19 个）

《What's New In Python 3.13》的 "Removed Modules and APIs → PEP 594: Remove the 'dead batteries'" 一节列出了以下 19 个模块（它们在 3.11 被标记为弃用，在 3.13 正式删除），按字母序：

| # | 模块 | 原用途（简述） |
|---|------|----------------|
| 1 | `aifc` | 读写 AIFF/AIFC 音频文件 |
| 2 | `audioop` | 原始音频数据操作 |
| 3 | `cgi` | CGI 支持 |
| 4 | `cgitb` | CGI 脚本的回溯管理 |
| 5 | `chunk` | 读取 IFF 分块数据 |
| 6 | `crypt` | 访问 Unix crypt(3) |
| 7 | `imghdr` | 判断图像文件类型 |
| 8 | `mailcap` | 处理 mailcap 文件 |
| 9 | `msilib` | 读写 Windows Installer (MSI) 文件 |
| 10 | `nis` | Sun NIS (Yellow Pages) 接口 |
| 11 | `nntplib` | NNTP 协议客户端 |
| 12 | `ossaudiodev` | 访问 OSS 兼容音频设备 |
| 13 | `pipes` | shell 管道接口 |
| 14 | `sndhdr` | 判断音频文件类型 |
| 15 | `spwd` | Unix shadow 密码数据库 |
| 16 | `sunau` | 读写 Sun AU 音频文件 |
| 17 | `telnetlib` | Telnet 客户端 |
| 18 | `uu` | uuencode/uudecode 编解码 |
| 19 | `xdrlib` | XDR 数据编解码 |

来源（可直接核对）：
- 官方文档 What's New In Python 3.13 → "PEP 594: Remove the 'dead batteries'"：
  https://docs.python.org/3/whatsnew/3.13.html#pep-594-remove-the-dead-batteries
- python.org 3.13.0 发布页面的 "Removed modules" 说明中也列出了同样这 19 个模块：
  https://www.python.org/downloads/release/python-3130/

## 3. 两点容易混淆的说明

1. **PEP 594 原文列了 22 个模块，但 3.13 只删了 19 个。** PEP 594 的弃用列表里还包含 `asynchat`、`asyncore`、`smtpd` 这 3 个模块，它们因为早就被弃用，已提前在 **Python 3.12** 中删除（见 What's New In Python 3.12 的 "Removed" 一节："The asynchat, asyncore, and imp modules have been removed…"，以及 smtpd 的单独条目）。
   - PEP 594 原文：https://peps.python.org/pep-0594/
   - What's New In Python 3.12 → Removed：https://docs.python.org/3/whatsnew/3.12.html#removed
2. **3.13 还删除了一些不属于 PEP 594 的模块/功能**，注意不要混进 PEP 594 列表：`2to3` 程序和 `lib2to3` 模块、`tkinter.tix` 模块、`locale.resetlocale()` 函数、`typing.io` / `typing.re` 命名空间、`configparser.LegacyInterpolation` 等。python.org 发布页在提到 "dead batteries" 时把 `lib2to3` 也一并列出，但 PEP 594 正文并未包含 `lib2to3`，它的移除依据是自身在 3.11 起的弃用，而非 PEP 594。
   - 详见 https://docs.python.org/3/whatsnew/3.13.html#removed-modules-and-apis

## 来源汇总

1. python.org — Python 3.13.0 发布页：https://www.python.org/downloads/release/python-3130/
2. Python 官方文档 — What's New In Python 3.13：https://docs.python.org/3/whatsnew/3.13.html
3. PEP 594 – Removing dead batteries from the standard library：https://peps.python.org/pep-0594/
4. Python 官方文档 — What's New In Python 3.12（asynchat/asyncore/smtpd 提前移除的依据）：https://docs.python.org/3/whatsnew/3.12.html
