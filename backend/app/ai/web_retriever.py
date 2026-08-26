from html import (
    unescape,
)

from urllib.parse import (
    urljoin,
    urlparse,
    urldefrag,
)

import httpx

from bs4 import (
    BeautifulSoup,
)

from app.ai.web_sources import (
    ApprovedWebSource,
)


USER_AGENT = (
    "NIBGPT-Web-Intelligence/1.0 "
    "(NIB International Bank)"
)


# ============================================================
# URL validation
# ============================================================


def validate_url(
    url: str,
    source: ApprovedWebSource,
) -> str:
    parsed = urlparse(
        url
    )

    if parsed.scheme not in {
        "http",
        "https",
    }:
        raise ValueError(
            "Unsupported URL scheme."
        )

    hostname = (
        parsed.hostname
        or ""
    ).lower()

    if hostname not in (
        source.allowed_domains
    ):
        raise ValueError(
            "URL is outside the approved "
            "web source."
        )

    return url


# ============================================================
# Clean HTML
# ============================================================


def clean_page_text(
    html: str,
) -> tuple[
    str,
    str | None,
]:
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    title = None

    if soup.title:
        title = (
            soup.title
            .get_text(
                " ",
                strip=True,
            )
        )

    for tag in soup(
        [
            "script",
            "style",
            "noscript",
            "svg",
            "iframe",
        ]
    ):
        tag.decompose()

    text = soup.get_text(
        "\n",
        strip=True,
    )

    lines = []

    for line in text.splitlines():
        cleaned = (
            " ".join(
                line.split()
            )
        )

        if not cleaned:
            continue

        lines.append(
            unescape(
                cleaned
            )
        )

    return (
        "\n".join(
            lines
        ),
        title,
    )


# ============================================================
# Fetch one approved page
# ============================================================


def fetch_page(
    url: str,
    source: ApprovedWebSource,
) -> dict:
    approved_url = (
        validate_url(
            url,
            source,
        )
    )

    headers = {
        "User-Agent":
            USER_AGENT,

        "Accept":
            (
                "text/html,"
                "application/xhtml+xml"
            ),
    }

    with httpx.Client(
        timeout=20.0,
        follow_redirects=True,
        headers=headers,
    ) as client:
        response = client.get(
            approved_url
        )

        response.raise_for_status()

        final_url = str(
            response.url
        )

        # Validate again after redirect.
        validate_url(
            final_url,
            source,
        )

        text, title = (
            clean_page_text(
                response.text
            )
        )
        
        sections = (
            extract_structured_sections(
                response.text
            )
        )

    return {
        "url":
            final_url,

        "title":
            title,

        "text":
            text,

        "sections":
            sections,
    }


# ============================================================
# Normalize discovered internal URLs
# ============================================================


def normalize_discovered_url(
    url: str,
    source: ApprovedWebSource,
) -> str | None:
    try:
        clean_url, _ = (
            urldefrag(
                url
            )
        )

        parsed = urlparse(
            clean_url
        )

        hostname = (
            parsed.hostname
            or ""
        ).lower()

        if parsed.scheme not in {
            "http",
            "https",
        }:
            return None

        if hostname not in (
            source.allowed_domains
        ):
            return None

        blocked_extensions = (
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".svg",
            ".webp",
            ".css",
            ".js",
            ".zip",
            ".rar",
            ".7z",
            ".mp4",
            ".mp3",
            ".wav",
            ".avi",
            ".mov",
            ".woff",
            ".woff2",
            ".ttf",
        )

        if (
            parsed.path
            .lower()
            .endswith(
                blocked_extensions
            )
        ):
            return None

        return clean_url

    except Exception:
        return None


# ============================================================
# Discover links from NIB website
# ============================================================


