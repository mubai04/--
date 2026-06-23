# M0 READY_FOR_REVIEW 验收材料

## 状态边界

- 当前状态：M0-01、M0-02 进入 `READY_FOR_REVIEW`。
- 未标记：未将任何任务标记为 `ACCEPTED`。
- 未执行：未执行 M1、M2、M7 或下一批任务。

## BASELINE_2026-06-23.json 字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | string | 静态基线结构版本，当前为 `xcue.m0.static-baseline/1.0`。 |
| `baseline_id` | string | 本次 M0-01 基线身份。 |
| `created_date` | string | 基线日期，使用 `2026-06-23`。 |
| `timezone` | string | 项目运行时区，当前为 `Asia/Shanghai`。 |
| `generation_policy` | object | 生成策略，声明确定性、是否运行 pytest、运行证据位置和排除规则。 |
| `generation_policy.deterministic` | boolean | 同一有效工程输入重复生成应得到同一输出。 |
| `generation_policy.does_not_run_pytest` | boolean | 生成静态基线时不执行 pytest。 |
| `generation_policy.runtime_test_results_are_external_evidence` | string | pytest 运行证据的独立文件路径。 |
| `generation_policy.excluded_from_effective_project_inventory` | array | 不进入有效工程清单和指纹的目录/前缀。 |
| `file_counts` | object | 有效工程清单内 `.py`、`.md`、`.json` 文件数量。 |
| `effective_project_file_count` | number | 有效工程清单内全部文件数量。 |
| `effective_project_manifest_sha256` | string | 有效工程清单的归档指纹，由相对路径和单文件 SHA256 组合计算。 |
| `key_entry_paths` | object | 当前关键入口相对路径。 |
| `tests_static_inventory` | object | 测试文件静态盘点，不包含测试运行结果。 |
| `tests_static_inventory.pytest_testpaths` | array | pytest 配置中的测试发现路径。 |
| `tests_static_inventory.test_file_count` | number | 原始工程测试文件数量。 |
| `tests_static_inventory.test_files` | array | 原始工程测试文件相对路径。 |
| `tests_static_inventory.standard_command` | string | 标准全量测试命令。 |
| `tests_static_inventory.m0_regression_command` | string | M0-02 回归样本专项命令。 |
| `tests_static_inventory.runtime_result_excluded_from_static_baseline` | boolean | 声明运行结果不写入静态基线。 |
| `known_failure_facts` | array | 已确认故障事实摘要。 |
| `reported_historical_pass_command` | object | 深度盘查报告中历史通过事实的来源记录，不冒充当前运行证据。 |
| `rule_file_hashes` | object | L0/L1/L1.5/L2/L3 规则 Markdown 文件 SHA256。 |
| `version_control` | object | git commit 或非 git 场景下的归档指纹。 |
| `version_control.git_commit` | string/null | 当前目录不是 git 仓库，因此为 null。 |
| `version_control.fallback_archive_sha256` | string/null | 非 git 场景下使用 `effective_project_manifest_sha256`。 |
| `version_control.note` | string | git 缺失时的解释。 |
| `unconfirmed_environment_items` | array | 当前不能确认的环境项。 |

## 基线排除规则

生成脚本 `00_工程总控/整改基线/生成整改前静态基线.py` 从有效工程清单中排除以下项目：

- `.git`
- `.pytest_cache`
- `__pycache__`
- `00_工程总控/整改基线/`
- `90_日志/`
- `99_归档_不要索引/`
- `测试/回归样本/`

因此：

- 生成脚本自身 `00_工程总控/整改基线/生成整改前静态基线.py` 排除在原始工程指纹之外。
- 基线输出 `00_工程总控/整改基线/BASELINE_2026-06-23.json` 排除在原始工程指纹之外。
- pytest 证据 `00_工程总控/整改基线/PYTEST_EVIDENCE_2026-06-23.json` 排除在原始工程指纹之外。
- M0-02 回归样本 `测试/回归样本/test_confirmed_failures.py` 排除在 M0-01 原始工程指纹之外。
- 运行记录、归档、缓存、旧报告和工具输出不进入有效工程清单。

## PYTEST_EVIDENCE skipped 明细

| node ID | skip reason |
|---|---|
| `00_工程总控/工程执行层/测试/测试第二轮C_流水线与安全.py::测试符号链接逃逸被拒绝` | `当前权限不允许创建符号链接` |

该 skip 来自 Windows 当前权限无法创建符号链接，不是 M0-02 回归样本路径错误或环境缺失。

## strict xfail 审计表

