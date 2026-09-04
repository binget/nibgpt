from pathlib import Path

from urllib.parse import (
    quote,
    urljoin,
)

import httpx

from app.core.config import (
    settings,
)


def resolve_document_location(
    filename: str,
) -> dict:

    filename = (
        filename
        or ""
    ).strip()

    if not filename:
        raise ValueError(
            "Document filename is empty."
        )

    # Remove any supplied directory information.
    # DMS filename values should resolve only inside
    # the approved uploads directory.
    safe_filename = (
        Path(filename).name
    )

    # ==================================================
    # Shared/local filesystem
    # ==================================================

    if settings.dms_upload_directory:

        base_directory = (
            Path(
                settings.dms_upload_directory
            )
            .resolve()
        )

        file_path = (
            base_directory
            / safe_filename
        ).resolve()

        if base_directory not in (
            file_path,
            *file_path.parents,
        ):
            raise ValueError(
                "Unsafe DMS document path."
            )

        return {
            "mode": "local",
            "filename": safe_filename,
            "path": str(file_path),
            "url": None,
        }

    # ==================================================
    # DMS HTTP/HTTPS
    # ==================================================

    if settings.dms_base_url:

        encoded_filename = quote(
            safe_filename
        )

        document_url = urljoin(
            settings.dms_base_url.rstrip("/")
            + "/",
            encoded_filename,
        )

        return {
            "mode": "http",
            "filename": safe_filename,
            "path": None,
            "url": document_url,
        }

    raise RuntimeError(
        "No DMS document location is configured."
    )
    
def fetch_document_file(
    filename: str,
) -> str:

    location = resolve_document_location(
        filename
    )

    if location["mode"] == "local":

        file_path = Path(
            location["path"]
        )

        if not file_path.exists():
            raise FileNotFoundError(
                f"Document not found: {file_path}"
            )

        return str(file_path)

    temp_directory = Path(
        "/tmp/nibgpt_documents"
    )

    temp_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = (
        temp_directory
        / location["filename"]
    )

    with httpx.Client(
        timeout=60.0,
        follow_redirects=True,
    ) as client:

        response = client.get(
            location["url"]
        )

        response.raise_for_status()

        content_type = (
            response.headers
            .get("content-type", "")
            .split(";")[0]
            .strip()
            .lower()
        )

        if (
            content_type
            and content_type
            not in {
                "application/pdf",
                "application/octet-stream",
            }
        ):
            raise ValueError(
                "Unexpected DMS content type: "
                f"{content_type}"
            )

        destination.write_bytes(
            response.content
        )

    return str(destination)