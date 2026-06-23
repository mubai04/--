# Snapshot 快照层说明

## 用途

Chuangjie 每章执行完成后，将实际结果回流 Xuke，驱动：

1. `历史快照.已用经验` 更新 → 影响历史惩罚系数
2. `历史快照.失败模式` 更新 → 降权相关经验
3. `学习信号` → 供 `08_训练进化系统` 人工或自动迭代

## 文件

- Schema：`snapshot.schema.yaml`
- 模板：`../模板/06_快照层.template.yaml` / `.json`

## 存储建议

```
Snapshot快照层/
├─ 记录/
│   ├─ CH-001.yaml
│   └─ CH-002.yaml
└─ 索引.yaml          # 最近 N 章摘要，供决策输入.history_snapshot 引用
```

v1.1 仅定义协议，记录目录随 Chuangjie 联调后写入。

## 边界

章节推演模拟器归属 **Chuangjie**（`Chuangjie/06_叙事模拟器`），不在 Xuke 内运行。  
Xuke 只消费 Chuangjie 推送的 `快照更新`。
