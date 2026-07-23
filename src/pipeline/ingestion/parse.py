import re
import xml.etree.ElementTree as ET

NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

VERSION_PATTERN = re.compile(r"v(\d+)$")


def parse_identifier(source_url: str) -> tuple[str, int]:
    versioned_id = source_url.split("/abs/")[-1]
    match = VERSION_PATTERN.search(versioned_id)

    if match:
        version = int(match.group(1))
        arxiv_id = VERSION_PATTERN.sub("", versioned_id)
    else:
        version = 1
        arxiv_id = versioned_id

    return arxiv_id, version


def parse_feed(xml: bytes, raw_page: str) -> list[dict]:
    root = ET.fromstring(xml)
    papers = []

    for entry in root.findall("atom:entry", NAMESPACES):
        links = {
            link.attrib.get("title") or link.attrib.get("rel"):
            link.attrib["href"]
            for link in entry.findall("atom:link", NAMESPACES)
        }

        source_url = links["alternate"]
        arxiv_id, version = parse_identifier(source_url)

        primary = entry.find("arxiv:primary_category", NAMESPACES)

        papers.append(
            {
                "arxiv_id": arxiv_id,
                "version": version,
                "title": entry.findtext(
                    "atom:title", default="", namespaces=NAMESPACES
                ).strip(),
                "abstract": entry.findtext(
                    "atom:summary", default="", namespaces=NAMESPACES
                ).strip(),
                "authors": [
                    author.findtext(
                        "atom:name", default="", namespaces=NAMESPACES
                    ).strip()
                    for author in entry.findall("atom:author", NAMESPACES)
                ],
                "categories": [
                    category.attrib["term"]
                    for category in entry.findall("atom:category", NAMESPACES)
                ],
                "primary_category": (
                    primary.attrib.get("term") if primary is not None else None
                ),
                "published_at": entry.findtext(
                    "atom:published", namespaces=NAMESPACES
                ),
                "updated_at": entry.findtext(
                    "atom:updated", namespaces=NAMESPACES
                ),
                "license": entry.findtext(
                    "arxiv:license", default=None, namespaces=NAMESPACES
                ),
                "pdf_url": links.get("pdf"),
                "source_url": source_url,
                "raw_page": raw_page,
            }
        )

    return papers