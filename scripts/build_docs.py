"""Build docs/ directory from root content for MkDocs."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).parent.parent
DOCS = ROOT / "docs"
RADAR_SRC = ROOT / "radar"
RADAR_DST = DOCS / "radar"

COPY_DIRS = ["chapters"]
COPY_FILES = ["index.md", "CHANGELOG.md"]


def _render_yaml_to_markdown(yaml_path: Path) -> str:
    """Render a radar YAML file as a markdown page with a table."""
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    title = yaml_path.stem.replace("-", " ").title()
    description = raw.get("description", "")
    last_updated = raw.get("last_updated", "")
    columns: list[dict[str, str]] = raw.get("columns", [])
    rows: list[dict[str, Any]] = raw.get("rows") or []

    lines: list[str] = [f"# Radar: {title}\n"]
    if description:
        lines.append(f"> {description}\n")
    if last_updated:
        lines.append(f"*Letztes Update: {last_updated}*\n")

    if not columns:
        lines.append("\n*(Keine Spalten definiert)*\n")
        return "\n".join(lines)

    col_names = [c["name"] for c in columns]
    col_keys = [c["name"].lower().replace("-", "_").replace(" ", "_") for c in columns]

    lines.append("")
    lines.append("| " + " | ".join(col_names) + " |")
    lines.append("|" + "|".join(["---"] * len(col_names)) + "|")

    if not rows:
        lines.append("| " + " | ".join(["—"] * len(col_names)) + " |")
    else:
        for row in rows:
            cells = [str(row.get(k, "")).replace("|", "\\|").replace("\n", " ") for k in col_keys]
            lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines) + "\n"


def _build_radar_index(radar_files: list[Path]) -> str:
    """Build a docs/radar/index.md summary page."""
    lines = ["# Radare\n", "Kontinuierlich gepflegte Monitoring-Streams ausserhalb der 13 Kapitel.\n", ""]
    lines.append("| Radar | Modus | Einträge | Letztes Update |")
    lines.append("|---|---|---|---|")
    for f in sorted(radar_files):
        name = f.stem
        if f.suffix == ".yaml":
            raw = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            count = len(raw.get("rows") or [])
            last = raw.get("last_updated", "—")
            lines.append(f"| [{name}]({name}.md) | list | {count} | {last} |")
        elif f.suffix == ".md":
            import re

            content = f.read_text(encoding="utf-8")
            count = len(re.findall(r"^### \d{4}-\d{2}-\d{2}", content, re.MULTILINE))
            lines.append(f"| [{name}]({name}.md) | feed | {count} | — |")
    return "\n".join(lines) + "\n"


def _build_radar() -> int:
    """Render radar/ content into docs/radar/. Returns number of pages written."""
    if not RADAR_SRC.exists():
        return 0
    RADAR_DST.mkdir(parents=True, exist_ok=True)

    radar_files: list[Path] = []
    count = 0

    for yaml_file in sorted(RADAR_SRC.glob("*.yaml")):
        md_out = RADAR_DST / f"{yaml_file.stem}.md"
        md_out.write_text(_render_yaml_to_markdown(yaml_file), encoding="utf-8")
        radar_files.append(yaml_file)
        count += 1

    for md_file in sorted(RADAR_SRC.glob("*.md")):
        shutil.copy2(md_file, RADAR_DST / md_file.name)
        radar_files.append(md_file)
        count += 1

    if radar_files:
        (RADAR_DST / "index.md").write_text(_build_radar_index(radar_files), encoding="utf-8")

    return count


def build() -> None:
    """Copy content files into docs/ for MkDocs build."""
    if DOCS.exists():
        shutil.rmtree(DOCS)
    DOCS.mkdir()

    for d in COPY_DIRS:
        src = ROOT / d
        if src.exists():
            shutil.copytree(src, DOCS / d)

    for f in COPY_FILES:
        src = ROOT / f
        if src.exists():
            shutil.copy2(src, DOCS / f)

    radar_count = _build_radar()

    md_count = sum(1 for _ in DOCS.rglob("*.md"))
    print(f"Built docs/: {md_count} markdown files ({radar_count} radar pages)")


if __name__ == "__main__":
    build()
