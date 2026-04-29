"""Regression tests for v0.15.2 T4-completion PR.

Closes Bug #2 + Bug #3 from the v0.15.0 deep-dive audit:

    Bug #2 — ``/vck-review`` Security perspective + ``/vck-cso`` regex
             pre-scan must invoke ``security_classifier`` on the diff
             so D4 (dormant classifier) is closed at review/audit gates,
             not only at the runtime pre_tool_use hook.
    Bug #3 — ``security_classifier`` CLI gains ``--scan-diff <base>``
             and ``--scan-paths <p1> <p2> …`` flags.

Plus invariant guards:

    Probe #86 — vck-review.md references security_classifier --scan-diff
    Probe #87 — vck-cso.md references security_classifier --scan-paths

Without these probes the wiring could regress silently because no other
gate inspects the markdown skills.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_PKG = _REPO / "scripts"
sys.path.insert(0, str(_PKG))

from vibecodekit import security_classifier  # noqa: E402
from vibecodekit.conformance_audit import (  # noqa: E402
    _probe_vck_cso_classifier_wired,
    _probe_vck_review_classifier_wired,
)


# ---------------------------------------------------------------------------
# Bug #3 — CLI flags
# ---------------------------------------------------------------------------

class ScanPathsCLI(unittest.TestCase):
    """Bug #3 — ``--scan-paths`` returns canonical JSON shape."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "ok.txt").write_text("just a normal sentence.\n")
        # Embed a literal AWS-style key to trigger a regex deny.  This is
        # a synthetic example for the test only — not a real secret.
        bad = (self.root / "bad.py")
        bad.write_text('AWS_SECRET_ACCESS_KEY = "AKIA' + 'IOSFODNN7EXAMPLE"\n')

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_scan_paths_returns_canonical_shape(self) -> None:
        out = security_classifier.scan_paths(["ok.txt", "bad.py"], root=self.root)
        self.assertEqual(out["scope"], "paths")
        self.assertEqual(out["files_scanned"], 2)
        paths_seen = {v["path"] for v in out["verdicts"]}
        self.assertEqual(paths_seen, {"ok.txt", "bad.py"})
        self.assertIn("summary", out)
        self.assertIn("exit_code", out)

    def test_scan_paths_missing_file_abstain(self) -> None:
        out = security_classifier.scan_paths(["nope.txt"], root=self.root)
        self.assertEqual(out["files_scanned"], 1)
        self.assertEqual(out["verdicts"][0]["decision"], "abstain")
        self.assertIn("not found", out["verdicts"][0]["reason"])

    def test_cli_scan_paths_emits_json(self) -> None:
        env = {**os.environ, "PYTHONPATH": str(_PKG)}
        proc = subprocess.run(
            [sys.executable, "-m", "vibecodekit.security_classifier",
             "--scan-paths", "ok.txt"],
            cwd=str(self.root), env=env, capture_output=True, text=True,
        )
        self.assertIn(proc.returncode, (0, 2),
                      f"unexpected exit {proc.returncode}; "
                      f"stdout={proc.stdout}; stderr={proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertEqual(data["scope"], "paths")
        self.assertEqual(data["files_scanned"], 1)


class ScanDiffCLI(unittest.TestCase):
    """Bug #3 — ``--scan-diff`` resolves git-diff and classifies post-state."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        # Bootstrap a tiny git repo with one commit.
        self._git("init", "-q", "-b", "main")
        self._git("config", "user.email", "test@example.invalid")
        self._git("config", "user.name", "test")
        (self.root / "a.txt").write_text("seed\n")
        self._git("add", "a.txt")
        self._git("commit", "-q", "-m", "seed")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args], cwd=str(self.root),
            capture_output=True, text=True, check=False,
        )

    def test_scan_diff_no_changes_returns_empty_verdicts(self) -> None:
        out = security_classifier.scan_diff("HEAD", root=self.root)
        self.assertEqual(out["scope"], "diff")
        self.assertEqual(out["base"], "HEAD")
        self.assertEqual(out["files_scanned"], 0)
        self.assertEqual(out["verdicts"], [])

    def test_scan_diff_picks_up_added_paths(self) -> None:
        (self.root / "new.txt").write_text("a fresh paragraph.\n")
        self._git("add", "new.txt")
        self._git("commit", "-q", "-m", "add new.txt")
        out = security_classifier.scan_diff("HEAD~1", root=self.root)
        paths = {v["path"] for v in out["verdicts"]}
        self.assertIn("new.txt", paths)

    def test_scan_diff_invalid_base_abstain(self) -> None:
        out = security_classifier.scan_diff("nonexistent-ref", root=self.root)
        self.assertEqual(out["files_scanned"], 0)
        self.assertEqual(len(out["verdicts"]), 1)
        self.assertEqual(out["verdicts"][0]["decision"], "abstain")

    def test_scan_diff_outside_repo_abstain(self) -> None:
        with tempfile.TemporaryDirectory() as outside:
            out = security_classifier.scan_diff("HEAD", root=Path(outside))
            self.assertEqual(len(out["verdicts"]), 1)
            self.assertEqual(out["verdicts"][0]["decision"], "abstain")
            self.assertIn("not_a_git_repo",
                          out["verdicts"][0]["permission_reason"])


class CLIMutex(unittest.TestCase):
    """Bug #3 — --text / --scan-diff / --scan-paths are mutually exclusive."""

    def test_text_plus_scan_paths_rejected(self) -> None:
        env = {**os.environ, "PYTHONPATH": str(_PKG)}
        proc = subprocess.run(
            [sys.executable, "-m", "vibecodekit.security_classifier",
             "--text", "hi", "--scan-paths", "x.txt"],
            cwd=str(_REPO), env=env, capture_output=True, text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("mutually exclusive", proc.stderr.lower())


# ---------------------------------------------------------------------------
# Bug #2 — vck-review + vck-cso wired
# ---------------------------------------------------------------------------

class VckReviewWiresClassifier(unittest.TestCase):
    """Bug #2 — /vck-review Security perspective invokes scan-diff."""

    def test_skill_references_scan_diff(self) -> None:
        body = (_REPO / "update-package" / ".claude" / "commands"
                / "vck-review.md").read_text(encoding="utf-8")
        self.assertIn("security_classifier", body)
        self.assertIn("--scan-diff", body)


class VckCsoWiresClassifier(unittest.TestCase):
    """Bug #2 — /vck-cso Phase 0 / regex pre-scan invokes scan-paths."""

    def test_skill_references_scan_paths(self) -> None:
        body = (_REPO / "update-package" / ".claude" / "commands"
                / "vck-cso.md").read_text(encoding="utf-8")
        self.assertIn("security_classifier", body)
        self.assertIn("--scan-paths", body)


# ---------------------------------------------------------------------------
# Probes #86 + #87 invariant guards
# ---------------------------------------------------------------------------

class Probe86VckReviewWiring(unittest.TestCase):
    """Probe #86 — invariant guard for Bug #2 vck-review wiring."""

    def test_probe_passes_on_current_repo(self) -> None:
        ok, detail = _probe_vck_review_classifier_wired(_REPO)
        self.assertTrue(ok, f"Probe #86 failed: {detail}")

    def test_probe_fails_when_skill_drops_classifier(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / "update-package" / ".claude" / "commands"
             ).mkdir(parents=True)
            (tdp / "update-package" / ".claude" / "commands"
             / "vck-review.md").write_text("# stripped of classifier wiring\n")
            old_env = os.environ.pop("VIBECODE_UPDATE_PACKAGE", None)
            os.environ["VIBECODE_UPDATE_PACKAGE"] = str(
                tdp / "update-package")
            try:
                ok, detail = _probe_vck_review_classifier_wired(tdp)
                self.assertFalse(ok)
                self.assertIn("does not reference", detail)
            finally:
                if old_env is not None:
                    os.environ["VIBECODE_UPDATE_PACKAGE"] = old_env
                else:
                    os.environ.pop("VIBECODE_UPDATE_PACKAGE", None)

    def test_probe_fails_when_scan_diff_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / "update-package" / ".claude" / "commands"
             ).mkdir(parents=True)
            # Mentions classifier but never invokes --scan-diff.
            (tdp / "update-package" / ".claude" / "commands"
             / "vck-review.md").write_text(textwrap.dedent("""\
                # half-wired
                We describe vibecodekit.security_classifier in prose
                but never invoke any of its scan flags directly.
                """))
            old_env = os.environ.pop("VIBECODE_UPDATE_PACKAGE", None)
            os.environ["VIBECODE_UPDATE_PACKAGE"] = str(
                tdp / "update-package")
            try:
                ok, detail = _probe_vck_review_classifier_wired(tdp)
                self.assertFalse(ok)
                self.assertIn("--scan-diff", detail)
            finally:
                if old_env is not None:
                    os.environ["VIBECODE_UPDATE_PACKAGE"] = old_env
                else:
                    os.environ.pop("VIBECODE_UPDATE_PACKAGE", None)


class Probe87VckCsoWiring(unittest.TestCase):
    """Probe #87 — invariant guard for Bug #2 vck-cso wiring."""

    def test_probe_passes_on_current_repo(self) -> None:
        ok, detail = _probe_vck_cso_classifier_wired(_REPO)
        self.assertTrue(ok, f"Probe #87 failed: {detail}")

    def test_probe_fails_when_scan_paths_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / "update-package" / ".claude" / "commands"
             ).mkdir(parents=True)
            (tdp / "update-package" / ".claude" / "commands"
             / "vck-cso.md").write_text(textwrap.dedent("""\
                # half-wired
                Mentions vibecodekit.security_classifier but never
                invokes any concrete scan helper flag.
                """))
            old_env = os.environ.pop("VIBECODE_UPDATE_PACKAGE", None)
            os.environ["VIBECODE_UPDATE_PACKAGE"] = str(
                tdp / "update-package")
            try:
                ok, detail = _probe_vck_cso_classifier_wired(tdp)
                self.assertFalse(ok)
                self.assertIn("--scan-paths", detail)
            finally:
                if old_env is not None:
                    os.environ["VIBECODE_UPDATE_PACKAGE"] = old_env
                else:
                    os.environ.pop("VIBECODE_UPDATE_PACKAGE", None)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
