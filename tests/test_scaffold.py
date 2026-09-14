"""Unit tests for everyone-can-projects — pure logic, no real APIs, no external hosts.

Run:
    pytest tests/ -v --cov=scripts --cov-report=term-missing --cov-fail-under=70
"""
from __future__ import annotations

import ast
import argparse
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import scaffold_project as sp  # noqa: E402


# ---------------------------------------------------------------------------
# 1. 基础：文件可被解析，SKILL.md 结构合法
# ---------------------------------------------------------------------------
class TestStructureSanity:
    def test_syntax_ok(self) -> None:
        code = (SCRIPTS / "scaffold_project.py").read_text(encoding="utf-8")
        ast.parse(code)  # SyntaxError 直接失败

    def test_seven_docs_complete(self) -> None:
        assert len(sp.SEVEN_DOCS) == 7
        for key in sp.SEVEN_DOCS:
            assert key in sp.DOC_RENDERERS

    def test_required_phases(self) -> None:
        assert set(sp.REQUIRED_PHASES) == {"01-design", "02-impl", "03-test", "04-review"}

    def test_skill_md_frontmatter(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        assert skill.startswith("---")
        # name + description 两个必填字段
        assert "name:" in skill
        assert "description:" in skill
        # description 必须同时涵盖「做什么」与「什么时候触发」
        desc_line = next(
            (ln for ln in skill.splitlines() if ln.strip().startswith("description:")), ""
        )
        assert len(desc_line) > 20

    def test_readme_links_to_references(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for md in ("SKILL.md", "LICENSE"):
            assert md in readme, f"README 缺失 {md} 链接/提及"


# ---------------------------------------------------------------------------
# 2. Intent 解析 & 默认值（鲁棒性：信息不全也不卡死）
# ---------------------------------------------------------------------------
class TestIntentDefaults:
    def test_empty_modules_gives_mvp(self) -> None:
        it = sp.ProjectIntent.from_user(" My App! ", "做个小工具", core_modules="")
        assert it.project_name == "my-app"
        assert it.core_modules and "MVP" in it.core_modules[0]

    def test_empty_brief_gives_placeholder(self) -> None:
        it = sp.ProjectIntent.from_user("x", "")
        assert "未提供" in it.brief or "补全" in it.brief

    def test_empty_deploy_falls_back(self) -> None:
        it = sp.ProjectIntent.from_user("x", "y", deploy="")
        assert it.deploy == sp.DEFAULTS["deploy"]

    def test_modules_comma_parsing(self) -> None:
        it = sp.ProjectIntent.from_user("x", "y", core_modules="A, B,  ,C  ,")
        assert it.core_modules == ["A", "B", "C"]

    def test_tech_stack_hint_default_and_custom(self) -> None:
        it = sp.ProjectIntent.from_user("x", "y")
        assert it.tech_stack_hint == sp.DEFAULTS["tech_stack_hint"]
        it2 = sp.ProjectIntent.from_user("x", "y", tech_stack_hint=" Vite + Vue3 ")
        assert it2.tech_stack_hint == "Vite + Vue3"
        assert "Vite + Vue3" in sp.render_doc_tech_stack(it2)


# ---------------------------------------------------------------------------
# 3. 7 份文档渲染：包含锚点，后续 Agent 能检索到
# ---------------------------------------------------------------------------
class TestDocRender:
    def _intent(self):
        return sp.ProjectIntent.from_user(
            "demo",
            "做个个人网站展示简历",
            core_modules="文章,生活记录,社交按钮",
            deploy="暂不部署",
        )

    def test_charter_mentions_success_criteria(self) -> None:
        txt = sp.render_doc_charter(self._intent())
        assert "成功标准" in txt and "五道门禁" in txt

    def test_feature_list_has_checkboxes(self) -> None:
        txt = sp.render_doc_feature_list(self._intent())
        assert txt.count("- [ ]") == 3  # 3 个 modules

    def test_dossier_has_roles_and_risks(self) -> None:
        txt = sp.render_doc_dossier(self._intent())
        for must in ("架构师", "开发者", "测试员", "审查员", "调度员", "风险登记"):
            assert must in txt

    def test_roadmap_numbering(self) -> None:
        n = len(self._intent().core_modules)
        txt = sp.render_doc_roadmap(self._intent())
        assert f"M{n + 2}" in txt and f"M{n + 4}" in txt

    def test_tech_stack_has_fallback(self) -> None:
        txt = sp.render_doc_tech_stack(self._intent())
        assert "降级策略" in txt

    def test_architecture_has_layered_structure(self) -> None:
        txt = sp.render_doc_architecture(self._intent())
        for must in ("接口层", "业务层", "数据层", "目录建议"):
            assert must in txt

    def test_engineering_norms_has_gates(self) -> None:
        txt = sp.render_doc_engineering_norms(self._intent())
        for g in ("Gate0", "Gate1", "Gate2", "Gate3", "Gate4"):
            assert g in txt


# ---------------------------------------------------------------------------
# 4. Scaffold：幂等、默认不覆盖、失败不丢产物
# ---------------------------------------------------------------------------
class TestScaffold:
    def test_scaffold_creates_all(self, tmp_path: Path) -> None:
        it = sp.ProjectIntent.from_user(
            "demo site", "做个个人站", core_modules="首页,博客"
        )
        res = sp.scaffold(it, tmp_path)
        assert res.errors == []
        # 7 + 4 phases + 1 progress
        assert len(res.created) >= 12
        assert (res.project_dir / "PROGRESS.md").is_file()
        docs = res.project_dir / "docs" / "planning"
        for k in sp.SEVEN_DOCS:
            assert (docs / f"{k}.md").is_file()
        phases = res.project_dir / "phases"
        for k in sp.REQUIRED_PHASES:
            assert (phases / f"{k}.md").is_file()

    def test_scaffold_idempotent_skips(self, tmp_path: Path) -> None:
        it = sp.ProjectIntent.from_user("demo", "x")
        r1 = sp.scaffold(it, tmp_path)
        r2 = sp.scaffold(it, tmp_path)
        assert r1.errors == [] and r2.errors == []
        # 第二次默认全部跳过
        assert len(r2.created) == 0
        assert len(r2.skipped) >= 12

    def test_scaffold_force_overwrites(self, tmp_path: Path) -> None:
        it = sp.ProjectIntent.from_user("demo", "x")
        r1 = sp.scaffold(it, tmp_path)
        # 手动污染其中一个，看 force 是否覆盖
        doc = r1.project_dir / "docs" / "planning" / "01-project-charter.md"
        doc.write_text("old content", encoding="utf-8")
        r2 = sp.scaffold(it, tmp_path, force=True)
        assert "old content" not in doc.read_text(encoding="utf-8")
        assert len(r2.created) >= 12

    def test_progress_contains_anchors(self, tmp_path: Path) -> None:
        it = sp.ProjectIntent.from_user("demo", "x")
        res = sp.scaffold(it, tmp_path)
        progress = (res.project_dir / "PROGRESS.md").read_text(encoding="utf-8")
        for must in ("下一步", "当前进行中", "失败方案"):
            assert must in progress


# ---------------------------------------------------------------------------
# 5. Validate：能检出缺失
# ---------------------------------------------------------------------------
class TestValidate:
    def test_validate_passes_on_valid(self, tmp_path: Path) -> None:
        it = sp.ProjectIntent.from_user("v", "x", core_modules="A,B")
        res = sp.scaffold(it, tmp_path)
        report = sp.validate(res.project_dir)
        assert report.ok, report.to_dict()

    def test_validate_fails_when_missing_docs(self, tmp_path: Path) -> None:
        d = tmp_path / "empty"
        d.mkdir()
        report = sp.validate(d)
        assert not report.ok
        names = {c["name"] for c in report.checks if not c["passed"]}
        assert "7 份立项文档齐全" in names
        assert "phases/ 交接文件齐全" in names
        assert "PROGRESS.md 存在（记忆兜底）" in names

    def test_validate_on_missing_dir(self, tmp_path: Path) -> None:
        """目录都不存在：不崩，直接给失败报告。"""
        report = sp.validate(tmp_path / "nope")
        assert not report.ok

    def test_validate_sensitive_fields_warn_not_fail(self, tmp_path: Path) -> None:
        """敏感字段只告警：文档里出现邮箱/密钥不应让 validate 硬失败。"""
        res = sp.scaffold(sp.ProjectIntent.from_user("warn", "x"), tmp_path)
        doc = res.project_dir / "docs" / "planning" / "01-project-charter.md"
        doc.write_text(
            doc.read_text(encoding="utf-8") + "\n联系：a@b.com 密钥：sk-abcdefgh123456\n",
            encoding="utf-8",
        )
        report = sp.validate(res.project_dir)
        assert report.ok is True, "敏感字段应只告警，不影响 ok"
        assert len(report.warnings) >= 2
        assert any("sk-" in w for w in report.warnings)
        assert any("@" in w for w in report.warnings)


# ---------------------------------------------------------------------------
# 6. 能力降级矩阵：覆盖所有声明过的可选能力
# ---------------------------------------------------------------------------
class TestCapabilityFallback:
    def test_all_expected_capabilities_exist(self) -> None:
        for cap in ("subagents", "memory_system", "brainstorm_skill", "aesthetic_skill", "web_fetch"):
            assert cap in sp.CAPABILITY_FALLBACK

    def test_capabilities_cli(self) -> None:
        # subprocess 跑一遍，确保输出合法 JSON 且 ≥5 条
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "scaffold_project.py"), "capabilities"],
            capture_output=True, text=True, check=True,
        )
        rows = json.loads(proc.stdout)
        assert len(rows) >= 5


