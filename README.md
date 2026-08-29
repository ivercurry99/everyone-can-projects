# everyone-can-projects · 让小白也能 vibe coding 一个完整项目

> **一句话**：你只说「我想做什么」，剩下的——需求明确、工程质量、进度记忆、版本管理、部署——**全部自动包圆**。
>
> 不需要懂记忆管理、项目流程、子智能体这些概念；**不管你用的是大模型还是本地小模型、是 TRAE 还是别的 Agent 宿主，都能跑出稳定结果**。

<p align="center">
  <strong>
    <a href="#特性">特性</a> ·
    <a href="#快速开始">快速开始</a> ·
    <a href="#标准六步工作流">工作流</a> ·
    <a href="#多模型多-agent-适配">兼容性</a> ·
    <a href="#ci-与回归保护">CI</a> ·
    <a href="#license">License</a>
  </strong>
</p>

---

## 特性

| 常见痛点 | 本技能怎么做 |
|---|---|
| 想法粗糙、信息不全就卡住 | ✅ **默认值补齐**：最多问 5 个问题，其他自动给合理假设并告诉你 |
| AI 一次想做太多，越写越乱 | ✅ **每次只做一个 feature**：小步迭代，做完一个过门禁再下一个 |
| 写代码的同时自己测自己 → 盲区 | ✅ **五角色分工**：架构师 / 开发者 / 测试员 / 审查员 / 调度员，严格互斥 |
| 换个会话、换个设备就全忘 | ✅ **PROGRESS.md 唯一事实来源**：任何 Agent 先读它再干活 |
| 模型能力弱就跳过门禁、乱写代码 | ✅ **结构化 Prompt 锁死 + 五道门禁 checklist**：一项不少，过闸签字 |
| 某个宿主没有子智能体/记忆/联网 | ✅ **能力缺失自动降级**：5 种核心能力都有等价路径，不会卡死 |
| 覆盖了用户之前辛苦写的内容 | ✅ **生成前检查**：默认只补缺失；显式 `--force` 才覆盖 |
| 同一个项目重复做 → 返工 | ✅ **幂等 + 回归红线（R1~R9）**：CI 全量保障，不退化 |

---

## 快速开始

### 方式 A · 在支持 Skill 的 Agent 里安装

对你的 Agent 说：

```text
帮我安装「https://github.com/ivercurry99/everyone-can-projects」这个 Skill。
```

或使用命令：

```shell
npx skills add ivercurry99/everyone-can-projects
```

### 方式 B · 纯命令行（不依赖任何 Agent）

```shell
cd everyone-can-projects
pip install -r requirements.txt   # 只有 pytest + pytest-cov

# 从零把一句想法变成标准工程骨架
python scripts/scaffold_project.py scaffold \
  --name "my-personal-site" \
  --brief "做个人网站，作为别人了解我的入口" \
  --modules "文章列表, 生活记录, 社交按钮" \
  --deploy "暂不部署，先本地可用" \
  --output ../workspace

# 校验生成结果是否合规
python scripts/scaffold_project.py validate ../workspace/my-personal-site
```

### 方式 C · 直接让 Agent 读 [SKILL.md](./SKILL.md)

即便宿主没有 Skill 系统，也可以把 [SKILL.md](./SKILL.md) 丢给任意支持读文件的 Agent，让它按文档执行。

---

## 你会得到什么（标准产物）

一个最小完整项目（以 `my-personal-site` 为例）：

```
my-personal-site/
├── docs/planning/         ← 7 份立项文档（缺一不可）
│   ├── 01-project-charter.md
│   ├── 02-feature-list.md
│   ├── 03-project-dossier.md
│   ├── 04-roadmap.md
│   ├── 05-tech-stack.md
│   ├── 06-architecture.md
│   └── 07-engineering-norms.md
├── phases/                ← Harness 文件交接（不靠聊天记录，靠文件）
│   ├── 01-design.md       # 架构师交付
│   ├── 02-impl.md         # 开发者交付
│   ├── 03-test.md         # 测试员交付
│   └── 04-review.md       # 审查员交付
├── PROGRESS.md            ← 进度索引，唯一事实来源（记忆兜底）
└── tests/                 ← 测试按 src 分层对齐
```

---

## 标准六步工作流

| 阶段 | 做什么 | 停止条件 |
|---|---|---|
| 0 · 需求明确 | 头脑风暴提问 → 产出 7 份立项文档 | 文档齐全 + 用户确认假设 OK |
| 1 · Harness 就位 | 五角色 + 五道门禁 + 文件交接目录就绪 | docs + phases 齐全 |
| 2 · 进度记忆初始化 | 检测宿主记忆系统，不可用就落盘 PROGRESS.md | 有「记忆方式」的明确记录 |
| 3 · 迭代实施 | **每次只做一个 feature**，五角色走一轮 + 门禁签字 | feature 的 5 道闸全部签字 |
| 4 · 质量打磨 | 去 AI 味 6 项 checklist + 审查员复核 | checklist 全部勾过 |
| 5 · 发版评审（可选） | 多角色挑刺 → 集成评估师汇总 → Team Leader 敲定 | 结论为「可以发版」或「需要修改」 |
| 6 · 部署 + 收尾 | 按用户要求部署，同步进度，汇报下一步 | 可访问 / 用户说 OK |

完整 Prompt 模板见：[references/prompt-engineering.md](references/prompt-engineering.md)。

---

