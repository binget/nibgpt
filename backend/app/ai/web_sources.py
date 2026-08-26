from dataclasses import (
    dataclass,
)


@dataclass(frozen=True)
class ApprovedWebSource:
    key: str
    name: str
    base_url: str
    allowed_domains: tuple[str, ...]
    source_type: str
    trust_level: str


NIB_PUBLIC_SOURCE = ApprovedWebSource(
    key="nib_public",
    name="NIB International Bank",
    base_url="https://www.nibbanksc.com",
    allowed_domains=(
        "nibbanksc.com",
        "www.nibbanksc.com",
    ),
    source_type="official_bank",
    trust_level="official",
)


APPROVED_WEB_SOURCES = {
    NIB_PUBLIC_SOURCE.key:
        NIB_PUBLIC_SOURCE,
}