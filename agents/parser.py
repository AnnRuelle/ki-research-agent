"""Vier-Zonen-Parser: parse and reassemble Markdown documents with four protected zones."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Zone headers — order matters
ZONE_HEADERS = [
    "## Überblick",
    "## Eigene Notizen",
    "## Schlüsselquellen",
    "## Changelog",
]

# Regex to match any h2 header
H2_PATTERN = re.compile(r"^## .+$", re.MULTILINE)


@dataclass
class FourZoneDocument:
    """A parsed Vier-Zonen document."""

    title: str
    overview: str  # Zone 1: Überblick
    own_notes: str  # Zone 2: Eigene Notizen (PROTECTED)
    key_sources: str  # Zone 3: Schlüsselquellen
    changelog: str  # Zone 4: Changelog

    def to_markdown(self) -> str:
        """Reassemble the document as Markdown."""
        parts = [
            f"# {self.title}",
            "",
            "## Überblick",
            "",
            self.overview.strip(),
            "",
            "## Eigene Notizen",
            "",
            self.own_notes.strip(),
            "",
            "## Schlüsselquellen",
            "",
            self.key_sources.strip(),
            "",
            "## Changelog",
            "",
            self.changelog.strip(),
            "",
        ]
        return "\n".join(parts)


class ParserError(Exception):
    """Raised when a document cannot be parsed as Vier-Zonen format."""


def parse(markdown: str) -> FourZoneDocument:
    """Parse a Markdown string into a FourZoneDocument.

    Raises ParserError if the document is missing required zones.
    """
    lines = markdown.strip().split("\n")

    # Extract title from first h1
    title = ""
    content_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            title = stripped[2:].strip()
            content_start = i + 1
            break

    if not title:
        raise ParserError("No h1 title found in document")

    remaining = "\n".join(lines[content_start:])

    # Find each zone by its header
    zones: dict[str, str] = {}
    zone_positions: list[tuple[int, str]] = []

    for header in ZONE_HEADERS:
        pos = remaining.find(header)
        if pos == -1:
            raise ParserError(f"Missing required zone header: {header}")
        zone_positions.append((pos, header))

    # Sort by position (should already be in order, but be safe)
    zone_positions.sort(key=lambda x: x[0])

    # Extract content between zone headers
    for i, (pos, header) in enumerate(zone_positions):
        start = pos + len(header)
        if i + 1 < len(zone_positions):
            end = zone_positions[i + 1][0]
        else:
            end = len(remaining)
        zones[header] = remaining[start:end].strip()

    return FourZoneDocument(
        title=title,
        overview=zones["## Überblick"],
        own_notes=zones["## Eigene Notizen"],
        key_sources=zones["## Schlüsselquellen"],
        changelog=zones["## Changelog"],
    )


def validate_own_notes_unchanged(original: str, modified: str) -> bool:
    """Check that the 'Eigene Notizen' zone is byte-identical between original and modified."""
    original_doc = parse(original)
    modified_doc = parse(modified)
    return original_doc.own_notes == modified_doc.own_notes
