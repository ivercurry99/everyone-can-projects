"""everyone-can-projects · 项目脚手架与校验工具

用途：
    1. 从零把一句粗糙想法，变成"7 份立项文档 + phases/ 目录 + PROGRESS.md"的标准工程布局。
    2. 校验已生成的产物是否满足「五道门禁 / 鲁棒性 / 多 Agent 适配」的硬性要求。
    3. 纯本地可运行：不依赖任何特定模型、子智能体或宿主；失败可重试，可幂等。

设计原则（对应 SKILL.md 的鲁棒性规则）：
    * 信息不全用默认值补齐，不卡死。
    * 生成前检查已有产物：默认只"补充缺失"，不覆盖已有文件（--force 显式覆盖）。
    * 幂等：重复运行只补缺失项，不产生重复冲突。
    * 每一步失败都给出可恢复的明确提示。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent

SEVEN_DOCS: Tuple[str, ...] = (
    "01-project-charter",      # 立项说明
    "02-feature-list",         # 功能清单
    "03-project-dossier",      # 项目管理档案
    "04-roadmap",              # 推进计划
    "05-tech-stack",           # 技术栈选型
    "06-architecture",         # 项目架构
    "07-engineering-norms",    # 项目级工程规范
)

REQUIRED_PHASES: Tuple[str, ...] = (
    "01-design",
    "02-impl",
    "03-test",
    "04-review",
)

# Agent / Model 能力矩阵：用于在降级时自动选择可行路径
# key = 能力标识；value = 缺失时的降级描述
CAPABILITY_FALLBACK: Dict[str, str] = {
    "subagents": "不支持多 Agent 并行 → 单人按角色串行切换，门禁一项都不能少。",
    "memory_system": "没有宿主记忆系统 → 使用项目内 PROGRESS.md 作为唯一事实来源。",
    "brainstorm_skill": "没有头脑风暴技能 → 用等价开放式提问逐项澄清。",
    "aesthetic_skill": "没有去 AI 味技能 → 人工逐项检查：通用占位符 / 模板套话 / 语气一致性。",
    "web_fetch": "没有网络能力 → 跳过【复用到 GitHub 开源方案】环节，直接按本地常识选型。",
}


# ---------------------------------------------------------------------------
# 默认值与用户意图解析
# ---------------------------------------------------------------------------

DEFAULTS: Dict[str, Any] = {
    "audience": "一般用户",
    "core_value": "提供一个可用、可维护的最小可行产品（MVP）",
    "scope_boundary": "仅实现用户明确列出的核心功能，不擅自扩展后台、支付、多租户等非必需模块",
    "style": "简洁专业，去除明显 AI 模板感",
    "deploy": "暂不部署，先本地可用",
    "tech_stack_hint": "未指定",
}


@dataclass
class ProjectIntent:
    project_name: str
    brief: str
    core_modules: List[str]
    reference: str
    deploy: str
    extra: str

    @classmethod
    def from_user(
        cls,
        project_name: str,
        brief: str,
        core_modules: Optional[str] = None,
        reference: str = "",
        deploy: str = "",
        extra: str = "",
    ) -> "ProjectIntent":
        name = _slugify(project_name) or "my-project"
        modules = [m.strip() for m in (core_modules or "").split(",") if m.strip()]
        if not modules:
            modules = ["MVP：能跑起来的主干功能"]
        return cls(
            project_name=name,
            brief=brief.strip() or "用户未提供详细简介，后续迭代中补全。",
            core_modules=modules,
            reference=reference.strip(),
            deploy=deploy.strip() or DEFAULTS["deploy"],
            extra=extra.strip(),
        )


def _slugify(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^\w\s\u4e00-\u9fff-]", "", name)
    name = re.sub(r"[\s_]+", "-", name)
    return name.strip("-")


# ---------------------------------------------------------------------------
# 7 份立项文档生成（内容模板化 + 用户意图填充）
# ---------------------------------------------------------------------------

def render_doc_charter(it: ProjectIntent) -> str:
    return f"""# 01 · 立项说明（Project Charter）

