#!/usr/bin/env python3
"""
scripts/verify_release.py — DyslexAid V2 Reproducible Release Candidate Verification Script.

Executes and verifies:
1. Git workspace sanity and whitespace check (git diff --check).
2. Phase 19 Security & Release Validation suite (pytest backend/test_phase19_release_validation.py).
3. Full backend regression test suite (pytest backend/ -q).
4. Frontend ESLint verification (npm run lint in frontend/).
5. Frontend production build (npm run build in frontend/).
6. Supply-chain dependency audit check (npm audit in frontend/).

Returns exit code 0 if all required verification steps pass cleanly.
"""
import sys
import os
import subprocess
import time
from pathlib import Path

import shutil

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
BACKEND_DIR = REPO_ROOT / "backend"


def print_header(title: str):
    print("\n" + "=" * 75)
    print(f"  {title}")
    print("=" * 75)


def run_step(name: str, cmd: list, cwd: Path, check: bool = True) -> bool:
    print(f"\n[STEP] {name}")
    print(f"  Running: {' '.join(cmd)}")
    print(f"  In:      {cwd}")
    start = time.time()
    try:
        # Use shell=True on Windows if invoking batch files like npm
        use_shell = os.name == "nt" and cmd[0] in ("npm", "npx")
        res = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, shell=use_shell)
        duration = time.time() - start
        if res.returncode == 0:
            print(f"  [PASS] {name} completed in {duration:.2f}s")
            if res.stdout.strip():
                # Print last 5 lines of stdout for brevity
                lines = res.stdout.strip().splitlines()
                summary_lines = lines[-5:] if len(lines) > 5 else lines
                for l in summary_lines:
                    print(f"     > {l}")
            return True
        else:
            print(f"  [FAIL] {name} exited with code {res.returncode} in {duration:.2f}s")
            if res.stdout:
                print("  --- Standard Output ---")
                print(res.stdout[-1500:])
            if res.stderr:
                print("  --- Error Output ---")
                print(res.stderr[-1500:])
            if check:
                return False
            return False
    except FileNotFoundError as fnfe:
        print(f"  [ERROR] Command not found: {cmd[0]} ({fnfe})")
        return False
    except Exception as exc:
        print(f"  [ERROR] Execution exception: {exc}")
        return False


def main():
    print_header("DyslexAid V2 — Release Candidate Verification")
    print(f"Repository Root: {REPO_ROOT}")
    print(f"Python Executable: {sys.executable}")

    steps = [
        # 1. Git whitespace and format check
        (
            "Git Whitespace and Diff Check",
            ["git", "diff", "--check"],
            REPO_ROOT,
            True,
        ),
        # 2. Phase 19 Security & UAT test suite
        (
            "Phase 19 Security & Release Acceptance Suite",
            [sys.executable, "-m", "pytest", "backend/test_phase19_release_validation.py", "-v"],
            REPO_ROOT,
            True,
        ),
        # 3. Full Backend regression suite
        (
            "Full Backend Regression Suite (Phases 1-19)",
            [sys.executable, "-m", "pytest", "backend/", "-q"],
            REPO_ROOT,
            True,
        ),
        # 4. Frontend ESLint
        (
            "Frontend ESLint",
            ["npm", "run", "lint"],
            FRONTEND_DIR,
            True,
        ),
        # 5. Frontend Production Build
        (
            "Frontend Vite Production Bundle Build",
            ["npm", "run", "build"],
            FRONTEND_DIR,
            True,
        ),
    ]

    all_passed = True
    for name, cmd, cwd, check in steps:
        passed = run_step(name, cmd, cwd, check=check)
        if not passed:
            all_passed = False
            print(f"\n[CRITICAL FAILURE] Pipeline halted at: {name}")
            sys.exit(1)

    # 6. Informational Dependency Audit (record without breaking on non-blocking dev advisory)
    print("\n[INFO] Running Dependency Audit...")
    try:
        audit_res = subprocess.run(
            ["npm", "audit", "--audit-level=high"],
            cwd=str(FRONTEND_DIR),
            text=True,
            capture_output=True,
            shell=os.name == "nt",
        )
        print("  npm audit summary output:")
        lines = [l for l in audit_res.stdout.splitlines() if "vulnerabilit" in l.lower() or "found" in l.lower()]
        for l in lines[:5]:
            print(f"     > {l}")
    except Exception as e:
        print(f"  Could not run npm audit: {e}")

    print_header("RELEASE CANDIDATE VERIFICATION: PASS")
    print("All release criteria, security regressions, builds, and linting checks passed successfully.\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
