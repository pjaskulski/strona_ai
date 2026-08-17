#!/usr/bin/env python3
"""Validate canonical URLs, social metadata, JSON-LD, robots and sitemap."""

from __future__ import annotations

import argparse
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree


SITE_URL = "https://ai.ihpan.edu.pl"
REQUIRED_OPEN_GRAPH = {
    "og:type",
    "og:site_name",
    "og:title",
    "og:description",
    "og:url",
    "og:locale",
    "og:image",
    "og:image:alt",
}
REQUIRED_TWITTER = {
    "twitter:card",
    "twitter:title",
    "twitter:description",
    "twitter:image",
    "twitter:image:alt",
}


class SeoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.in_title = False
        self.meta_names: dict[str, str] = {}
        self.meta_properties: dict[str, str] = {}
        self.canonical = ""
        self.is_redirect = False
        self.in_json_ld = False
        self.json_ld_parts: list[str] = []

    @property
    def title(self) -> str:
        return " ".join("".join(self.title_parts).split())

    @property
    def json_ld(self) -> str:
        return "".join(self.json_ld_parts).strip()

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            content = (attributes.get("content") or "").strip()
            name = (attributes.get("name") or "").lower()
            prop = (attributes.get("property") or "").lower()
            if name:
                self.meta_names[name] = content
            if prop:
                self.meta_properties[prop] = content
            if (attributes.get("http-equiv") or "").lower() == "refresh":
                self.is_redirect = True
        elif tag == "link" and (attributes.get("rel") or "").lower() == "canonical":
            self.canonical = (attributes.get("href") or "").strip()
        elif tag == "script" and (attributes.get("type") or "").lower() == "application/ld+json":
            self.in_json_ld = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        elif tag == "script" and self.in_json_ld:
            self.in_json_ld = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self.in_json_ld:
            self.json_ld_parts.append(data)


def public_url(path: Path, root: Path) -> str:
    relative = path.relative_to(root).as_posix()
    if relative == "index.html":
        return "/"
    if relative.endswith("/index.html"):
        return f"/{relative[:-10]}"
    return f"/{relative}"


def local_image_exists(value: str, root: Path) -> bool:
    parts = urlsplit(value)
    return (
        parts.scheme == "https"
        and parts.netloc == "ai.ihpan.edu.pl"
        and (root / parts.path.lstrip("/")).is_file()
    )


def validate_html(root: Path) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    indexable_urls: set[str] = set()
    titles: dict[str, Path] = {}

    for path in sorted(root.rglob("*.html")):
        parser = SeoParser()
        parser.feed(path.read_text(encoding="utf-8"))
        parser.close()
        relative = path.relative_to(root.parent)
        location = str(relative)
        robots = parser.meta_names.get("robots", "").lower()

        if not parser.title:
            errors.append(f"{location}: missing title")
        elif not parser.is_redirect and "noindex" not in robots:
            previous = titles.get(parser.title)
            if previous:
                errors.append(
                    f"{location}: duplicate title also used by {previous}"
                )
            titles[parser.title] = relative

        if parser.is_redirect:
            if "noindex" not in robots:
                errors.append(f"{location}: redirect must be noindex")
            if not parser.canonical.startswith(f"{SITE_URL}/"):
                errors.append(f"{location}: redirect canonical is invalid")
            continue

        if "noindex" in robots:
            continue

        expected_canonical = f"{SITE_URL}{public_url(path, root)}"
        if parser.canonical != expected_canonical:
            errors.append(
                f"{location}: canonical {parser.canonical!r} does not match "
                f"{expected_canonical!r}"
            )
        else:
            indexable_urls.add(expected_canonical)

        description = parser.meta_names.get("description", "")
        if not 50 <= len(description) <= 180:
            errors.append(
                f"{location}: description length must be 50-180 characters "
                f"(got {len(description)})"
            )

        missing_og = REQUIRED_OPEN_GRAPH - parser.meta_properties.keys()
        if missing_og:
            errors.append(
                f"{location}: missing Open Graph fields: "
                f"{', '.join(sorted(missing_og))}"
            )
        missing_twitter = REQUIRED_TWITTER - parser.meta_names.keys()
        if missing_twitter:
            errors.append(
                f"{location}: missing Twitter fields: "
                f"{', '.join(sorted(missing_twitter))}"
            )

        if parser.meta_properties.get("og:url") != parser.canonical:
            errors.append(f"{location}: og:url must match canonical")
        if not local_image_exists(parser.meta_properties.get("og:image", ""), root):
            errors.append(f"{location}: og:image does not resolve locally")

        if not parser.json_ld:
            errors.append(f"{location}: missing JSON-LD")
        else:
            try:
                structured_data = json.loads(parser.json_ld)
            except json.JSONDecodeError as error:
                errors.append(f"{location}: invalid JSON-LD: {error}")
            else:
                if structured_data.get("@context") != "https://schema.org":
                    errors.append(f"{location}: unexpected JSON-LD context")
                if not structured_data.get("@graph"):
                    errors.append(f"{location}: JSON-LD graph is empty")

    return errors, indexable_urls


def validate_discovery_files(root: Path, expected_urls: set[str]) -> list[str]:
    errors: list[str] = []
    robots_path = root / "robots.txt"
    sitemap_path = root / "sitemap.xml"

    if not robots_path.is_file():
        errors.append("html/robots.txt: file is missing")
    elif f"Sitemap: {SITE_URL}/sitemap.xml" not in robots_path.read_text(
        encoding="utf-8"
    ):
        errors.append("html/robots.txt: sitemap URL is missing or invalid")

    if not sitemap_path.is_file():
        errors.append("html/sitemap.xml: file is missing")
        return errors

    try:
        sitemap = ElementTree.parse(sitemap_path)
    except ElementTree.ParseError as error:
        errors.append(f"html/sitemap.xml: invalid XML: {error}")
        return errors

    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    sitemap_urls = {
        (element.text or "").strip()
        for element in sitemap.findall("s:url/s:loc", namespace)
    }
    missing = expected_urls - sitemap_urls
    unexpected = sitemap_urls - expected_urls
    if missing:
        errors.append(f"html/sitemap.xml: missing URLs: {', '.join(sorted(missing))}")
    if unexpected:
        errors.append(
            f"html/sitemap.xml: unexpected URLs: {', '.join(sorted(unexpected))}"
        )
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

    errors, indexable_urls = validate_html(root)
    errors.extend(validate_discovery_files(root, indexable_urls))
    if errors:
        print("SEO validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        f"Checked SEO metadata and discovery files for "
        f"{len(indexable_urls)} indexable pages."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
