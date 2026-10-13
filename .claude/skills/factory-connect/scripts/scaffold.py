#!/usr/bin/env python3
"""Create a new D365 CE factory project from this repo.

Copies the factory (agents, skills, dashboard, auth helper) into an empty
folder, renames the source environment's solution, prefix, plugin project and
Dataverse MCP server to the new ones, and writes CLAUDE.md, ANTIGRAVITY.md and
README.md from templates. Copies no solution files, code or job history.

Usage:
  python3 scaffold.py --target <dir> --title "<Title>" --url https://<org>.crm5.dynamics.com \
      --solution <UniqueName> --solution-display "<Display Name>" --prefix <prefix>
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

SKILL = Path(__file__).resolve().parents[1]
SOURCE = SKILL.parents[2]  # .claude/skills/factory-connect -> repo root

# Copied as-is, then renamed (except the factory-connect skill, which stays generic).
COPY = [
    ".claude/agents",
    ".claude/skills/factory",
    ".claude/skills/factory-connect",
    ".agents/agents",
    ".agents/skills/factory",
    ".agents/skills/factory-connect",
    "factory/dashboard.html",
    "scripts/auth.py",
    ".gitignore",
]
NO_RENAME = (".claude/skills/factory-connect", ".agents/skills/factory-connect")


def source_tokens():
    """Read the source repo's solution, prefix, plugin project and MCP org."""
    claude = (SOURCE / "CLAUDE.md").read_text()
    mcp = json.loads((SOURCE / ".mcp.json").read_text())
    org = next(k for k in mcp["mcpServers"] if k.startswith("dataverse-"))[len("dataverse-"):]
    solution = re.search(r"Solution: `([^`]+)`", claude).group(1)
    prefix = re.search(r"\(`(\w+)` prefix\)", claude).group(1)
    plugins = re.search(r"plugins/(\w+)\.sln", claude).group(1)
    return {"org": org, "solution": solution, "prefix": prefix, "plugins": plugins}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--target", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--url", required=True)
    p.add_argument("--solution", required=True)
    p.add_argument("--solution-display", required=True)
    p.add_argument("--prefix", required=True)
    a = p.parse_args()

    if not re.fullmatch(r"[a-z][a-z0-9]{1,7}", a.prefix) or a.prefix.startswith("mscrm"):
        sys.exit("prefix must be 2-8 lowercase letters/digits, starting with a letter, not mscrm")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", a.solution):
        sys.exit("solution unique name: letters, digits and underscores only")
    host = urlparse(a.url).hostname or ""
    if not host.endswith(".dynamics.com"):
        sys.exit("url must be https://<org>.<region>.dynamics.com")
    url = f"https://{host}"
    target = Path(a.target).expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        sys.exit(f"{target} exists and is not empty")

    old = source_tokens()
    new = {
        "org": host.split(".")[0],
        "solution": a.solution,
        "prefix": a.prefix,
        "plugins": a.prefix.capitalize() + "Plugins",
    }
    renames = [
        (f"dataverse-{old['org']}", f"dataverse-{new['org']}"),
        (old["solution"], new["solution"]),
        (old["plugins"], new["plugins"]),
        (f"`{old['prefix']}`", f"`{new['prefix']}`"),
    ]

    target.mkdir(parents=True, exist_ok=True)
    changed = 0
    for rel in COPY:
        src = SOURCE / rel
        if not src.exists():
            continue
        files = [src] if src.is_file() else [f for f in src.rglob("*") if f.is_file()]
        for f in files:
            if f.name == ".DS_Store" or "__pycache__" in f.parts:
                continue
            out = target / f.relative_to(SOURCE)
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, out)
            if out.suffix == ".md" and not rel.startswith(NO_RENAME):
                text = out.read_text()
                for x, y in renames:
                    text = text.replace(x, y)
                if text != f.read_text():
                    out.write_text(text)
                    changed += 1

    fill = {
        "{{TITLE}}": a.title,
        "{{URL}}": url,
        "{{ORG}}": new["org"],
        "{{SOLUTION}}": new["solution"],
        "{{SOLUTION_DISPLAY}}": a.solution_display,
        "{{PREFIX}}": new["prefix"],
        "{{PLUGINS}}": new["plugins"],
    }
    for name in ("CLAUDE.md", "ANTIGRAVITY.md", "README.md"):
        text = (SKILL / "templates" / name).read_text()
        for x, y in fill.items():
            text = text.replace(x, y)
        (target / name).write_text(text)
    for link in ("AGENTS.md", "GEMINI.md"):
        try:
            (target / link).symlink_to("ANTIGRAVITY.md")
        except OSError:  # Windows without symlink rights
            shutil.copy2(target / "ANTIGRAVITY.md", target / link)

    (target / "factory").mkdir(exist_ok=True)
    (target / "factory/backlog.md").write_text(
        "# Backlog\n\n`/factory next` builds the first unchecked item and checks it off with its job id.\n"
    )
    (target / "factory/board.json").write_text('{\n  "jobs": []\n}\n')

    print(f"Created {target}")
    print(f"Renamed in {changed} agent/skill files: " + ", ".join(f"{x} -> {y}" for x, y in renames))
    print(f"Plugin project name for later: {new['plugins']}")


if __name__ == "__main__":
    main()