- 项目代号：`{it.project_name}`
- 一句话简介：{it.brief}
- 目标用户：{DEFAULTS['audience']}
- 核心价值：{DEFAULTS['core_value']}
- 功能边界：{DEFAULTS['scope_boundary']}
- 参考风格 / 竞品：{it.reference or '暂无，后续补充'}
- 部署要求：{it.deploy}
- 其他补充：{it.extra or '无'}

## 成功标准（Definition of Done）
1. 核心模块「{it.core_modules[0]}」能跑通主流程。
2. 五道门禁（Gate0~Gate4）全部通过。
3. PROGRESS.md 已同步，换会话可继续。
4. 关键节点已在 git 提交。

## 非目标（明确不做什么）
- 不擅自实现用户未提及的支付、后台、权限系统。
- 不在本期追求极致性能或无限扩展。
- 不引入多余依赖；能标准库解决就不引第三方。
"""


def render_doc_feature_list(it: ProjectIntent) -> str:
    lines = "\n".join(
        f"- [ ] M{i+1} · {m}（优先级：P{'1' if i==0 else '2'}）"
        for i, m in enumerate(it.core_modules)
    )
    return f"""# 02 · 功能清单（Feature List）

> 原则：一个 feature 完成并过门禁，再进入下一个。

## 核心功能
{lines}

## 功能拆分粒度
- 每个 feature 必须能被「架构师→开发者→测试员→审查员」独立走完一轮。
- 超过 3 天/30 文件的 feature 必须再拆小。
"""


def render_doc_dossier(it: ProjectIntent) -> str:
    return f"""# 03 · 项目管理档案（Project Dossier）

## 基本信息
| 项 | 值 |
|---|---|
| 项目名 | {it.project_name} |
| 启动时间 | {datetime.now().isoformat(timespec='minutes')} |
| 当前状态 | 立项中（Gate0 待通过） |
| 项目负责人（用户） | 用户本人 |
| 调度员（Agent） | 宿主智能体自动切换 |

## 角色分派
| 角色 | 负责人 | 产出目录 |
|---|---|---|
| 架构师 | 宿主智能体 / 子智能体（可选） | phases/01-design.md |
| 开发者 | 宿主智能体 / 子智能体（可选） | phases/02-impl.md + 代码 |
| 测试员 | 宿主智能体 / 子智能体（可选，≠ 开发者） | phases/03-test.md |
| 审查员 | 宿主智能体 / 子智能体（可选，≠ 架构师） | phases/04-review.md |
| 调度员（Gate） | 宿主智能体 | PROGRESS.md + 门禁记录 |

## 风险登记
| 风险 | 概率 | 影响 | 缓解策略 |
|---|---|---|---|
| 用户需求模糊 | 高 | 中 | 默认值 + 阶段性确认，不阻塞 |
| 模型能力弱，跳步骤 | 中 | 高 | 每步输出门禁 checklist，强制过一遍 |
| 多 Agent 宿主不支持 | 高 | 低 | 单人切换角色串行执行 |
| 记忆 / 上下文丢失 | 中 | 高 | 每个阶段写盘 PROGRESS.md，以文件为准 |
"""


def render_doc_roadmap(it: ProjectIntent) -> str:
    n = len(it.core_modules)
    modules = "\n".join(
        f"  - Sprint {i+1} · {m}（设计→实现→测试→审查）"
        for i, m in enumerate(it.core_modules)
    )
    return f"""# 04 · 推进计划（Roadmap）

## Milestones
- M0 · 立项文档齐全 → Gate0 通过（本阶段）
- M1 · Harness + 记忆初始化完成（阶段 1~2）
{modules}
- M{n + 2} · 质量打磨 + 去 AI 味
- M{n + 3} · 发版评审（可选）
- M{n + 4} · 部署 + 收尾

## 节奏
- 每个 feature 走完一轮（设计/实现/测试/审查）再下一个。
- 每结束一阶段 → 同步 PROGRESS.md → 提交 git。
"""


def render_doc_tech_stack(it: ProjectIntent) -> str:
    hint = DEFAULTS["tech_stack_hint"]
    return f"""# 05 · 技术栈选型（Tech Stack）

> 用户选型暗示：`{hint}`。以下为通用默认，架构师在阶段 1 可按实际需求调整（需更新本文件 + 在 PROGRESS 记录原因）。

