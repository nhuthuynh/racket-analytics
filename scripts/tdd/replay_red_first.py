"""Replay the red step of a TDD commit after the fact (QA-R1S3-10).

For a commit that added a module and its tests together, this shows the tests cannot pass
without the module's behaviour. It exports the commit's ``backend/`` tree to a temp dir
(``git archive``; the repo, its index and its branches are not touched) and runs the tests:

1. as committed (green);
2. ``--skeleton``: every function body in MODULE replaced by ``raise NotImplementedError``
   (imports, constants, classes, dataclass fields and signatures kept);
3. ``--mutant OLD=>NEW`` (repeatable): one source edit per run, e.g. a negative branch
   switched off; the test that guards that rule must fail.

It is a reconstruction, not the original history: it proves the tests discriminate, not that
they were written first. Usage (from the repo root):

    backend/.venv/bin/python scripts/tdd/replay_red_first.py COMMIT MODULE TESTS... \
        [--skeleton] [--mutant 'OLD=>NEW' ...]
"""

from __future__ import annotations

import argparse
import ast
import io
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def skeleton(source: str) -> str:
    tree = ast.parse(source)

    class Gut(ast.NodeTransformer):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
            first = node.body[0] if node.body else None
            doc = (
                [first]
                if isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
                else []
            )
            node.body = [*doc, ast.parse("raise NotImplementedError('red-first skeleton')").body[0]]
            return node

        visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    return ast.unparse(ast.fix_missing_locations(Gut().visit(tree)))


def export(commit: str, into: Path) -> Path:
    blob = subprocess.run(  # noqa: S603 - fixed argv; commit is the caller's own input
        ["git", "-C", str(REPO), "archive", commit, "backend"],  # noqa: S607 - git from PATH
        check=True,
        capture_output=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(blob)) as tar:
        tar.extractall(into, filter="data")
    return into / "backend"


def run(backend: Path, tests: list[str], label: str) -> int:
    env = {k: v for k, v in os.environ.items() if k != "APP_ENV"}
    env["PYTHONPATH"] = "src:."
    out = subprocess.run(  # noqa: S603 - fixed argv; test paths are the caller's own input
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *tests],
        cwd=backend, env=env, capture_output=True, text=True,
    )  # fmt: skip
    lines = out.stdout.strip().splitlines()
    failed = [ln.split(" - ")[0] for ln in lines if ln.startswith("FAILED")]
    print(f"== {label}: rc={out.returncode} :: {lines[-1] if lines else out.stderr[-300:]}")
    for ln in failed[:8]:
        print(f"   {ln}")
    return out.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("commit")
    ap.add_argument("module", help="path under backend/, e.g. src/racket/dataset/full_tag.py")
    ap.add_argument("tests", nargs="+")
    ap.add_argument("--skeleton", action="store_true")
    ap.add_argument("--mutant", action="append", default=[], metavar="OLD=>NEW")
    a = ap.parse_args()
    bad = 0
    with tempfile.TemporaryDirectory() as tmp:
        backend = export(a.commit, Path(tmp) / "green")
        bad |= run(backend, a.tests, f"GREEN {a.commit} as committed") != 0
        if a.skeleton:
            backend = export(a.commit, Path(tmp) / "skeleton")
            target = backend / a.module
            target.write_text(skeleton(target.read_text()))
            bad |= run(backend, a.tests, f"RED {a.commit} {a.module} as skeleton") == 0
        for i, spec in enumerate(a.mutant):
            old, new = spec.split("=>", 1)
            backend = export(a.commit, Path(tmp) / f"mutant{i}")
            target = backend / a.module
            text = target.read_text()
            if text.count(old) != 1:
                print(f"== MUTANT NOT APPLIED (matches {text.count(old)}x): {old!r}")
                bad = 1
                continue
            target.write_text(text.replace(old, new))
            label = f"RED {a.commit} mutant {old.strip()!r} -> {new.strip()!r}"
            bad |= run(backend, a.tests, label) == 0
    return int(bad)


if __name__ == "__main__":
    raise SystemExit(main())
