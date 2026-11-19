# 固定版本的完整性和干净环境复算

main 的文件清单 151/151 项、PR #4 的文件清单 188/188 项与各自的 Git 内容一致。PR #4 的三份研究在另一台机器上均可离线重建。15 份 CSV / JSON 的最大绝对数值误差为 2 × 10⁻¹⁶；4 张 PNG 的文字和图形与原图对应，逐字节哈希均有差异。上述结果衡量文件和计算的一致性。对财务事实和规则判断的独立核对见本次复核的主报告。[实测明细](data/history_audit_20261119.json) · [复核入口](README.md)

## 两个固定提交

| 归档对象 | main 文件清单条目 | PR #4 文件清单条目 | PR #4 manifest 中另列的输入哈希 | PR #4 summary 中另列的输入哈希 |
|---|---:|---:|---:|---:|
| Claude 11/13 | 39 | 39 | — | — |
| Claude 11/14 | 23 | 23 | 8 | 8 |
| Claude 11/15 | 21 | 21 | 11 | 11 |
| Claude 11/16 | — | 16 | 8 | 13 |
| Claude 11/17 | — | 10 | 4 | 6 |
| Claude 11/19 | — | 11 | 4 | 5 |
| GPT 11/13 原包内容 | 68 | 68 | — | — |
| **合计** | **151** | **188** | **35** | **43** |

两个提交分别为 `f9c4e5481742a828f7e548d0ad0ce6c99d613247` 和 `d5bf419b94179b6ad5f8d6be6ed794f0bfb31d64`。每项按该版本的归档字节重算 SHA-256，声明了文件长度的条目同时核对字节数。相同路径在多个清单重复列出时逐次检验。main 单列的 manifest 输入和 summary 输入各 19 项均相符，两版 `current_plan.json` 各有 8 项来源哈希，全部相符。11/13 后加的勘误不在当日冻结的 39 项内。[main 提交](https://github.com/ShuaiWang-Castle/StockPortfolio/tree/f9c4e5481742a828f7e548d0ad0ce6c99d613247) · [PR #4 提交](https://github.com/ShuaiWang-Castle/StockPortfolio/tree/d5bf419b94179b6ad5f8d6be6ed794f0bfb31d64)

- **大小写重名。** `claude_analysis_20261113/` 和 GPT 的 `reference_inputs/` 均各自包含 `out_FINAL.json`、`out_final.json`，分别为 1,058 和 4,887 字节。默认 macOS 工作区会把同目录下两者映射到同一路径。清单核验使用区分大小写的 Git 归档名，干净复算使用区分大小写的临时卷。[核验脚本](verify_history_20261119.py)
- **浏览器输入。** 11/13 浏览器记录的四段文本指纹全部能由归档文件去除**一个末尾 LF**后得到。manifest 中的文件指纹则覆盖该 LF。52 个资产的完整原始价格数组缺少对应的仓库文件，无法复算 `raw_price_data_sha256`。[原始元数据](https://github.com/ShuaiWang-Castle/StockPortfolio/blob/d5bf419b94179b6ad5f8d6be6ed794f0bfb31d64/claude_analysis_20261113/data/meta.json)
- **GPT 导入与历史价格。** 两个提交都通过 68 项原包文件验证，对话文本也与 `README_IMPORT.md` 单列的哈希相符。原始 zip 容器没有归档，归档内容不能证明当时压缩容器的字节数或 SHA。GPT 包内另有从早期项目带入的 39 个标的来源记录，其中 16 个原始响应在库且与各自长度、SHA 一致；另抓的 4 个响应也全部符合指纹。其余 23 个旧标的和三份更早的 CSV 指纹没有对应文件，属于历史来源记录的覆盖范围，68 项原包清单均可核验。[GPT 导入说明](https://github.com/ShuaiWang-Castle/StockPortfolio/blob/d5bf419b94179b6ad5f8d6be6ed794f0bfb31d64/gpt_review_20261113/README_IMPORT.md) · [归档内价格来源及未归档标的](data/history_audit_20261119.json)

## PR #4 的 clean export

将整个 PR #4 提交经 `git archive` 导出，在临时卷解包，先删除三个目录的全部 `out/` 和 `figures/`，再从导出的仓库根运行三个日期共六条 README 命令；每个 Python 进程均启用 `-I`。另以同样的核验脚本重新导出、从空产出目录复跑，并用逐文件数据复验结果。CSV 检查列名、行列次序与字符串；JSON 递归检查键、类型、列表次序与字符串；数字按文件中的十进制表示计算绝对差，容差为 10⁻⁹，相同位置的 NaN 按缺失值处理。[核验脚本](verify_history_20261119.py)

| 目录 | 清单总数 | 静态文件逐字节通过 | 重建的 CSV/JSON 逐字节通过 | 重建的 CSV/JSON 数值通过 | 最大绝对误差 | 重建的 PNG 逐字节通过 |
|---|---:|---:|---:|---:|---:|---:|
| 11/16 MSFT | 16 | 9/9 | 3/5 | 5/5 | 2 × 10⁻¹⁶ | 0/2 |
| 11/17 NVDA | 10 | 5/5 | 4/4 | 4/4 | 0 | 0/1 |
| 11/19 ANT | 11 | 4/4 | 2/6 | 6/6 | 2 × 10⁻¹⁶ | 0/1 |

合并静态文件、数据输出和 PNG 统计，三目录分别有 **12/16、9/10、6/11 项**与原清单逐字节一致。11/16 的尾差出现在再配置表与汇总，11/19 的尾差出现在风险曲线、仓位表、敏感性表与汇总。11/17 的五条规则输出逐字节一致。11/19 的估值网格与反向 DCF 表也逐字节一致。[逐文件误差、字节数及复跑 SHA](data/history_audit_20261119.json)

复跑环境为 macOS 13.7.3 / arm64，Python 3.11.6、NumPy 1.26.4、pandas 2.3.2、SciPy 1.16.2、Matplotlib 3.10.6，字体为 Noto Sans CJK SC Regular / Bold。原图 PNG 元数据标注 Matplotlib 3.11.2。四对图片逐一并排查看，数据点、图例和中文标签相符，宽度或高度差 1–2 像素。实测文件记录两套图像尺寸和本机两款字体的 SHA。[环境及尺寸](data/history_audit_20261119.json)

## 复现此次核验

在具备上述两个固定 Git 对象的本地仓库运行。第一条只依赖 Python 标准库和 Git。第二条还需历史脚本的科学计算与绘图依赖；选择区分大小写的临时目录以容纳两对重名文件。两个命令均把结果写到标准输出。

```sh
python3 -I codex_review_20261119/verify_history_20261119.py .
python3 -I codex_review_20261119/verify_history_20261119.py . --rerun
```

若工作区来自不含 Git 对象的 zip，可用含这两个提交的克隆单独运行历史审计。脚本的输入只来自本地归档，全程离线，临时目录在结束时自动清理。
