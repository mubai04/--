# 测试证据 v0.2

测试日期：2026-06-22

## 基础测试

```text
python -m py_compile src/novel_pseudo_math.py
退出码：0

python src/novel_pseudo_math.py self-test
SELF-TEST PASS
退出码：0

pytest -q
17 passed
退出码：0
```

## 正文目录

```text
python src/novel_pseudo_math.py validate-work --work-dir 正文/作品/DEMO
chapter_count：1
退出码：0
```

## 路径越界

```text
python src/novel_pseudo_math.py init-work --work-id ../../evil --title x
结果：拒绝 work_id
退出码：2
```

## 批处理失败传播

```text
任务数：1
成功：0
失败：1
原因：缺少 extraction.json
退出码：2
```

## 极短文本端到端

示例正文 57 字符：

```text
prepare：通过
score：通过
硬闸门：NEEDS_REVIEW
最终状态：NEEDS_REVIEW
```

没有出现“四个硬闸门全部 PASS”或短文本高分。

## 自动测试覆盖

- 运行时 Schema 拒绝额外字段；
- 负分子阻断；
- 分子大于分母阻断；
- 伪造证据文件阻断；
- 极短正文 PASS 阻断；
- 同证据过度复用阻断；
- 路径穿越阻断；
- 风险阈值无空档；
- 状态机五种核心路径；
- 反刷分失败阻止稳健通过；
- Stability 固定随机种子可复现；
- 版本比较范围与哈希约束；
- 批处理失败传播。

## 发布包复验

```text
ZIP 文件数：34
ZIP CRC：通过
after extract MANIFEST.sha256：0 错误
中文路径 UTF-8 标志：全部通过
解压后 self-test：通过
解压后 pytest：17 passed
```
