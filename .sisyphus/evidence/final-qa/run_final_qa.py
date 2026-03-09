from __future__ import annotations

import importlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

try:
    tomllib = importlib.import_module("tomllib")
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    tomllib = importlib.import_module("tomli")


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = Path(__file__).resolve().parent


def run_shell(name: str, command: str) -> dict[str, Any]:
    completed = subprocess.run(
        ["/bin/bash", "-lc", command],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    log_path = EVIDENCE_DIR / f"{name}.log"
    log_path.write_text(
        "COMMAND\n"
        f"{command}\n\n"
        "EXIT_CODE\n"
        f"{completed.returncode}\n\n"
        "STDOUT\n"
        f"{completed.stdout}\n"
        "STDERR\n"
        f"{completed.stderr}\n",
        encoding="utf-8",
    )
    return {
        "name": name,
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "log_path": str(log_path.relative_to(ROOT)),
    }


def write_json(name: str, payload: dict[str, Any]) -> None:
    (EVIDENCE_DIR / f"{name}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def record(scenario_id: int, title: str, checks: list[dict[str, Any]]) -> dict[str, Any]:
    passed = all(check["pass"] for check in checks)
    result = {
        "scenario": scenario_id,
        "title": title,
        "pass": passed,
        "checks": checks,
    }
    write_json(f"scenario_{scenario_id:02d}", result)
    return result


def main() -> int:
    pyproject_path = ROOT / "pyproject.toml"
    pyproject = tomllib.load(pyproject_path.open("rb"))

    scenarios: list[dict[str, Any]] = []

    task1_cmd = run_shell(
        "task1_toml_syntax",
        "python -c \"import tomllib; tomllib.load(open('pyproject.toml','rb'))\"",
    )
    dev_deps = pyproject.get("project", {}).get("optional-dependencies", {}).get("dev", [])
    scenarios.append(
        record(
            1,
            "pyproject QA",
            [
                {
                    "name": "TOML syntax parses via tomllib",
                    "pass": task1_cmd["returncode"] == 0,
                    "evidence": task1_cmd["log_path"],
                },
                {
                    "name": "[tool.ruff] target-version is py39",
                    "pass": pyproject.get("tool", {}).get("ruff", {}).get("target-version") == "py39",
                    "actual": pyproject.get("tool", {}).get("ruff", {}).get("target-version"),
                },
                {
                    "name": "dev optional dependencies include ruff and pre-commit",
                    "pass": "ruff>=0.4.0" in dev_deps and "pre-commit>=3.5.0" in dev_deps,
                    "actual": dev_deps,
                },
            ],
        )
    )

    task2_head = run_shell("task2_license_head", "head -1 LICENSE")
    task2_copyright = run_shell(
        "task2_license_copyright_count",
        'grep -c "Copyright (c) 2024" LICENSE',
    )
    scenarios.append(
        record(
            2,
            "LICENSE QA",
            [
                {
                    "name": "LICENSE first line contains MIT License",
                    "pass": "MIT License" in task2_head["stdout"],
                    "actual": task2_head["stdout"].strip(),
                    "evidence": task2_head["log_path"],
                },
                {
                    "name": "Copyright (c) 2024 appears exactly once",
                    "pass": task2_copyright["stdout"].strip() == "1",
                    "actual": task2_copyright["stdout"].strip(),
                    "evidence": task2_copyright["log_path"],
                },
            ],
        )
    )

    task3_wc = run_shell("task3_gitignore_line_count", "wc -l .gitignore")
    task3_env = run_shell("task3_gitignore_env_count", 'grep -c "^\\.env$" .gitignore')
    task3_ignore = run_shell(
        "task3_gitignore_check_ignore",
        "rm -f .env.test && touch .env.test && git check-ignore .env.test && rm -f .env.test",
    )
    gitignore_lines = int(task3_wc["stdout"].strip().split()[0])
    scenarios.append(
        record(
            3,
            "gitignore QA",
            [
                {
                    "name": ".gitignore has more than 30 lines",
                    "pass": gitignore_lines > 30,
                    "actual": gitignore_lines,
                    "evidence": task3_wc["log_path"],
                },
                {
                    "name": "exact .env entry appears once",
                    "pass": task3_env["stdout"].strip() == "1",
                    "actual": task3_env["stdout"].strip(),
                    "evidence": task3_env["log_path"],
                },
                {
                    "name": ".env.test is ignored by git",
                    "pass": task3_ignore["returncode"] == 0 and ".env.test" in task3_ignore["stdout"],
                    "actual": task3_ignore["stdout"].strip(),
                    "evidence": task3_ignore["log_path"],
                },
            ],
        )
    )

    task4_wc = run_shell("task4_contributing_line_count", "wc -l CONTRIBUTING.md")
    contributing_text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8").lower()
    contributing_lines = int(task4_wc["stdout"].strip().split()[0])
    task4_keywords = ["uv", "ruff", "pytest", "pre-commit", "fork"]
    scenarios.append(
        record(
            4,
            "CONTRIBUTING QA",
            [
                {
                    "name": "CONTRIBUTING.md has more than 100 lines",
                    "pass": contributing_lines > 100,
                    "actual": contributing_lines,
                    "evidence": task4_wc["log_path"],
                },
                {
                    "name": "required keywords exist in CONTRIBUTING.md",
                    "pass": all(keyword in contributing_text for keyword in task4_keywords),
                    "actual": {keyword: (keyword in contributing_text) for keyword in task4_keywords},
                },
            ],
        )
    )

    task5_wc = run_shell("task5_security_line_count", "wc -l SECURITY.md")
    task5_grep = run_shell(
        "task5_security_keyword_count",
        'grep -ci "vulnerability\\|reporting" SECURITY.md',
    )
    security_lines = int(task5_wc["stdout"].strip().split()[0])
    security_keyword_count = int(task5_grep["stdout"].strip() or "0")
    scenarios.append(
        record(
            5,
            "SECURITY QA",
            [
                {
                    "name": "SECURITY.md has more than 30 lines",
                    "pass": security_lines > 30,
                    "actual": security_lines,
                    "evidence": task5_wc["log_path"],
                },
                {
                    "name": "SECURITY.md mentions vulnerability/reporting",
                    "pass": security_keyword_count > 0,
                    "actual": security_keyword_count,
                    "evidence": task5_grep["log_path"],
                },
            ],
        )
    )

    bug_template = ROOT / ".github/ISSUE_TEMPLATE/bug_report.yml"
    feature_template = ROOT / ".github/ISSUE_TEMPLATE/feature_request.yml"
    pr_template = ROOT / ".github/PULL_REQUEST_TEMPLATE.md"
    bug_yaml = yaml.safe_load(bug_template.read_text(encoding="utf-8"))
    feature_yaml = yaml.safe_load(feature_template.read_text(encoding="utf-8"))
    pr_checkbox_count = len(re.findall(r"^- \[ \]", pr_template.read_text(encoding="utf-8"), re.MULTILINE))
    scenarios.append(
        record(
            6,
            "GitHub templates QA",
            [
                {
                    "name": "all 3 template files exist",
                    "pass": bug_template.exists() and feature_template.exists() and pr_template.exists(),
                    "actual": {
                        str(bug_template.relative_to(ROOT)): bug_template.exists(),
                        str(feature_template.relative_to(ROOT)): feature_template.exists(),
                        str(pr_template.relative_to(ROOT)): pr_template.exists(),
                    },
                },
                {
                    "name": "bug_report.yml and feature_request.yml are valid YAML",
                    "pass": isinstance(bug_yaml, dict) and isinstance(feature_yaml, dict),
                    "actual": {
                        "bug_report_type": type(bug_yaml).__name__,
                        "feature_request_type": type(feature_yaml).__name__,
                    },
                },
                {
                    "name": "PR template has at least 3 checkboxes",
                    "pass": pr_checkbox_count >= 3,
                    "actual": pr_checkbox_count,
                },
            ],
        )
    )

    dependabot = yaml.safe_load((ROOT / ".github/dependabot.yml").read_text(encoding="utf-8"))
    ecosystems = [update.get("package-ecosystem") for update in dependabot.get("updates", [])]
    scenarios.append(
        record(
            7,
            "Dependabot QA",
            [
                {
                    "name": "dependabot.yml version is 2",
                    "pass": dependabot.get("version") == 2,
                    "actual": dependabot.get("version"),
                },
                {
                    "name": "dependabot.yml has pip and github-actions ecosystems",
                    "pass": "pip" in ecosystems and "github-actions" in ecosystems,
                    "actual": ecosystems,
                },
            ],
        )
    )

    precommit_text = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    precommit_yaml = yaml.safe_load(precommit_text)
    scenarios.append(
        record(
            8,
            "pre-commit QA",
            [
                {
                    "name": ".pre-commit-config.yaml has ruff and ruff-format hooks",
                    "pass": "- id: ruff" in precommit_text and "- id: ruff-format" in precommit_text,
                    "actual": {
                        "ruff": "- id: ruff" in precommit_text,
                        "ruff-format": "- id: ruff-format" in precommit_text,
                    },
                },
                {
                    "name": "pre-commit config excludes black/flake8/isort",
                    "pass": all(tool not in precommit_text.lower() for tool in ["black", "flake8", "isort"]),
                    "actual": {tool: (tool in precommit_text.lower()) for tool in ["black", "flake8", "isort"]},
                },
                {
                    "name": ".pre-commit-config.yaml is valid YAML",
                    "pass": isinstance(precommit_yaml, dict),
                    "actual": type(precommit_yaml).__name__,
                },
            ],
        )
    )

    ci_text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    ci_yaml = yaml.safe_load(ci_text)
    jobs = ci_yaml.get("jobs", {})
    matrix_versions = jobs.get("test", {}).get("strategy", {}).get("matrix", {}).get("python-version", [])
    forbidden_keywords = ["publish", "pypi", "push"]
    scenarios.append(
        record(
            9,
            "CI workflow QA",
            [
                {
                    "name": "ci.yml has lint, test, build-check jobs",
                    "pass": all(job in jobs for job in ["lint", "test", "build-check"]),
                    "actual": sorted(jobs.keys()),
                },
                {
                    "name": "ci.yml tests Python 3.9 and 3.12",
                    "pass": "3.9" in matrix_versions and "3.12" in matrix_versions,
                    "actual": matrix_versions,
                },
                {
                    "name": "ci.yml contains no publish/pypi/push keywords",
                    "pass": all(keyword not in ci_text.lower() for keyword in forbidden_keywords),
                    "actual": {keyword: ci_text.lower().count(keyword) for keyword in forbidden_keywords},
                },
            ],
        )
    )

    task10_import = run_shell(
        "task10_import",
        'python -c "from observability.logging_config import configure_logging"',
    )
    task10_logging = run_shell(
        "task10_logging",
        (
            'python -c "import json, logging; '
            "from observability.logging_config import configure_logging; "
            "configure_logging(); "
            "logging.getLogger('qa').info("
            "'hello', extra={'api_key': 'secret123', 'nested': {'password': 'pw'}, 'safe': 'ok'}"
            ')"'
        ),
    )
    log_line = task10_logging["stderr"].strip().splitlines()[-1] if task10_logging["stderr"].strip() else ""
    parsed_log: dict[str, Any] | None = None
    json_valid = False
    redacted = False
    if log_line:
        try:
            parsed_candidate = json.loads(log_line)
            if isinstance(parsed_candidate, dict):
                parsed_log = parsed_candidate
                json_valid = True
                nested = parsed_log.get("nested")
                nested_password = nested.get("password") if isinstance(nested, dict) else None
                redacted = parsed_log.get("api_key") == "***" and nested_password == "***"
        except json.JSONDecodeError:
            parsed_log = None
    task10_result = record(
        10,
        "observability logging QA",
        [
            {
                "name": "from observability.logging_config import configure_logging works",
                "pass": task10_import["returncode"] == 0,
                "evidence": task10_import["log_path"],
            },
            {
                "name": "configure_logging() runs without error",
                "pass": task10_logging["returncode"] == 0,
                "evidence": task10_logging["log_path"],
            },
            {
                "name": "JSON format outputs valid JSON",
                "pass": json_valid,
                "actual": parsed_log,
            },
            {
                "name": "Sensitive fields are redacted",
                "pass": redacted,
                "actual": parsed_log,
            },
        ],
    )
    scenarios.append(task10_result)

    build_check = run_shell("integration_build", "python -m build")
    integration_pass = build_check["returncode"] == 0 and task10_result["pass"]

    passed_count = sum(1 for scenario in scenarios if scenario["pass"])
    total_count = len(scenarios)
    verdict = "PASS" if passed_count == total_count and integration_pass else "FAIL"
    summary = {
        "scenarios": scenarios,
        "scenario_pass_count": passed_count,
        "scenario_total_count": total_count,
        "integration": {
            "pass": integration_pass,
            "build_evidence": build_check["log_path"],
            "task10_required": task10_result["pass"],
        },
        "verdict": verdict,
    }
    write_json("summary", summary)
    report_line = (
        f"Scenarios [{passed_count}/{total_count} pass] | "
        f"Integration [{'PASS' if integration_pass else 'FAIL'}] | "
        f"VERDICT {verdict}"
    )
    (EVIDENCE_DIR / "report.txt").write_text(f"{report_line}\n", encoding="utf-8")
    print(report_line)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
