"""
Approved internal NIB department profiles.

IMPORTANT:
- These descriptions are maintained internally.
- They are separate from NIB public website data.
- Only approved information should be added here.
"""

DEPARTMENT_PROFILES = {
    "ai and data management": {
        "name": "AI and Data Management",

        "description": (
            "The AI and Data Management Department leads "
            "NIB International Bank's artificial intelligence "
            "and enterprise data management initiatives. "
            "The department supports the bank in using data, "
            "analytics, and AI technologies to improve "
            "decision-making, operational efficiency, "
            "automation, and innovation."
        ),

        "key_functions": [
            "Artificial intelligence and intelligent automation",
            "AI solution development and implementation",
            "Data engineering and data integration",
            "Data governance and data quality",
            "Enterprise analytics and reporting",
            "AI and data platform management",
            "Development of data-driven solutions",
            "AI and data innovation initiatives",
        ],
    },
}


def get_department_profile(
    department_name: str,
) -> dict | None:
    """
    Return an approved department profile using
    normalized department-name matching.
    """

    if not department_name:
        return None

    key = " ".join(
        department_name.lower().split()
    )

    return DEPARTMENT_PROFILES.get(
        key
    )