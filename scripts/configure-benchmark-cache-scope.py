#!/usr/bin/env python3
"""Write one benchmark run's isolated adapter tags into the repo plan."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Optional


CACHE_TAG = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._-]{0,127}")
LANE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._-]{0,63}")


def replace_tag(source: str, adapter: str, tag: str) -> str:
    lines = source.splitlines(keepends=True)
    section = f"[adapters.{adapter}]"
    in_section = False
    replacements = 0

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_section = stripped == section
            continue
        if in_section and stripped.startswith("tag = "):
            ending = "\n" if line.endswith("\n") else ""
            lines[index] = f'tag = "{tag}"{ending}'
            replacements += 1

    if replacements != 1:
        raise SystemExit(f"expected one tag in {section}, found {replacements}")
    return "".join(lines)


def read_tag(source: str, adapter: str) -> Optional[str]:
    section = f"[adapters.{adapter}]"
    in_section = False
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_section = stripped == section
            continue
        if in_section and stripped.startswith("tag = "):
            return stripped.removeprefix("tag = ").strip('"')
    return None


def replace_lane(source: str, adapter: str, lane: str) -> str:
    lines = source.splitlines(keepends=True)
    section = f"[adapters.{adapter}]"
    in_section = False
    replacements = 0

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_section = stripped == section
            continue
        if in_section and stripped.startswith("metadata-hints = "):
            rendered, count = re.subn(r'"lane=[^"]+"', f'"lane={lane}"', line)
            lines[index] = rendered
            replacements += count

    if replacements != 1:
        raise SystemExit(f"expected one lane hint in {section}, found {replacements}")
    return "".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("plan", type=Path)
    parser.add_argument("--docker-tag", required=True)
    parser.add_argument("--ccache-tag", required=True)
    parser.add_argument("--lane", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for label, tag in (("Docker", args.docker_tag), ("ccache", args.ccache_tag)):
        if CACHE_TAG.fullmatch(tag) is None:
            raise SystemExit(f"invalid {label} cache tag: {tag}")
    if args.docker_tag == args.ccache_tag:
        raise SystemExit("Docker and ccache cache tags must differ")
    if LANE.fullmatch(args.lane) is None:
        raise SystemExit(f"invalid cache lane: {args.lane}")

    source = args.plan.read_text()
    rendered = replace_tag(source, "docker", args.docker_tag)
    rendered = replace_tag(rendered, "ccache", args.ccache_tag)
    rendered = replace_lane(rendered, "docker", args.lane)
    rendered = replace_lane(rendered, "ccache", args.lane)
    args.plan.write_text(rendered)

    written = args.plan.read_text()
    actual = (read_tag(written, "docker"), read_tag(written, "ccache"))
    expected = (args.docker_tag, args.ccache_tag)
    if actual != expected:
        raise SystemExit(f"cache plan contains the wrong tags: {actual}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