# ---------------------------------------------------------------------------
# 7. CLI：scaffold + validate 干跑
# ---------------------------------------------------------------------------
class TestCli:
    def test_cli_scaffold_json(self, tmp_path: Path) -> None:
        proc = subprocess.run(
            [
                sys.executable, str(SCRIPTS / "scaffold_project.py"),
                "scaffold",
                "--name", "cli-demo",
                "--brief", "一个 CLI 小工具",
                "--modules", "命令行入口,子命令A",
                "--tech-stack", "pytest + ruff",
                "--output", str(tmp_path),
                "--json",
            ],
            capture_output=True, text=True, check=True,
        )
        data = json.loads(proc.stdout)
        assert data["ok"] is True
        assert Path(data["project_dir"]).is_dir()
        # --tech-stack 透传到 05-tech-stack.md
        ts = Path(data["project_dir"]) / "docs" / "planning" / "05-tech-stack.md"
        assert "pytest + ruff" in ts.read_text(encoding="utf-8")

        # 再跑 validate CLI，必须通过
        proc2 = subprocess.run(
            [
                sys.executable, str(SCRIPTS / "scaffold_project.py"),
                "validate", data["project_dir"], "--json",
            ],
            capture_output=True, text=True,
        )
        report = json.loads(proc2.stdout)
        assert report["ok"] is True, report
        assert proc2.returncode == 0

    def test_cli_scaffold_json_error_returns_nonzero(self, tmp_path: Path) -> None:
        """--json 模式出错也必须返回非 0 退出码（编排层靠退出码判断成败）。"""
        blocker = tmp_path / "blocker"
        blocker.write_text("占位", encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable, str(SCRIPTS / "scaffold_project.py"),
                "scaffold", "--name", "bad", "--brief", "x",
                "--output", str(blocker), "--json",
            ],
            capture_output=True, text=True,
        )
        assert proc.returncode == 2
        data = json.loads(proc.stdout)
        assert data["ok"] is False
        assert data["errors"]

    def test_cli_scaffold_human_output(self, tmp_path: Path) -> None:
        proc = subprocess.run(
            [
                sys.executable, str(SCRIPTS / "scaffold_project.py"),
                "scaffold", "--name", "human", "--brief", "demo",
                "--output", str(tmp_path),
            ],
            capture_output=True, text=True, check=True,
        )
        assert "创建：" in proc.stdout and "项目目录：" in proc.stdout

    def test_cli_validate_human_output_pass_fail(self, tmp_path: Path) -> None:
        # 先建一个合法项目，再用一个空目录测 FAIL 路径
        sp.scaffold(sp.ProjectIntent.from_user("ok", "x"), tmp_path)
        good = subprocess.run(
            [
                sys.executable, str(SCRIPTS / "scaffold_project.py"),
                "validate", str(tmp_path / "ok"),
            ],
            capture_output=True, text=True,
        )
        assert good.returncode == 0
        assert "PASS" in good.stdout

        empty = tmp_path / "empty"
        empty.mkdir()
        bad = subprocess.run(
            [
                sys.executable, str(SCRIPTS / "scaffold_project.py"),
                "validate", str(empty),
            ],
            capture_output=True, text=True,
        )
        assert bad.returncode == 1
        assert "FAIL" in bad.stdout


