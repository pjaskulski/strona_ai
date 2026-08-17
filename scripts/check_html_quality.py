#!/usr/bin/env python3
"""Check generated HTML for basic accessibility and security regressions."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


HEADING_TAGS = {f"h{level}": level for level in range(1, 7)}
FORM_CONTROLS = {"input", "select", "textarea"}


class QualityParser(HTMLParser):
    def __init__(self, source: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self.errors: list[str] = []
        self.ids: Counter[str] = Counter()
        self.label_targets: set[str] = set()
        self.unlabelled_controls: list[tuple[int, str, str]] = []
        self.headings: list[tuple[int, int]] = []
        self.html_lang = ""
        self.has_title = False
        self.has_viewport = False
        self.is_redirect = False

    def error(self, line: int, message: str) -> None:
        self.errors.append(f"{self.source}:{line}: {message}")

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        line, _ = self.getpos()
        names = [name for name, _ in attrs]
        for name, count in Counter(names).items():
            if count > 1:
                self.error(line, f"duplicate {name!r} attribute on <{tag}>")

        attributes = dict(attrs)
        element_id = attributes.get("id")
        if element_id:
            self.ids[element_id] += 1

        if tag == "html":
            self.html_lang = (attributes.get("lang") or "").strip()
        elif tag == "title":
            self.has_title = True
        elif tag == "meta":
            name = (attributes.get("name") or "").lower()
            http_equiv = (attributes.get("http-equiv") or "").lower()
            if name == "viewport":
                self.has_viewport = True
            if http_equiv == "refresh":
                self.is_redirect = True
        elif tag in HEADING_TAGS:
            self.headings.append((HEADING_TAGS[tag], line))
        elif tag == "img" and "alt" not in attributes:
            self.error(line, "<img> is missing an alt attribute")
        elif tag == "iframe" and not (attributes.get("title") or "").strip():
            self.error(line, "<iframe> is missing a title")
        elif tag == "button" and not (attributes.get("type") or "").strip():
            self.error(line, "<button> is missing an explicit type")
        elif tag == "label" and attributes.get("for"):
            self.label_targets.add(attributes["for"])

        if tag == "a":
            href = (attributes.get("href") or "").strip().lower()
            if href.startswith("javascript:"):
                self.error(line, "javascript: URL is not allowed")
            if attributes.get("target") == "_blank":
                rel = set((attributes.get("rel") or "").lower().split())
                if "noopener" not in rel:
                    self.error(line, 'target="_blank" requires rel="noopener"')

        for name in names:
            if name.lower().startswith("on"):
                self.error(line, f"inline event handler {name!r} is not allowed")

        if tag in FORM_CONTROLS:
            control_type = (attributes.get("type") or "").lower()
            if tag == "input" and control_type == "hidden":
                return
            has_aria_label = bool(
                (attributes.get("aria-label") or "").strip()
                or (attributes.get("aria-labelledby") or "").strip()
            )
            if not has_aria_label:
                self.unlabelled_controls.append(
                    (line, tag, attributes.get("id") or "")
                )

    def finish(self) -> list[str]:
        if not self.html_lang:
            self.error(1, "document language is missing")
        if not self.has_title:
            self.error(1, "document title is missing")
        if not self.has_viewport:
            self.error(1, "viewport metadata is missing")

        for element_id, count in self.ids.items():
            if count > 1:
                self.error(1, f"duplicate id {element_id!r}")

        for line, tag, element_id in self.unlabelled_controls:
            if not element_id or element_id not in self.label_targets:
                self.error(line, f"<{tag}> has no accessible label")

        if not self.is_redirect:
            levels = [level for level, _ in self.headings]
            if levels.count(1) != 1:
                self.error(1, "document must contain exactly one <h1>")
            for (previous, _), (current, line) in zip(
                self.headings, self.headings[1:]
            ):
                if current > previous + 1:
                    self.error(
                        line,
                        f"heading level jumps from h{previous} to h{current}",
                    )

        return self.errors


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(root.rglob("*.html")):
        relative_path = path.relative_to(root.parent)
        parser = QualityParser(relative_path)
        try:
            parser.feed(path.read_text(encoding="utf-8"))
            parser.close()
        except (OSError, UnicodeError) as error:
            errors.append(f"{relative_path}: cannot read document: {error}")
            continue
        errors.extend(parser.finish())
    return errors


def main() -> int:
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path("html"),
        help="published site directory (default: html)",
    )
    args = argument_parser.parse_args()
    root = args.root.resolve()

    if not root.is_dir():
        print(f"error: site directory does not exist: {root}", file=sys.stderr)
        return 2

    errors = validate(root)
    if errors:
        print("HTML quality validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    document_count = sum(1 for _ in root.rglob("*.html"))
    print(
        f"Checked accessibility and security rules in {document_count} "
        "HTML documents."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