| 层 | 选型 | 理由 |
|---|---|---|
| 后端（如需） | FastAPI / Flask | 生态成熟、文档多、弱模型也能写对 |
| 前端（如需） | Vite + React | 社区模板多，易于部署 |
| 存储 | SQLite + 可选向量库 | MVP 无需数据库运维 |
| 部署 | 用户指定；默认：本地可跑 + 后续再上 Vercel/Railway | 对齐用户部署要求（{it.deploy}） |
| 质量 | 单元测试 + 门禁 checklist | 任何宿主都能执行 |

## 降级策略
- 若宿主不支持装依赖：优先标准库。
- 若宿主无网络：跳过开源复用，按本地常识实现。
"""


def render_doc_architecture(it: ProjectIntent) -> str:
    modules = "\n".join(f"  - {m}" for m in it.core_modules)
    return f"""# 06 · 项目架构（Architecture）

## 模块划分
{modules}

## 分层原则（强制）
1. **接口层（API / UI）**：只做参数接收与响应格式化，不写业务。
2. **业务层（service / use case）**：纯业务逻辑，可单元测试。
3. **数据层（repository / dao）**：屏蔽存储细节，方便换库。
4. **公共层（util / config）**：无业务副作用。

## 目录建议
```
{it.project_name}/
├── src/
│   ├── api/        # 接口层
│   ├── services/   # 业务层
│   ├── repos/      # 数据层
│   └── utils/      # 公共层
├── tests/          # 测试，与 src 分层对齐
├── docs/           # 文档
└── phases/         # Harness 文件交接
```
"""


def render_doc_engineering_norms(it: ProjectIntent) -> str:
    return f"""# 07 · 项目级工程规范（Engineering Norms）

> 适用于：{it.project_name}。如与宿主级 AGENTS.md 冲突，以更具体/更安全的一条为准。

## 代码
- 单一职责；函数 ≤ 60 行；超过就拆成「可命名」的小函数。
- 默认不可变更新；不 mutate 输入参数。
- 错误显式处理；不静默吞错；不裸 `except:`。
- 所有对外输入做 Schema 校验。

## 门禁（Feature 完成时必须逐项确认）
- [ ] Gate0：需求清楚，本 feature 的"完成标准"已写进 phases/01-design。
- [ ] Gate1：设计文档齐全，调度员已签字确认。
- [ ] Gate2：代码可编译 / 可运行，开发者自测 smoke case。
- [ ] Gate3：测试员写并跑过单测/集成用例，全部通过。
- [ ] Gate4：审查员检查架构合规，无明显坏味道。

