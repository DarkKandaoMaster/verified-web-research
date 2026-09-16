# 《Attention Is All You Need》arXiv 摘要中的 WMT 2014 BLEU 分数

来源：arXiv:1706.03762 摘要页 https://arxiv.org/abs/1706.03762 （访问日期：2026-09-17）

| 任务 | 摘要中报告的 BLEU |
|---|---|
| WMT 2014 英语→德语（English-to-German） | **28.4 BLEU** |
| WMT 2014 英语→法语（English-to-French） | **41.8 BLEU**（单模型 state-of-the-art，在 8 块 GPU 上训练 3.5 天） |

摘要原文（对应句子）：

> Our model achieves **28.4 BLEU** on the WMT 2014 English-to-German translation task, improving over the existing best results, including ensembles by over 2 BLEU. On the WMT 2014 English-to-French translation task, our model establishes a new single-model state-of-the-art **BLEU score of 41.8** after training for 3.5 days on eight GPUs, a small fraction of the training costs of the best models from the literature.

## 截图证据（已保存到当前目录）

1. `arxiv_1706.03762_abstract_full.png` —— arXiv 摘要页整页截图（含标题、作者、摘要）
2. `arxiv_1706.03762_abstract_crop.png` —— 仅摘要区域的裁剪截图（原样，无任何修改）
3. `arxiv_1706.03762_abstract_highlighted.png` —— 摘要区域截图，用黄色高亮标出 "28.4 BLEU" 和 "BLEU score of 41.8" 两处（仅在浏览器渲染时加了高亮标记，文字内容未改动）

截图方式：Playwright 驱动 Microsoft Edge（headless，2 倍分辨率）直接访问上述 arXiv 页面抓取。
