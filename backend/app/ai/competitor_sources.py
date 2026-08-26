from dataclasses import (
    dataclass,
    field,
)


@dataclass(frozen=True)
class CompetitorSource:
    key: str
    name: str
    base_url: str

    allowed_domains: tuple[
        str,
        ...
    ]

    aliases: tuple[
        str,
        ...
    ] = field(
        default_factory=tuple
    )


COMPETITOR_SOURCES = {
    "cbe": CompetitorSource(
        key="cbe",

        name=(
            "Commercial Bank "
            "of Ethiopia"
        ),

        base_url=(
            "https://combanketh.et/"
        ),

        allowed_domains=(
            "combanketh.et",
            "www.combanketh.et",
        ),

        aliases=(
            "cbe",
            "commercial bank of ethiopia",
            "commercial bank",
        ),
    ),

    "awash": CompetitorSource(
        key="awash",

        name="Awash Bank",

        base_url=(
            "https://awashbank.com/"
        ),

        allowed_domains=(
            "awashbank.com",
            "www.awashbank.com",
        ),

        aliases=(
            "awash",
            "awash bank",
        ),
    ),
}