## 提交
- 提交信息：`feat/fix/refactor/test/docs/chore: <一句话>`。
- 每完成一个 feature 且过门禁 → 至少 1 次提交。
- 提交前跑：格式 → 类型 → 单测（如有）。
"""


DOC_RENDERERS: Dict[str, Any] = {
    "01-project-charter":      render_doc_charter,
    "02-feature-list":         render_doc_feature_list,
    "03-project-dossier":      render_doc_dossier,
    "04-roadmap":              render_doc_roadmap,
    "05-tech-stack":           render_doc_tech_stack,
    "06-architecture":         render_doc_architecture,
    "07-engineering-norms":    render_doc_engineering_norms,
}


# ---------------------------------------------------------------------------
# 骨架生成
# ---------------------------------------------------------------------------

@dataclass
class ScaffoldResult:
    project_dir: Path
    created: List[str]
    skipped: List[str]
    errors: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_dir": str(self.project_dir),
            "created": self.created,
            "skipped": self.skipped,
            "errors": self.errors,
            "ok": not self.errors,
        }


def scaffold(
    intent: ProjectIntent,
    output_root: Path,
    force: bool = False,
) -> ScaffoldResult:
    """把 intent 变成标准工程布局。幂等：已存在文件默认跳过。"""
    project_dir = output_root / intent.project_name
    docs_dir = project_dir / "docs" / "planning"
    phases_dir = project_dir / "phases"
    created: List[str] = []
    skipped: List[str] = []
    errors: List[str] = []

    # 1. 目录
    for d in (project_dir, docs_dir, phases_dir, project_dir / "tests"):
        try:
            d.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            errors.append(f"创建目录失败 {d}: {e}")

    # 2. 7 份立项文档
    for key in SEVEN_DOCS:
        path = docs_dir / f"{key}.md"
        if path.exists() and not force:
            skipped.append(str(path.relative_to(project_dir)))
            continue
        try:
            path.write_text(DOC_RENDERERS[key](intent), encoding="utf-8")
            created.append(str(path.relative_to(project_dir)))
        except OSError as e:
            errors.append(f"写入失败 {path}: {e}")

    # 3. phases 占位文件
    for key in REQUIRED_PHASES:
        path = phases_dir / f"{key}.md"
        if path.exists() and not force:
            skipped.append(str(path.relative_to(project_dir)))
            continue
        try:
            title = {
                "01-design": "设计文档（架构师交付）",
                "02-impl": "实现记录（开发者交付）",
                "03-test": "测试报告（测试员交付）",
                "04-review": "架构审查（审查员交付）",
            }[key]
            path.write_text(f"# {title}\n\n> 由对应角色在 feature 开发中填写。\n", encoding="utf-8")
            created.append(str(path.relative_to(project_dir)))
        except OSError as e:
            errors.append(f"写入失败 {path}: {e}")

    # 4. PROGRESS.md（唯一事实来源，用于多 Agent / 多会话续做）
    progress = project_dir / "PROGRESS.md"
    if progress.exists() and not force:
        skipped.append("PROGRESS.md")
    else:
        try:
            progress.write_text(
                f"""# {intent.project_name} · 进度索引

> 本文件 = 项目的唯一事实来源。任何 Agent、任何会话，先读本文件再干活。

## 当前里程碑
- [x] M0 · 立项文档齐全
- [ ] M1 · Harness + 记忆初始化
- [ ] M+ · features 迭代（详见 docs/planning/04-roadmap.md）

## 已确认的关键决定
1. 立项意图：{intent.brief}
2. 核心模块：{', '.join(intent.core_modules)}
3. 部署：{intent.deploy}

## 当前进行中
- 阶段：0 → 1（Harness 就位）

## 下一步（具体）
1. 调度员确认五角色 + 五道门禁就位 → 写回本文件。
2. 选第一个 feature，开始架构师产出 phases/01-design.md。

## 失败方案 & 证据
（暂无，有失败方案时在此补充，避免重复踩坑。）