def discover_internal_links(
    source: ApprovedWebSource,
    start_url: str | None = None,
    maximum_links: int = 80,
) -> list[str]:
    root_url = (
        start_url
        or source.base_url
    )

    validate_url(
        root_url,
        source,
    )

    headers = {
        "User-Agent":
            USER_AGENT,

        "Accept":
            (
                "text/html,"
                "application/xhtml+xml"
            ),
    }

    with httpx.Client(
        timeout=20.0,
        follow_redirects=True,
        headers=headers,
    ) as client:
        response = client.get(
            root_url
        )

        response.raise_for_status()

        final_url = str(
            response.url
        )

        validate_url(
            final_url,
            source,
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

    discovered = []
    seen = set()

    # Include the root page itself.
    normalized_root = (
        normalize_discovered_url(
            final_url,
            source,
        )
    )

    if normalized_root:
        seen.add(
            normalized_root
        )

        discovered.append(
            normalized_root
        )

    for anchor in soup.find_all(
        "a",
        href=True,
    ):
        href = (
            anchor.get(
                "href"
            )
            or ""
        ).strip()

        if not href:
            continue

        absolute_url = (
            urljoin(
                final_url,
                href,
            )
        )

        approved_url = (
            normalize_discovered_url(
                absolute_url,
                source,
            )
        )

        if not approved_url:
            continue

        if approved_url in seen:
            continue

        seen.add(
            approved_url
        )

        discovered.append(
            approved_url
        )

        if (
            len(discovered)
            >= maximum_links
        ):
            break

    return discovered


# ============================================================
# Fetch automatically discovered pages
# ============================================================


def fetch_discovered_pages(
    source: ApprovedWebSource,
    maximum_pages: int = 30,
) -> list[dict]:
    urls = (
        discover_internal_links(
            source=source,
            maximum_links=(
                maximum_pages * 3
            ),
        )
    )

    pages = []

    for url in urls:
        if (
            len(pages)
            >= maximum_pages
        ):
            break

        try:
            page = fetch_page(
                url=url,
                source=source,
            )

            text = (
                page.get(
                    "text"
                )
                or ""
            )

            # Ignore empty/useless pages.
            if len(text) < 80:
                continue

            pages.append(
                page
            )

        except Exception as error:
            print(
                "WEB FETCH WARNING:",
                url,
                str(error),
            )

            continue

    return pages

def extract_structured_sections(
    html: str,
) -> list[dict]:
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    sections = []

    # ========================================================
    # HTMega tab sections
    #
    # NIB Executive Management page uses:
    #
    # <a data-toggle="htbtab"
    #    href="#htmegatab-...">
    #     Department Directors
    # </a>
    #
    # and the actual content exists in an element whose
    # id matches the href target.
    # ========================================================

    tab_links = soup.select(
        (
            ".htmega-tab-nav "
            "a[data-toggle='htbtab'][href^='#']"
        )
    )

    for tab in tab_links:
        heading = (
            " ".join(
                tab.get_text(
                    " ",
                    strip=True,
                ).split()
            )
        )

        target = (
            tab.get("href")
            or ""
        ).strip()

        if (
            not heading
            or not target.startswith("#")
        ):
            continue

        target_id = (
            target[1:]
        )

        panel = soup.find(
            id=target_id
        )

        if panel is None:
            continue

        # Work on a separate parsed copy so removing
        # unwanted tags does not alter the main soup.
        panel_soup = BeautifulSoup(
            str(panel),
            "html.parser",
        )

        for tag in panel_soup(
            [
                "script",
                "style",
                "noscript",
                "svg",
                "iframe",
            ]
        ):
            tag.decompose()

        raw_text = (
            panel_soup.get_text(
                "\n",
                strip=True,
            )
        )

        lines = []

        for line in (
            raw_text.splitlines()
        ):
            cleaned = (
                " ".join(
                    line.split()
                )
            )

            if not cleaned:
                continue

            lines.append(
                unescape(
                    cleaned
                )
            )

        content = "\n".join(
            lines
        ).strip()

        if not content:
            continue

        sections.append(
            {
                "heading":
                    heading,

                "target_id":
                    target_id,

                "content":
                    content,
            }
        )

    # ========================================================
    # If tab sections were found, use them.
    # This prevents generic heading extraction from mixing
    # different management groups.
    # ========================================================

    if sections:
        return sections

    # ========================================================
    # Generic fallback for normal website pages
    # ========================================================

    heading_tags = [
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
    ]

    for heading_tag in soup.find_all(
        heading_tags
    ):
        heading_text = (
            " ".join(
                heading_tag
                .get_text(
                    " ",
                    strip=True,
                )
                .split()
            )
        )

        if not heading_text:
            continue

        content = []

        sibling = (
            heading_tag.next_sibling
        )

        while sibling:
            sibling_name = getattr(
                sibling,
                "name",
                None,
            )

            if sibling_name in heading_tags:
                break

            if hasattr(
                sibling,
                "get_text",
            ):
                sibling_text = (
                    " ".join(
                        sibling
                        .get_text(
                            " ",
                            strip=True,
                        )
                        .split()
                    )
                )

                if sibling_text:
                    content.append(
                        sibling_text
                    )

            sibling = (
                sibling.next_sibling
            )

        if content:
            sections.append(
                {
                    "heading":
                        heading_text,

                    "target_id":
                        None,

                    "content":
                        "\n".join(
                            content
                        ),
                }
            )

    return sections


# ============================================================
# Fetch known fallback pages
# ============================================================


def fetch_source_pages(
    source: ApprovedWebSource,
    paths: list[str],
) -> list[dict]:
    pages = []

    for path in paths:
        url = urljoin(
            source.base_url,
            path,
        )

        try:
            page = fetch_page(
                url=url,
                source=source,
            )

            pages.append(
                page
            )

        except Exception as error:
            pages.append(
                {
                    "url":
                        url,

                    "title":
                        None,

                    "text":
                        "",

                    "error":
                        str(error),
                }
            )
    
    return pages