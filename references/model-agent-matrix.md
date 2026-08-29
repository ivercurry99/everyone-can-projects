# 模型 & Agent 适配矩阵（Model & Agent Matrix）

> 一份"什么模型 / 什么宿主 → 推荐走哪条路径、注意什么坑"的速查表。
>
> 原则：**能力越强，越能并行跑得飞快；能力越弱，越要靠「单步任务 + 显式 checklist + 文件落地」兜底。**
>
> 所有降级方案均可在 `scripts/scaffold_project.py capabilities` 输出中检索到。

---

## 1. 按模型能力档位推荐策略

| 档位 | 典型模型 | 推荐执行模式 | 强制保护 |
|---|---|---|---|
| **S** · 强推理（≥ GPT-4o / Claude 3.5 Sonnet / 同等） | 顶级闭源 + 顶级开源 70B+ | 子智能体并行，5 角色同时跑 | 仍要求「文件落地 + 调度员签字」，不凭聊天记录推进 |
| **A** · 中强（8x7B / 34B 本地推理等） | Qwen2.5-72B / Llama 3 70B / 国产旗舰 API | 串行单 Agent 切角色；可同时调度 2 个子角色 | **单步任务 ≤ 2 个并列动作**；弱模型默认一次只做一件事 |
| **B** · 可用（7B / 8B / 14B 小模型） | Llama 3.1 8B / Qwen2 7B / 端侧模型 | **单人串行 + 模板强制填充**；每个阶段打印 checklist | 每个阶段必须先「打印 checklist」再「做任务」再「确认 checklist 完成」；绝不允许直接跳过门禁 |
| **C** · 弱 / 纯聊天 | 在线聊天机器人、无文件写入能力 | 输出结构化文本，让用户手动把内容保存到项目文件中 | 明确提示用户：**请把我输出的每段保存到对应的 xxx.md 中再往下走** |

**Agent 执行时自动判定档位的经验法则**：

1. 让模型先做一道"读 SKILL.md 的 frontmatter 并提取 description"的小题。
   - 一次答对 → S / A；
   - 答案含糊但方向对 → B；
   - 全错或幻觉 → C。
2. 判档后按上表切换策略，**不升级、不降级，除非同一会话中出现证据支持调整**。

---

## 2. 按宿主能力的路径选择

| 宿主类别 | 能做什么 | 走什么路径 | 对应能力缺失的降级 |
|---|---|---|---|
| TRAE（本技能宿主） | 读写文件 / 子智能体 / 记忆 / 提问 / 执行命令 / 联网 | **最优路径**：并行子智能体 + 记忆系统 + GitHub 开源复用 | — |
| 普通 IDE Agent（Cursor / Copilot Chat / 本地 IDE 插件） | 读写文件 / 提问 / 执行命令 / 可能联网 | `subagents` 走降级（串行切角色）；`memory_system` 降级到 PROGRESS.md | `fallback-strategy.md` §1 表格 |
| 纯 CLI Agent（如 codex / aider 类） | 读写文件 / 执行命令 / 可能联网 | 不使用「提问」；所有未明确字段用默认值补齐；PROGRESS.md 做记忆 | `brainstorm_skill` 降级为「默认值 + 文档末尾列出假设」 |
| 纯网页 / 聊天窗口 Agent | 只有文本 | 纯文本输出，要求用户手动落盘 | 所有能力走 C 档；每步给出「保存到哪个路径」的明确指令 |

---

## 3. 回归保护：升级后不能退化的行为（红线）

以下项目被 `tests/test_scaffold.py` 作为回归保护：

| # | 红线条目 | 谁校验 |
|---|---|---|
| R1 | 7 份立项文档必须齐全（缺任何一份 = 校验失败） | `TestValidate` + CI |
| R2 | phases/ 四份交接文件必须存在 | `TestValidate` + CI |
| R3 | PROGRESS.md 必须包含「下一步」「当前」续做锚点 | `TestValidate` + CI |
| R4 | scaffold 第二次运行默认全跳过（幂等） | `TestScaffold.test_scaffold_idempotent_skips` + CI |
| R5 | 空模块 / 空简介 / 空部署不会崩（都有默认值） | `TestIntentDefaults` + CI |
| R6 | 五道门禁在工程规范中齐全（Gate0~Gate4） | `TestDocRender.test_engineering_norms_has_gates` |
| R7 | 降级矩阵至少覆盖 5 种核心能力（subagents/memory/brainstorm/aesthetic/web_fetch） | `TestCapabilityFallback` + CI |
| R8 | CLI scaffold → validate round-trip 通过 | `TestCli` + CI 冒烟步骤 |
| R9 | scripts/scaffold_project.py 必须 AST 可解析 | `TestStructureSanity.test_syntax_ok` + CI |

**任何 PR / 改动导致 R1~R9 任一失败 → 视为退化，必须修正后再合入。**

---

## 4. 常见故障 & 快速修复

| 故障表象 | 根因 | 修复 |
|---|---|---|
| Agent 跳过阶段 0 直接写代码 | Prompt 没锁死 / 模型跳过 checklist | 在"动手前"强制要求执行 `scripts/scaffold_project.py scaffold` 或等价落地 7 份文档 |
| "接着做"时从头开始、不读进度 | 没有强制先读 PROGRESS.md | 对恢复会话强制套用 `prompt-engineering.md` §5 模板 |
| 同一个 feature 被做了两次（重复） | 没有调度员门禁签字 | 门禁没签 → 不允许切 feature；已签的 feature 在 PROGRESS 打勾 |
| 覆盖用户已有文件导致返工 | 没有「生成前检查」 | scaffold 默认不覆盖；必须显式 `--force` |
| 弱模型一次要做 10 件事 → 混乱 | 多任务并列指令 | 按档位 B 策略：一次只给 ≤2 个并列动作，优先单步执行 |
| 密钥/邮箱不小心写进记忆 | 启发式检查没打开 | `validate` 每次对新项目做敏感字段检查，命中则告警 + 人工复核 |
