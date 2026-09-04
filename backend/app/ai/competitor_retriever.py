from urllib.parse import (
    urljoin,
    urlparse,
    urldefrag,
)

from html import (
    unescape,
)

import httpx

from bs4 import (
    BeautifulSoup,
)

from app.ai.competitor_sources import (
    CompetitorSource,
)


USER_AGENT = (
    "NIBGPT-Competitor-Intelligence/1.0"
)


def validate_competitor_url(
    url: str,
    source: CompetitorSource,
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
            "competitor source."
        )

    return url


def clean_html_text(
    html: str,
) -> tuple[str, str | None]:
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    title = None

    if soup.title:
        title = (
            soup.title.get_text(
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

    lines = []

    for line in soup.get_text(
        "\n",
        strip=True,
    ).splitlines():
        cleaned = (
            " ".join(
                line.split()
            )
        )

        if cleaned:
            lines.append(
                unescape(
                    cleaned
                )
            )

    return (
        "\n".join(lines),
        title,
    )


def fetch_competitor_page(
    url: str,
    source: CompetitorSource,
) -> dict:
    approved_url = (
        validate_competitor_url(
            url,
            source,
        )
    )

    headers = {
        "User-Agent":
            USER_AGENT,
        "Accept":
            "text/html,application/xhtml+xml",
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

        validate_competitor_url(
            final_url,
            source,
        )

        text, title = (
            clean_html_text(
                response.text
            )
        )

    return {
        "bank_key":
            source.key,
        "bank_name":
            source.name,
        "url":
            final_url,
        "title":
            title,
        "text":
            text,
    }


def normalize_link(
    url: str,
    source: CompetitorSource,
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

        if hostname not in (
            source.allowed_domains
        ):
            return None

        if parsed.scheme not in {
            "http",
            "https",
        }:
            return None

        blocked = (
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".svg",
            ".webp",
            ".css",
            ".js",
            ".zip",
            ".pdf",
            ".mp4",
            ".mp3",
        )

        if (
            parsed.path
            .lower()
            .endswith(
                blocked
            )
        ):
            return None

        return clean_url

    except Exception:
        return None


def discover_competitor_links(
    source: CompetitorSource,
    start_url: str | None = None,
    maximum_links: int = 80,
) -> list[str]:

    root_url = (
        start_url
        or source.base_url
    )

    headers = {
        "User-Agent":
            USER_AGENT,
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

        validate_competitor_url(
            final_url,
            source,
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

    discovered = []
    seen = set()

    for anchor in soup.find_all(
        "a",
        href=True,
    ):
        href = (
            anchor.get("href")
            or ""
        ).strip()

        if not href:
            continue

        absolute = urljoin(
            final_url,
            href,
        )

        approved = normalize_link(
            absolute,
            source,
        )

        if not approved:
            continue

        if approved in seen:
            continue

        seen.add(
            approved
        )

        discovered.append(
            approved
        )

        if (
            len(discovered)
            >= maximum_links
        ):
            break

    

    return discovered