"""Unit tests for everyone-can-projects — pure logic, no real APIs, no external hosts.

Run:
    pytest tests/ -v --cov=scripts --cov-report=term-missing --cov-fail-under=60
"""
from __future__ import annotations

import ast
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
        ast.parse(code)

    def test_seven_docs_complete(self) -> None:
        assert len(sp.SEVEN_DOCS) == 7
        for key in sp.SEVEN_DOCS:
            assert key in sp.DOC_RENDERERS

    def test_required_phases(self) -> None:
        assert set(sp.REQUIRED_PHASES) == {"01-design", "02-impl", "03-test", "04-review"}

    def test_skill_md_frontmatter(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        assert skill.startswith("---")
        assert "name:" in skill
        assert "description:" in skill
        desc_line = next(
            (ln for ln in skill.splitlines() if ln.strip().startswith("description:")), ""
        )
        assert len(desc_line) > 20

    def test_readme_links_to_references(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for md in ("SKILL.md", "LICENSE"):
            assert md in readme, f"README 缺失 {md} 链接/提及"


# ---------------------------------------------------------------------------
# 2. Intent 解析 & 默认值
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


# ---------------------------------------------------------------------------
# 3. 7 份文档渲染：包含锚点
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
        assert txt.count("- [ ]") == 3

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
# 4. Scaffold：幂等、默认不覆盖
# ---------------------------------------------------------------------------
class TestScaffold:
    def test_scaffold_creates_all(self, tmp_path: Path) -> None:
        it = sp.ProjectIntent.from_user("demo site", "做个个人站", core_modules="首页,博客")
        res = sp.scaffold(it, tmp_path)
        assert res.errors == []
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
        assert len(r2.created) == 0
        assert len(r2.skipped) >= 12

    def test_scaffold_force_overwrites(self, tmp_path: Path) -> None:
        it = sp.ProjectIntent.from_user("demo", "x")
        r1 = sp.scaffold(it, tmp_path)
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
# 5. Validate
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


# ---------------------------------------------------------------------------
# 6. 能力降级矩阵
# ---------------------------------------------------------------------------
class TestCapabilityFallback:
    def test_all_expected_capabilities_exist(self) -> None:
        for cap in ("subagents", "memory_system", "brainstorm_skill", "aesthetic_skill", "web_fetch"):
            assert cap in sp.CAPABILITY_FALLBACK

    def test_capabilities_cli(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "scaffold_project.py"), "capabilities"],
            capture_output=True, text=True, check=True,
        )
        rows = json.loads(proc.stdout)
        assert len(rows) >= 5


# ---------------------------------------------------------------------------
# 7. CLI
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
                "--output", str(tmp_path),
                "--json",
            ],
            capture_output=True, text=True, check=True,
        )
        data = json.loads(proc.stdout)
        assert data["ok"] is True
        assert Path(data["project_dir"]).is_dir()

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