## 五道门禁（任何模型都得过，一项都不能少）

| 闸 | 谁查 | 查什么 |
|---|---|---|
| Gate 0 | 架构师 | 需求说清楚了吗？有明确的完成标准吗？ |
| Gate 1 | 调度员 | 设计文档完整吗？ |
| Gate 2 | 开发者 | 代码能编译 / 可运行？ smoke case 跑过了？ |
| Gate 3 | 测试员（**≠ 开发者**） | 测试全过了吗？覆盖主路径 + 至少 2 条边界？ |
| Gate 4 | 审查员（**≠ 架构师**） | 架构合规？去 AI 味 6 项全勾？ |

**调度员在 `phases/` 末尾签字，签完才算过。** 没签字 → 不允许进入下一 feature。

---

## 多模型 /多 Agent 适配

| 档位 | 典型 | 推荐 |
|---|---|---|
| S · 强推理 | GPT-4o / Claude 3.5+ 等 | 子智能体并行跑 5 角色，仍要求文件落地 + 签字 |
| A · 中强 | Qwen2.5-72B / Llama 3 70B 等 | 单 Agent 串行切角色，单次 ≤2 个并列动作 |
| B · 可用（小模型） | 7B / 14B / 端侧 | 单步 + 显式 checklist，先打印再执行再确认 |
| C · 弱 / 纯聊天 | 在线聊天机器人 | 纯文本输出，提示用户把内容手动存到对应文件 |

完整矩阵 & 故障修复：[references/model-agent-matrix.md](references/model-agent-matrix.md)
降级策略（能力缺失怎么应对）：[references/fallback-strategy.md](references/fallback-strategy.md)

---

## 配套脚本（可选增强）

| 脚本 / 命令 | 做什么 |
|---|---|
| `python scripts/scaffold_project.py scaffold ...` | 生成「7 份文档 + phases/ + PROGRESS.md」标准骨架；默认幂等（不覆盖）；`--force` 才覆盖。 |
| `python scripts/scaffold_project.py validate <dir>` | 校验项目是否满足所有鲁棒性红线（7 文档 / 4 phases / PROGRESS 锚点 / 敏感字段启发式）。 |
| `python scripts/scaffold_project.py capabilities` | 输出「能力 → 降级方案」JSON 矩阵，供多 Agent 编排层自动选路。 |

---

## Evals（评估用例）

技能评估用例定义在 [evals/evals.json](./evals/evals.json)，覆盖：

1. `vague-idea-to-planning`：模糊想法不直接写代码 → 先出 7 份文档
2. `one-feature-at-a-time`：大系统拆 feature，小步迭代
3. `resume-without-guessing`：「接着做」先读进度文件，不凭印象猜
4. `release-review-gate`：发版前先问是否评审，多角色挑刺

---

## CI 与回归保护

CI 配置：[.github/workflows/ci.yml](.github/workflows/ci.yml)，在 Python 3.10 / 3.11 / 3.12 上跑，核心保护项：

| 编号 | 回归红线 |
|---|---|
| R1 | 7 份立项文档必须齐全 |
| R2 | phases/ 四份交接文件必须存在 |
| R3 | PROGRESS.md 含「下一步」「当前」续做锚点 |
| R4 | scaffold 幂等：第二次跑默认全跳过 |
| R5 | 空模块 / 空简介 / 空部署 都不会崩（默认值兜底） |
| R6 | 五道门禁 Gate0~Gate4 齐全 |
| R7 | 降级矩阵覆盖 5 种核心能力 |
| R8 | CLI scaffold → validate 往返通过 |
| R9 | `scripts/scaffold_project.py` AST 可解析 |

本地跑：

```shell
pip install -r requirements.txt
pytest tests/ -v --cov=scripts --cov-report=term-missing --cov-fail-under=60
```

---

## 文档索引

| 文档 | 说啥 |
|---|---|
| [SKILL.md](./SKILL.md) | 技能本体：定位、流程、资源导航、鲁棒性规则、完成标准 |
| [references/harness.md](references/harness.md) | Harness 规范：五角色 / 五道门禁 / 文件交接 / 发版评审 |
| [references/memory.md](references/memory.md) | 进度记忆纪律：三层分类、同步、恢复、压缩 |
| [references/development-principles.md](references/development-principles.md) | 底层开发思维：GitHub 开源复用、版本管理、部署 |
| [references/fallback-strategy.md](references/fallback-strategy.md) | **多模型 / 多 Agent 降级策略**、去 AI 味 checklist、兜底三铁律 |
| [references/prompt-engineering.md](references/prompt-engineering.md) | **结构化 Prompt 模板**：触发词、立项、Harness、每轮 Feature、恢复、发版 |
| [references/model-agent-matrix.md](references/model-agent-matrix.md) | **模型 & Agent 适配矩阵 + 回归红线 + 故障修复** |
| [evals/evals.json](./evals/evals.json) | 评估用例（4 条核心路径） |

---

## 作者 & 协议

- 版本：1.0.0
- 作者：ivercurry99
- 协议：[MIT](./LICENSE)
- 邮箱：ivercurry99@gmail.com
- 发布后优化（v1.0.0 相对初始版本）：**全中文本地化**；新增 scaffold/validate/capabilities 三件套脚本；新增降级策略 / Prompt 锁死 / 适配矩阵 3 篇 references；新增 CI（py3.10~3.12）+ pytest 回归红线 R1~R9。
