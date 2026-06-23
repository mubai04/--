# 正文检测工程

本目录用于把 L1 / L1.5 / L2 的 Markdown 标准，转换为对章节正文的工程化检测。

它检测的是正文，不是文件壳：

- 输入：候选正文 Markdown、L1 闸门标准、L1.5 路由矩阵、L2-99 接口表。
- 输出：正文检测报告、failure packet、路由建议。
- 证据：所有问题必须落到段落编号和正文摘句，不能只说“感觉不行”。

当前边界：

- 自动检测只做初筛，不冒充最终文学判断。
- “通过”只表示当前规则未发现硬失败，不等于发布质量无问题。
- 图片不是规则真源；Markdown 是当前标准来源。
- 正式正文 `chapters/ch01.md` 不会被本工程自动覆盖。

运行示例：

```powershell
python "00_工程总控\工程执行层\统一运行入口.py" --target 正文检测 --run-id 正文检测_RUN-手动编号
```

指定正文：

```powershell
python "00_工程总控\工程执行层\统一运行入口.py" --target 正文检测 --chapter "70_测试项目\TP-001_CleanHarness_IR_Runtime\chapters\_candidates\ch01_candidate_RUN-20260621-002.md"
```
