#!/usr/bin/env python3
"""Detect and configure local Deskmate Providers."""

from __future__ import annotations

import dataclasses
import shutil
import subprocess
import sys


PROBE_TIMEOUT_SECONDS = 2


@dataclasses.dataclass(frozen=True)
class Provider:
    key: str
    label: str
    executable: str
    identity: str


@dataclasses.dataclass(frozen=True)
class Detection:
    provider: Provider
    compatible: bool
    reason: str


PROVIDERS = (
    Provider("claude", "Claude Code", "claude", "claude"),
    Provider("codex", "Codex CLI", "codex", "codex"),
)


def one_line(value: str) -> str:
    return " ".join(value.split())


def detect(provider: Provider) -> Detection:
    executable = shutil.which(provider.executable)
    if executable is None:
        return Detection(provider, False, "not found")
    try:
        result = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return Detection(provider, False, "version probe timed out")
    output = one_line(result.stdout or result.stderr)
    if result.returncode != 0:
        detail = f": {output}" if output else ""
        return Detection(
            provider, False, f"version probe exited {result.returncode}{detail}"
        )
    if provider.identity not in output.casefold():
        detail = output or "empty output"
        return Detection(provider, False, f"unrecognized version output: {detail}")
    return Detection(provider, True, output)


def render(detections: list[Detection]) -> str:
    lines = []
    for item in detections:
        status = "included" if item.compatible else "excluded"
        lines.append(f"{item.provider.label}: {status} ({item.reason})")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args != ["providers"]:
        print("usage: providers.py providers", file=sys.stderr)
        return 2
    detections = [detect(provider) for provider in PROVIDERS]
    sys.stdout.write(render(detections))
    return 0 if any(item.compatible for item in detections) else 1


if __name__ == "__main__":
    raise SystemExit(main())