# ---------------------------------------------------------------------------
# 8. CLI 函数进程内直调：行为测试 + 覆盖率反映真实执行路径
# ---------------------------------------------------------------------------
class TestCliInProcess:
    def _scaffold_args(self, tmp_path: Path, **overrides) -> argparse.Namespace:
        base = dict(
            name="inproc", brief="简介", modules="A,B", reference="",
            deploy="", extra="", tech_stack="",
            output=str(tmp_path), force=False, json=True,
        )
        base.update(overrides)
        return argparse.Namespace(**base)

    def test_scaffold_cmd_json_ok_and_error_exit_code(self, tmp_path: Path, capsys) -> None:
        rc = sp._cmd_scaffold(self._scaffold_args(tmp_path))
        out = capsys.readouterr().out
        assert rc == 0
        data = json.loads(out)
        assert data["ok"] is True

        blocker = tmp_path / "blocker"
        blocker.write_text("占位", encoding="utf-8")
        rc2 = sp._cmd_scaffold(self._scaffold_args(tmp_path, output=str(blocker)))
        data2 = json.loads(capsys.readouterr().out)
        assert rc2 == 2
        assert data2["ok"] is False

    def test_scaffold_cmd_human_output_includes_skip(self, tmp_path: Path, capsys) -> None:
        sp._cmd_scaffold(self._scaffold_args(tmp_path, json=False))
        first = capsys.readouterr().out
        assert "项目目录：" in first and "创建：" in first
        # 第二次：幂等 → 走「跳过」分支
        rc = sp._cmd_scaffold(self._scaffold_args(tmp_path, json=False))
        second = capsys.readouterr().out
        assert rc == 0
        assert "跳过（已存在）" in second

    def test_validate_cmd_human_prints_warnings(self, tmp_path: Path, capsys) -> None:
        res = sp.scaffold(sp.ProjectIntent.from_user("vw", "x"), tmp_path)
        doc = res.project_dir / "docs" / "planning" / "02-feature-list.md"
        doc.write_text(doc.read_text(encoding="utf-8") + "\n邮箱：leak@example.com\n", encoding="utf-8")
        rc = sp._cmd_validate(argparse.Namespace(project_dir=str(res.project_dir), json=False))
        out = capsys.readouterr().out
        assert rc == 0  # 只告警，不失败
        assert "PASS" in out
        assert "敏感字段告警" in out

    def test_capabilities_cmd_json(self, capsys) -> None:
        rc = sp._cmd_capabilities(argparse.Namespace())
        rows = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert len(rows) >= 5

    def test_build_parser_defaults(self) -> None:
        args = sp.build_parser().parse_args(
            ["scaffold", "--name", "n", "--brief", "b"]
        )
        assert args.tech_stack == "" and args.force is False and args.json is False
