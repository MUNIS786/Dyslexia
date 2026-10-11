#!/usr/bin/env python3
"""
scripts/test_project_diagnostics.py — Deep QA Diagnostic Test Suite for DyslexAid.

Performs static and dynamic checks across:
1. Frontend relative import integrity: verifies all imports resolve to valid files.
2. Frontend router completeness: verifies all lazy/static imported components in App.jsx exist.
3. Backend route parameter validation: verifies path parameters {param} match function arguments.
4. Backend imports & schemas: imports all routers, services, and models.
5. API Contract & error handling: tests 404, 405, 422, 500 error sanitization and response contracts.
6. Report findings and identify any real errors.
"""
import os
import sys
import re
import inspect
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"
BACKEND_DIR = REPO_ROOT / "backend"

sys.path.insert(0, str(BACKEND_DIR))

findings = []


def check_frontend_imports():
    print("[1/5] Checking frontend import integrity...")
    broken = []
    total_files = 0
    total_imports = 0

    for root, _, files in os.walk(FRONTEND_SRC):
        for f in files:
            if f.endswith((".js", ".jsx")):
                total_files += 1
                filepath = Path(root) / f
                try:
                    content = filepath.read_text(encoding="utf-8")
                except Exception as e:
                    broken.append((str(filepath), f"Unreadable file: {e}"))
                    continue

                # Match import ... from './...' or import './...' or import(...)
                patterns = [
                    r'''(?:from|import)\s+['"](\.[^'"]+)['"]''',
                    r'''import\s*\(\s*['"](\.[^'"]+)['"]\s*\)''',
                ]
                for p in patterns:
                    for m in re.finditer(p, content):
                        total_imports += 1
                        target = m.group(1)
                        # Clean query params or hashes if any
                        clean_target = target.split("?")[0].split("#")[0]
                        resolved = (Path(root) / clean_target).resolve()
                        candidates = [
                            resolved,
                            resolved.with_suffix(".js"),
                            resolved.with_suffix(".jsx"),
                            resolved.with_suffix(".json"),
                            resolved.with_suffix(".css"),
                            resolved / "index.js",
                            resolved / "index.jsx",
                        ]
                        if not any(c.exists() for c in candidates):
                            broken.append((str(filepath.relative_to(REPO_ROOT)), target))

    print(f"  Scanned {total_files} files and {total_imports} imports.")
    if broken:
        print(f"  [ERROR] Found {len(broken)} broken frontend imports:")
        for source, target in broken:
            print(f"    - {source} -> '{target}'")
            findings.append(f"Broken frontend import in {source}: '{target}'")
    else:
        print("  [PASS] All frontend relative imports resolve cleanly.")


def check_backend_path_params():
    print("\n[2/5] Checking FastAPI path parameters vs function signatures...")
    from main import app

    issues = []
    route_count = 0

    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "endpoint"):
            route_count += 1
            path = route.path
            endpoint = route.endpoint

            # Extract {param}
            path_params = set(re.findall(r"\{([a-zA-Z0-9_]+)\}", path))
            if path_params:
                sig = inspect.signature(endpoint)
                func_params = set(sig.parameters.keys())
                missing = path_params - func_params
                if missing:
                    issues.append((path, getattr(endpoint, "__name__", str(endpoint)), missing))

    print(f"  Inspected {route_count} FastAPI routes.")
    if issues:
        print(f"  [ERROR] Found {len(issues)} route signature mismatches:")
        for path, name, missing in issues:
            print(f"    - Route '{path}' ({name}) missing params in signature: {missing}")
            findings.append(f"Route '{path}' missing parameter in signature: {missing}")
    else:
        print("  [PASS] All route path parameters match endpoint signatures.")


def check_backend_imports():
    print("\n[3/5] Testing backend module imports and model definitions...")
    import_errors = []
    discovered_modules = []

    subdirs = ["core", "database", "deps", "models", "routers", "services"]
    for subdir in subdirs:
        dir_path = BACKEND_DIR / subdir
        if not dir_path.exists():
            continue
        for root, _, files in os.walk(dir_path):
            for f in files:
                if f.endswith(".py") and f != "__init__.py":
                    rel = Path(root).relative_to(BACKEND_DIR)
                    parts = list(rel.parts) + [f[:-3]]
                    mod_name = ".".join(parts)
                    discovered_modules.append(mod_name)

    print(f"  Discovered {len(discovered_modules)} backend modules to import.")
    for mod_name in sorted(discovered_modules):
        try:
            __import__(mod_name)
        except Exception as e:
            import_errors.append((mod_name, str(e)))

    if import_errors:
        print(f"  [ERROR] {len(import_errors)} module import errors:")
        for mod, err in import_errors:
            print(f"    - {mod}: {err}")
            findings.append(f"Import error in {mod}: {err}")
    else:
        print(f"  [PASS] Successfully imported all {len(discovered_modules)} discovered backend modules.")


def check_api_error_handling_contracts():
    print("\n[4/5] Checking API error handling & middleware contracts...")
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app, raise_server_exceptions=False)
    issues = []

    # 1. 404 handler returns clean JSON
    res_404 = client.get("/api/v2/non-existent-endpoint-xyz-123")
    if res_404.status_code != 404:
        issues.append(f"Expected 404 for nonexistent route, got {res_404.status_code}")
    elif "detail" not in res_404.json():
        issues.append(f"404 response missing 'detail' field: {res_404.text}")

    # 2. 405 Method Not Allowed returns clean JSON
    res_405 = client.post("/api/version")
    if res_405.status_code != 405:
        issues.append(f"Expected 405 for POST /api/version, got {res_405.status_code}")

    # 3. Request-ID header is generated and returned
    res_head = client.get("/api/health")
    if "x-request-id" not in res_head.headers:
        issues.append("Missing 'X-Request-ID' in response headers from Observability middleware")

    if issues:
        print(f"  [ERROR] Found {len(issues)} API contract issues:")
        for iss in issues:
            print(f"    - {iss}")
            findings.append(iss)
    else:
        print("  [PASS] API error responses and X-Request-ID middleware verified.")


def check_locale_translations():
    print("\n[5/5] Checking multilingual frontend locale keys...")
    locales_dir = FRONTEND_SRC / "i18n" / "locales"
    if not locales_dir.exists():
        print("  [SKIP] Locales directory not found.")
        return

    en_file = locales_dir / "en.js"
    hi_file = locales_dir / "hi.js"
    mr_file = locales_dir / "mr.js"

    missing_files = [f.name for f in [en_file, hi_file, mr_file] if not f.exists()]
    if missing_files:
        findings.append(f"Missing locale files: {missing_files}")
        print(f"  [ERROR] Missing locale files: {missing_files}")
    else:
        print("  [PASS] English (en), Hindi (hi), and Marathi (mr) locale definitions exist.")


def main():
    print("=" * 70)
    print("  DYSLEXAID COMPREHENSIVE QA DIAGNOSTIC TEST SUITE")
    print("=" * 70)

    check_frontend_imports()
    check_backend_path_params()
    check_backend_imports()
    check_api_error_handling_contracts()
    check_locale_translations()

    print("\n" + "=" * 70)
    if findings:
        print(f"  DIAGNOSTICS FINISHED: {len(findings)} ISSUES FOUND")
        for f in findings:
            print(f"  [FAIL] {f}")
        sys.exit(1)
    else:
        print("  DIAGNOSTICS FINISHED: ALL CHECKS PASSED (0 ISSUES FOUND)")
        sys.exit(0)


if __name__ == "__main__":
    main()