## 未解决的风险
- （暂无）
""",
                encoding="utf-8",
            )
            created.append("PROGRESS.md")
        except OSError as e:
            errors.append(f"写入 PROGRESS 失败: {e}")

    return ScaffoldResult(project_dir=project_dir, created=created, skipped=skipped, errors=errors)


# ---------------------------------------------------------------------------
# 校验：验证一个项目目录是否满足鲁棒性要求
# ---------------------------------------------------------------------------

@dataclass
class ValidationReport:
    project_dir: Path
    checks: List[Dict[str, Any]]

    @property
    def ok(self) -> bool:
        return all(c["passed"] for c in self.checks)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_dir": str(self.project_dir),
            "ok": self.ok,
            "checks": self.checks,
        }


def validate(project_dir: Path) -> ValidationReport:
    checks: List[Dict[str, Any]] = []
    docs_dir = project_dir / "docs" / "planning"
    phases_dir = project_dir / "phases"

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})

    # 0. 基础目录
    add("项目目录存在", project_dir.is_dir(), str(project_dir))
    if not project_dir.is_dir():
        return ValidationReport(project_dir=project_dir, checks=checks)

    # 1. 7 份立项文档齐全
    missing_docs = [k for k in SEVEN_DOCS if not (docs_dir / f"{k}.md").is_file()]
    add(
        "7 份立项文档齐全",
        not missing_docs,
        "OK" if not missing_docs else f"缺失: {missing_docs}",
    )

    # 2. phases 目录 + 4 个交接文件
    missing_phases = [k for k in REQUIRED_PHASES if not (phases_dir / f"{k}.md").is_file()]
    add(
        "phases/ 交接文件齐全",
        not missing_phases,
        "OK" if not missing_phases else f"缺失: {missing_phases}",
    )

    # 3. PROGRESS.md 存在（记忆降级必备）
    progress = project_dir / "PROGRESS.md"
    add("PROGRESS.md 存在（记忆兜底）", progress.is_file(), str(progress))

    # 4. PROGRESS.md 包含续做锚点：下一步 + 当前阶段
    if progress.is_file():
        txt = progress.read_text(encoding="utf-8", errors="ignore")
        anchors = ["下一步", "当前"]
        has_anchor = any(a in txt for a in anchors)
        add("PROGRESS.md 含续做锚点", has_anchor, "含" if has_anchor else "缺少 `下一步`/`当前` 锚点")
    else:
        add("PROGRESS.md 含续做锚点", False, "文件不存在")

    # 5. 文档中无硬编码的高敏感字段（黑名单：裸手机号/邮箱/密钥等）
    sensitive_hits: List[str] = []
    secret_pattern = re.compile(r"(sk-[\w-]{10,}|AKIA[\w]{12,}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})")
    for p in list(project_dir.rglob("*.md"))[:200]:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in secret_pattern.findall(text):
            # 示例中邮箱可能是占位的，这里只是告警，不算硬失败
            sensitive_hits.append(f"{p.relative_to(project_dir)}: {m[:60]}")
    add(
        "未检测到敏感凭据（启发式）",
        len(sensitive_hits) == 0,
        "OK" if not sensitive_hits else "疑似敏感字段（仅告警，需人工复核）：\n  - " + "\n  - ".join(sensitive_hits[:5]),
    )

    return ValidationReport(project_dir=project_dir, checks=checks)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cmd_scaffold(args: argparse.Namespace) -> int:
    intent = ProjectIntent.from_user(
        project_name=args.name,
        brief=args.brief,
        core_modules=args.modules,
        reference=args.reference,
        deploy=args.deploy,
        extra=args.extra,
    )
    out = Path(args.output).resolve()
    result = scaffold(intent, output_root=out, force=args.force)
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"项目目录：{result.project_dir}")
        print(f"创建：{len(result.created)} 项")
        for x in result.created:
            print(f"  + {x}")
        if result.skipped:
            print(f"跳过（已存在）：{len(result.skipped)} 项")
            for x in result.skipped:
                print(f"  - {x}")
        if result.errors:
            print("错误：")
            for x in result.errors:
                print(f"  ! {x}")
            return 2
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    report = validate(project_dir)
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"校验：{project_dir} → {'PASS' if report.ok else 'FAIL'}")
        for c in report.checks:
            mark = "✅" if c["passed"] else "❌"
            print(f"  {mark} {c['name']} — {c['detail']}")
    return 0 if report.ok else 1


def _cmd_capabilities(_: argparse.Namespace) -> int:
    """输出"能力 → 降级方案"矩阵，用于多 Agents/弱模型适配时参考。"""
    rows = [{"capability": k, "fallback": v} for k, v in CAPABILITY_FALLBACK.items()]
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="scaffold_project", description="everyone-can-projects · 脚手架 + 校验")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scaffold", help="从一句提示词创建标准工程布局")
    s.add_argument("--name", required=True, help="项目名")
    s.add_argument("--brief", required=True, help="一句话简介（我想做什么）")
    s.add_argument("--modules", default="", help="核心模块，英文逗号分隔；留空则用默认 MVP")
    s.add_argument("--reference", default="", help="参考网站 / 风格（可选）")
    s.add_argument("--deploy", default="", help="部署要求（可选）")
    s.add_argument("--extra", default="", help="其他补充（可选）")
    s.add_argument("--output", default=str(Path.cwd()), help="输出根目录，默认 cwd")
    s.add_argument("--force", action="store_true", help="覆盖已有文件（默认只补缺失）")
    s.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    s.set_defaults(func=_cmd_scaffold)

    v = sub.add_parser("validate", help="校验一个已生成的项目目录是否合规")
    v.add_argument("project_dir", help="要校验的项目目录路径")
    v.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    v.set_defaults(func=_cmd_validate)

    c = sub.add_parser("capabilities", help="输出 能力→降级方案 矩阵（JSON）")
    c.set_defaults(func=_cmd_capabilities)

    return p


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))
