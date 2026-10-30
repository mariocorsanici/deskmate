#!/usr/bin/env python3
"""Detect and configure local Deskmate Providers."""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile


PROBE_TIMEOUT_SECONDS = 2
CONFIG_SCHEMA_VERSION = 1
ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = pathlib.Path(os.environ.get("DESKMATE_DATA_DIR", ROOT / "data"))


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


class ConfigError(ValueError):
    """Configuration cannot be safely read by this Deskmate version."""


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


def read_config() -> dict[str, object]:
    path = DATA / "config.json"
    if not path.exists():
        return {}
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ConfigError(
            f"config.json is not valid JSON: line {error.lineno}, column {error.colno}"
        ) from error
    if not isinstance(config, dict):
        raise ConfigError("config.json must contain a JSON object")
    schema = config.get("schema_version")
    if schema is not None and (type(schema) is not int or schema != CONFIG_SCHEMA_VERSION):
        raise ConfigError(
            f"unsupported config schema {schema}; supported schema is {CONFIG_SCHEMA_VERSION}"
        )
    return config


def write_config(
    config: dict[str, object], installed: list[str], default: str
) -> None:
    path = DATA / "config.json"
    config["schema_version"] = CONFIG_SCHEMA_VERSION
    config["providers"] = {"installed": installed, "default": default}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=".config-", delete=False
        ) as handle:
            temporary = pathlib.Path(handle.name)
            json.dump(config, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def choose_default(
    detections: list[Detection], requested: str | None, non_interactive: bool
) -> tuple[str | None, str | None]:
    compatible = [item for item in detections if item.compatible]
    if not compatible:
        return None, "No compatible Provider found"
    available = {item.provider.key: item for item in compatible}
    if requested is not None:
        if requested not in available:
            provider = next(item for item in PROVIDERS if item.key == requested)
            return None, f"{provider.label} is not compatible"
        return requested, None
    if len(compatible) == 1:
        return compatible[0].provider.key, None
    if non_interactive:
        return None, "--default-provider is required when both Providers are compatible"
    print("Choose the Default provider:")
    for index, item in enumerate(compatible, start=1):
        print(f"  {index}. {item.provider.label}")
    try:
        answer = input("Default provider: ").strip().casefold()
    except EOFError:
        return None, "Default provider selection required"
    choices = {
        str(index): item.provider.key
        for index, item in enumerate(compatible, start=1)
    }
    choices.update({item.provider.key: item.provider.key for item in compatible})
    if answer not in choices:
        return None, f"invalid Default provider selection: {answer or 'empty'}"
    return choices[answer], None


def configure(args: argparse.Namespace) -> int:
    try:
        config = read_config()
    except ConfigError as error:
        print(error, file=sys.stderr)
        return 2
    detections = [detect(provider) for provider in PROVIDERS]
    sys.stdout.write(render(detections))
    default, error = choose_default(
        detections, args.default_provider, args.non_interactive
    )
    if error is not None:
        print(error, file=sys.stderr)
        return 1 if not any(item.compatible for item in detections) else 2
    installed = [item.provider.key for item in detections if item.compatible]
    write_config(config, installed, default)
    label = next(item.label for item in PROVIDERS if item.key == default)
    print(f"Configured Providers: {', '.join(installed)}")
    print(f"Default provider: {label}")
    return 0


def parse_args(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="providers.py")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("providers", add_help=False)
    configure_parser = subparsers.add_parser("configure", add_help=False)
    configure_parser.add_argument("--non-interactive", action="store_true")
    configure_parser.add_argument(
        "--default-provider", choices=[provider.key for provider in PROVIDERS]
    )
    return parser.parse_args(args)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    parsed = parse_args(args)
    if parsed.command == "configure":
        return configure(parsed)
    detections = [detect(provider) for provider in PROVIDERS]
    sys.stdout.write(render(detections))
    return 0 if any(item.compatible for item in detections) else 1


if __name__ == "__main__":
    raise SystemExit(main())
