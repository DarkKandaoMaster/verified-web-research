# Python 3.13 新特性简述

Python 3.13 于 2024 年 10 月 7 日正式发布[1]。本版本引入了实验性的自由线程模式（可选关闭 GIL）[2]，以及一个实验性的 JIT 编译器[3]。官方称 JIT 使大多数工作负载提速 2–3 倍[3]。此外，3.13 移除了 19 个"dead batteries"标准库模块，包括 cgi、telnetlib、imghdr 等[4]。3.13 还把默认 REPL 换成了源自 PyPy 的新交互式解释器，支持多行编辑和彩色提示[5]。最后，3.13 将 asyncio 的默认事件循环改为 uvloop[6]。

[1] https://www.python.org/downloads/release/python-3130/
[2] https://docs.python.org/3/whatsnew/3.13.html
[3] https://peps.python.org/pep-0744/
[4] https://peps.python.org/pep-0594/
[5] https://docs.python.org/3/whatsnew/3.13/repl-improvements.html
[6] https://docs.python.org/3/library/asyncio-uvloop.html