| 测试 node ID | 来源问题 ID | 任务 ID | 当前错误行为 | 修复后预期行为 |
|---|---|---|---|---|
| `测试/回归样本/test_confirmed_failures.py::test_unified_entry_tp001_default_invocation_should_succeed_without_unrecognized_standard_mode` | `R1-P0-01` | `M0-02` | 统一入口调用 TP-001 时额外透传 `--standard-mode CANDIDATE_TEST`，TP-001 入口返回 unrecognized arguments。 | 统一入口调用 TP-001 默认成功，返回 `ExitCode.OK`，stdout JSON 中 `returncode == 0`。 |
| `测试/回归样本/test_confirmed_failures.py::test_l2_empty_json_input_should_be_rejected` | `R1-P0-01` | `M0-02` | L2 接收 `{}` 后返回成功并生成空修复报告。 | L2 对空对象输入返回 `ExitCode.INPUT_INVALID`，且不生成修复报告。 |
| `测试/回归样本/test_confirmed_failures.py::test_l3_empty_json_input_should_be_rejected` | `R1-P0-01` | `M0-02` | L3 接收 `{}` 后返回成功并生成空任务结果。 | L3 对空对象输入返回 `ExitCode.INPUT_INVALID`，且不生成执行报告/任务包。 |
| `测试/回归样本/test_confirmed_failures.py::test_corrupt_json_input_should_return_structured_error_without_traceback` | `R1-P0-01` | `M0-02` | 损坏 JSON 触发 `JSONDecodeError` 裸 traceback，进程返回 1。 | 返回结构化 JSON 错误，退出码为 `ExitCode.INPUT_INVALID`，stderr/stdout 不含 `Traceback`。 |
| `测试/回归样本/test_confirmed_failures.py::test_sixty_four_character_pipeline_id_should_not_leave_running_manifest` | `R1-P0-01` | `M0-02` | 64 字符 pipeline ID 运行失败后留下 `status == RUNNING` 的清单残骸。 | 失败后不留下清单，或清单终态不是 `RUNNING`。 |
| `测试/回归样本/test_confirmed_failures.py::test_reusing_same_l1_run_id_should_preserve_previous_report_attempt` | `R1-P0-01` | `M0-02` | 同一 L1 run-id 第二次运行会覆盖旧报告并返回 L1 业务状态码。 | 第二次运行应拒绝覆盖并返回 `ExitCode.INPUT_INVALID`，旧报告保持原项目字段。 |
| `测试/回归样本/test_confirmed_failures.py::test_mixed_valid_and_out_of_scope_l2_items_should_still_emit_valid_fix` | `R1-P0-01` | `M0-02` | 合法 L2 项与越界项混合时，整体返回 `BLOCKED`，合法修复任务被阻断。 | 合法项仍生成 1 条修复单，越界项进入阻断记录，整体不跳过合法任务。 |
| `测试/回归样本/test_confirmed_failures.py::test_l2_markdown_route_change_should_change_interface_decision` | `R1-P0-01` | `M0-02` | 不加载 Markdown 规则时仍由硬编码 fallback 把 `入口弱` 路由到 `L2-05`。 | 路由行为应由 Markdown 规则驱动；修改规则后接口判断随之变化。 |
| `测试/回归样本/test_confirmed_failures.py::test_l2_six_ability_forbidden_items_should_be_parsed_from_markdown` | `R1-P0-01` | `M0-02` | L2 六能力禁止项解析结果均为 0。 | 六个 L2 能力的禁止项均能从 Markdown 解析出至少 1 条。 |
| `测试/回归样本/test_confirmed_failures.py::test_built_wheel_should_import_xc_ue_package` | `R1-P0-01` | `M0-02` | `importlib.util.find_spec("xc_ue")` 返回 `None`，构建包缺少可导入实际包。 | wheel 安装后可导入 `xc_ue` 包。 |

## xfail 有效性证明

- 收集证明：`python -m pytest --collect-only -q 测试/回归样本/test_confirmed_failures.py` 收集到 10 个测试。
- strict xfail 证明：`python -m pytest -q 测试/回归样本/test_confirmed_failures.py` 结果为 `10 xfailed in 3.47s`。
- 失败断言证明：`python -m pytest -q --runxfail 测试/回归样本/test_confirmed_failures.py` 结果为 `10 failed in 3.43s`。
- 路径证明：测试文件使用 `ROOT = Path(__file__).resolve().parents[2]` 定位项目根，不依赖当前 shell 中文路径编码。
- 环境证明：需要外部临时目录 IO 的 L1/L2/L3 子进程均显式设置 `XCUE_TEST_ALLOW_EXTERNAL_IO=1` 与临时令牌文件。
- 异常证明：10 个 xfail 的失败点均为具体断言失败；其中损坏 JSON 样本刻意捕捉当前裸 traceback，作为待修复行为，不是测试自身宽泛捕获异常。

## 当前命令结果

- `python -m pytest -q 测试/回归样本/test_confirmed_failures.py`：`10 xfailed in 3.47s`
- `python -m pytest -q`：`36 passed, 1 skipped, 10 xfailed in 11.65s`

