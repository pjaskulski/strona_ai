#!/usr/bin/env python3
"""Validate local links, embedded resources, and HTML fragments."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


LINK_ATTRIBUTES = {"href", "src"}
IGNORED_SCHEMES = {"data", "javascript", "mailto", "tel"}


@dataclass(frozen=True)
class Reference:
    source: Path
    line: int
    attribute: str
    value: str


class DocumentParser(HTMLParser):
    def __init__(self, source: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self.ids: set[str] = set()
        self.references: list[Reference] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self._handle_attributes(attrs)

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self._handle_attributes(attrs)

    def _handle_attributes(self, attrs: list[tuple[str, str | None]]) -> None:
        line, _ = self.getpos()
        for name, value in attrs:
            if value is None:
                continue
            if name == "id":
                self.ids.add(value)
            if name in LINK_ATTRIBUTES:
                self.references.append(
                    Reference(self.source, line, name, value)
                )


def parse_document(path: Path) -> DocumentParser:
    parser = DocumentParser(path)
    try:
        parser.feed(path.read_text(encoding="utf-8"))
        parser.close()
    except (OSError, UnicodeError) as error:
        raise RuntimeError(f"cannot read {path}: {error}") from error
    return parser


def resolve_target(reference: Reference, root: Path) -> tuple[Path, str] | None:
    value = reference.value
    if value != value.strip():
        return Path("__invalid_whitespace__"), ""

    parts = urlsplit(value)
    if parts.scheme.lower() in IGNORED_SCHEMES or parts.scheme or parts.netloc:
        return None

    path = unquote(parts.path)
    if not path:
        return reference.source, unquote(parts.fragment)

    if path.startswith("/"):
        target = root / path.lstrip("/")
    else:
        target = reference.source.parent / path
    return target.resolve(), unquote(parts.fragment)


def validate(root: Path) -> list[str]:
    documents: dict[Path, DocumentParser] = {}
    errors: list[str] = []

    for path in sorted(root.rglob("*.html")):
        resolved = path.resolve()
        try:
            documents[resolved] = parse_document(resolved)
        except RuntimeError as error:
            errors.append(str(error))

    for document in documents.values():
        for reference in document.references:
            resolved = resolve_target(reference, root)
            if resolved is None:
                continue

            target, fragment = resolved
            location = f"{reference.source.relative_to(root.parent)}:{reference.line}"
            if target.name == "__invalid_whitespace__":
                errors.append(
                    f"{location}: {reference.attribute} has surrounding whitespace: "
                    f"{reference.value!r}"
                )
                continue
            if not target.exists():
                errors.append(
                    f"{location}: missing target for {reference.attribute}: "
                    f"{reference.value!r}"
                )
                continue
            if not fragment:
                continue

            target_document = documents.get(target)
            if target_document is None:
                errors.append(
                    f"{location}: fragment points to a non-HTML target: "
                    f"{reference.value!r}"
                )
            elif fragment not in target_document.ids:
                errors.append(
                    f"{location}: missing fragment #{fragment} in "
                    f"{target.relative_to(root.parent)}"
                )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path("html"),
        help="published site directory (default: html)",
    )
    args = parser.parse_args()
    root = args.root.resolve()

    if not root.is_dir():
        print(f"error: site directory does not exist: {root}", file=sys.stderr)
        return 2

    errors = validate(root)
    if errors:
        print("Local link validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    document_count = sum(1 for _ in root.rglob("*.html"))
    print(f"Checked {document_count} HTML documents: no broken local links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
