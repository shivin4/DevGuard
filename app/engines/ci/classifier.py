import re
from typing import Literal

FailureCategory = Literal[
    "dependency_install",
    "failing_test",
    "lint_error",
    "docker_build",
    "missing_secret",
    "timeout",
    "unknown",
]


def classify_ci_failure_rules(log_text: str) -> FailureCategory:
    """Classify CI failure category using deterministic regex rules."""
    log_lower = log_text.lower()

    # 1. Dependency Install Failures
    if any(
        kw in log_lower
        for kw in [
            "could not find a version that satisfies the requirement",
            "no matching distribution found",
            "pip install",
            "npm err!",
            "yarn install",
            "poetry install",
            "modulenotfounderror",
        ]
    ):
        return "dependency_install"

    # 2. Failing Tests
    if any(
        kw in log_lower
        for kw in [
            "pytest",
            "assertionerror",
            "failed test_",
            "=== short test summary info ===",
            "test session starts",
            "fail:",
            "failures!",
        ]
    ) or re.search(r"FAILED\s+tests/", log_text):
        return "failing_test"

    # 3. Lint Errors
    if any(
        kw in log_lower
        for kw in [
            "ruff check",
            "flake8",
            "black --check",
            "eslint",
            "pylint",
            "mypy",
            "syntaxerror",
        ]
    ) or re.search(r"\b[EFW]\d{3}\b", log_text):
        return "lint_error"

    # 4. Docker Build Failures
    if any(
        kw in log_lower
        for kw in [
            "docker build",
            "the command '/bin/sh -c",
            "returned a non-zero code:",
            "dockerfile",
            "failed to solve with frontend dockerfile.v0",
        ]
    ):
        return "docker_build"

    # 5. Missing Secrets / Environment Variables
    if any(
        kw in log_lower
        for kw in [
            "secret not found",
            "missing required environment variable",
            "unauthorized",
            "401 unauthorized",
            "invalid api key",
            "token is required",
        ]
    ):
        return "missing_secret"

    # 6. Timeout
    if any(
        kw in log_lower
        for kw in [
            "the operation was canceled",
            "job timed out",
            "execution timed out",
            "command timed out after",
        ]
    ):
        return "timeout"

    return "unknown"
