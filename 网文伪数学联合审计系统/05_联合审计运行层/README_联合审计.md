# 联合审计运行层 v1.0.2 CANDIDATE

正式输入：正文、广域审计 v1.0.2 JSON、八维探针正式报告 JSON。人工八维摘要仅保留展示，不进入计算。

```bash
python 联合审计器.py score --source 测试样本/第一章_第三扇门不能开.md --broad 测试样本/第一章_广域审计_v1.0.2.json --probe-report 测试样本/第一章_八维正式报告.json --output 测试报告/第一章_完整联合审计报告_v1.0.2.json
python 联合审计器.py self-test
```

联合层实际执行 JSON Schema、证据锚点、正文哈希、八维正式报告复算和商业六门门控。AI参与伪概率保持 C0，禁止身份定案。
