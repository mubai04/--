# TEST EVIDENCE · 八维伪线性探针 v3.2.1 CANDIDATE

测试日期：2026-06-22

## 1. 版本与静态验收

| 项目 | 命令/方法 | 结果 |
|---|---|---|
| 版本 | `python pseudo_linear_probe.py --version` | `3.2.1` |
| Python语法 | `python -m py_compile pseudo_linear_probe.py` | 通过 |
| 第三方依赖 | 检查 imports | 仅标准库 |
| OpenAI SDK/API Key/网络调用 | 静态关键词扫描 | 均为0 |
| SHA-256清单 | `sha256sum -c MANIFEST.sha256` | 生成清单后复验 |

静态扫描：

```text
import openai 0
from openai 0
OPENAI_API_KEY 0
requests. 0
urllib.request 0
httpx 0
socket. 0
```

## 2. 本地自检

命令：

```text
python pseudo_linear_probe.py self-test
```

结果：

```text
SELF-TEST PASS
```

覆盖：

1. 八维全2分映射为“中”；
2. 八维全4分映射为“高”；
3. 多维高过载不得继续输出“高”；
4. 数量覆盖率不足输出“证据不足”；
5. 7/8维有效但关键轴缺失，仍输出“证据不足”；
6. 数量覆盖合格但权重覆盖不足，输出“证据不足”；
7. 同一句证据重复支撑三个及以上高分维度，校验拒绝；
8. 商业关键门失败能够下调等级；
9. 有分无证据、虚构证据、主线全空、哈希错配均被拒绝。

## 3. 可复现单章评分

修改前：

```text
JSON 报告：/mnt/data/probe_revised/八维伪线性探针_v3.2.1_CANDIDATE/reports/before.probe.json
Markdown 报告：/mnt/data/probe_revised/八维伪线性探针_v3.2.1_CANDIDATE/reports/before.probe.md
本章追读执行强度：低；activation=0.4409（非概率）
```

修改后：

```text
JSON 报告：/mnt/data/probe_revised/八维伪线性探针_v3.2.1_CANDIDATE/reports/after.probe.json
Markdown 报告：/mnt/data/probe_revised/八维伪线性探针_v3.2.1_CANDIDATE/reports/after.probe.md
本章追读执行强度：高；activation=0.9497（非概率）
```

包内包含：

```text
samples/chapter_before.txt
samples/chapter_after.txt
examples/before_task/
examples/after_task/
reports/before.probe.json
reports/after.probe.json
```

这些示例只验证结构与计算链路，不构成市场有效性证据。

## 4. 修订关系对比

```text
对比 JSON：/mnt/data/probe_revised/八维伪线性探针_v3.2.1_CANDIDATE/reports/before_after.compare.json
对比 Markdown：/mnt/data/probe_revised/八维伪线性探针_v3.2.1_CANDIDATE/reports/before_after.compare.md
```

比较必须提供 `examples/revision_relation.json`；正文哈希相同或规则口径不兼容时默认拒绝。

## 5. 批量计算

```text
JSON 报告：/mnt/data/probe_revised/八维伪线性探针_v3.2.1_CANDIDATE/reports/batch/after_task/probe.report.json
Markdown 报告：/mnt/data/probe_revised/八维伪线性探针_v3.2.1_CANDIDATE/reports/batch/after_task/probe.report.md
本章追读执行强度：高；activation=0.9497（非概率）
JSON 报告：/mnt/data/probe_revised/八维伪线性探针_v3.2.1_CANDIDATE/reports/batch/before_task/probe.report.json
Markdown 报告：/mnt/data/probe_revised/八维伪线性探针_v3.2.1_CANDIDATE/reports/batch/before_task/probe.report.md
本章追读执行强度：低；activation=0.4409（非概率）
批处理索引：/mnt/data/probe_revised/八维伪线性探针_v3.2.1_CANDIDATE/reports/batch/probe_index.csv
成功 2，失败 0
```

结果：成功2，失败0。

## 6. 权重拟合路径

使用40份唯一哈希的合成报告进行代码路径测试：

```text
拟合权重文件：/mnt/data/probe_acceptance_tmp/fitted_weights.json
交叉验证均值：accuracy=1.000, balanced_accuracy=1.000, log_loss=0.177
```

该测试只证明拟合、分层交叉验证与权重输出路径可运行。合成样本被人为分离，不能作为真实市场相关性证据。

## 7. 尚未完成的外部有效性

1. 用户真实Codex环境中的多次独立提取；
2. 至少10段不同题材真实正文；
3. 同文重复提取的评分漂移与一致性；
4. 人工审稿人与Codex的轴级一致率；
5. 八维权重与真实追读、留存或付费数据的相关性；
6. 独立验证集与阈值校准。

## 8. 测试结论

```text
代码闭环：PASS
证据完整性闸门：PASS
版本治理：PASS
包内复现示例：PASS
市场有效性：未证明
版本状态：v3.2.1 CANDIDATE
```
