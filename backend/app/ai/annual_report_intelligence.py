from __future__ import annotations

import os
import re
import tempfile

import httpx
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.ai.document_extractor import (
    extract_document,
)

from app.ai.web_retriever import (
    USER_AGENT,
)

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.data_source import DataSource

from app.models.document_index import (
    DocumentIndex,
)

from app.models.document_chunk import (
    DocumentChunk,
)

from app.ai.document_retriever import (
    chunk_pages,
)

from app.ai.document_cache_service import (
    calculate_file_fingerprint,
    get_cached_chunks,
)


ANNUAL_REPORT_PAGE = (
    "https://www.nibbanksc.com/category/annual-report/"
)

ALLOWED_DOMAINS = {
    "www.nibbanksc.com",
    "nibbanksc.com",
}


# ============================================================
# INTENT
# ============================================================


def detect_annual_report_intent(
    question: str,
) -> bool:

    normalized = (
        " ".join(
            (question or "")
            .lower()
            .strip()
            .split()
        )
    )

    return any(
        phrase in normalized
        for phrase in (
            "annual report",
            "annual reports",
            "yearly report",
            "financial report",
        )
    )


# ============================================================
# YEAR NORMALIZATION
# ============================================================


def normalize_report_year(
    value: str,
) -> str:

    value = (
        value
        .replace("\\", "/")
        .replace("-", "/")
        .strip()
    )

    value = re.sub(
        r"\s+",
        "",
        value,
    )

    return value


def extract_requested_year(
    question: str,
) -> str | None:

    if not question:
        return None

    patterns = (
        r"\b(20\d{2})\s*[/\-]\s*(20\d{2})\b",
        r"\b(20\d{2})\s*[/\-]\s*(\d{2})\b",
        r"\b(20\d{2})\b",
    )

    for pattern in patterns:

        match = re.search(
            pattern,
            question,
        )

        if not match:
            continue

        groups = match.groups()

        if len(groups) == 2:

            first = groups[0]
            second = groups[1]

            if len(second) == 2:
                second = (
                    first[:2]
                    + second
                )

            return (
                f"{first}/{second}"
            )

        return groups[0]

    return None


# ============================================================
# ANNUAL REPORT DISCOVERY
# ============================================================


def discover_annual_reports() -> list[dict]:

    headers = {
        "User-Agent":
            USER_AGENT,

        "Accept":
            (
                "text/html,"
                "application/xhtml+xml"
            ),
    }

    reports = []
    seen_pdfs = set()
    post_urls = []

    with httpx.Client(
        timeout=30.0,
        follow_redirects=True,
        headers=headers,
    ) as client:

        # ----------------------------------------------------
        # 1. Load annual report archive
        # ----------------------------------------------------

        response = client.get(
            ANNUAL_REPORT_PAGE
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        # ----------------------------------------------------
        # 2. Discover annual-report post pages
        # ----------------------------------------------------

        seen_posts = set()

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

            absolute_url = urljoin(
                ANNUAL_REPORT_PAGE,
                href,
            )

            try:

                parsed_url = httpx.URL(
                    absolute_url
                )

                hostname = (
                    parsed_url.host
                    or ""
                ).lower()

            except Exception:
                continue

            if hostname not in ALLOWED_DOMAINS:
                continue

            # PDF directly on archive page.
            if (
                parsed_url.path
                .lower()
                .endswith(".pdf")
            ):

                if absolute_url in seen_pdfs:
                    continue

                seen_pdfs.add(
                    absolute_url
                )

                title = (
                    " ".join(
                        anchor.get_text(
                            " ",
                            strip=True,
                        ).split()
                    )
                )

                reports.append(
                    {
                        "title":
                            title
                            or os.path.basename(
                                parsed_url.path
                            ),

                        "url":
                            absolute_url,

                        "filename":
                            os.path.basename(
                                parsed_url.path
                            ),
                    }
                )

                continue

            # Annual-report post page.
            anchor_text = (
                " ".join(
                    anchor.get_text(
                        " ",
                        strip=True,
                    ).split()
                )
            ).lower()

            url_text = (
                absolute_url.lower()
            )

            if (
                "annual report" not in anchor_text
                and "annual-report" not in url_text
            ):
                continue

            if absolute_url in seen_posts:
                continue

            if (
                absolute_url.rstrip("/")
                == ANNUAL_REPORT_PAGE.rstrip("/")
            ):
                continue

            seen_posts.add(
                absolute_url
            )

            post_urls.append(
                absolute_url
            )

        # ----------------------------------------------------
        # 3. Open each post and find its PDF links
        # ----------------------------------------------------

        for post_url in post_urls:

            try:

                post_response = client.get(
                    post_url
                )

                post_response.raise_for_status()

            except Exception as error:

                print(
                    "DEBUG ANNUAL REPORT POST ERROR:",
                    post_url,
                    type(error).__name__,
                    str(error),
                    flush=True,
                )

                continue

            post_soup = BeautifulSoup(
                post_response.text,
                "html.parser",
            )

            for anchor in post_soup.find_all(
                "a",
                href=True,
            ):

                href = (
                    anchor.get("href")
                    or ""
                ).strip()

                if not href:
                    continue

                pdf_url = urljoin(
                    post_url,
                    href,
                )

                try:

                    parsed_pdf = httpx.URL(
                        pdf_url
                    )

                    hostname = (
                        parsed_pdf.host
                        or ""
                    ).lower()

                except Exception:
                    continue

                if hostname not in ALLOWED_DOMAINS:
                    continue

                if not (
                    parsed_pdf.path
                    .lower()
                    .endswith(".pdf")
                ):
                    continue

                if pdf_url in seen_pdfs:
                    continue

                seen_pdfs.add(
                    pdf_url
                )

                title = (
                    " ".join(
                        anchor.get_text(
                            " ",
                            strip=True,
                        ).split()
                    )
                )

                filename = os.path.basename(
                    parsed_pdf.path
                )
                
                annual_report_identity = (
                    (
                        title
                        + " "
                        + filename
                    )
                    .lower()
                )

                is_annual_report = (
                    "annual report" in annual_report_identity
                    or "annual-report" in annual_report_identity
                    or " ar fy " in f" {annual_report_identity} "
                )

                if not is_annual_report:
                    continue

                reports.append(
                    {
                        "title":
                            title
                            or filename,

                        "url":
                            pdf_url,

                        "filename":
                            filename,

                        "post_url":
                            post_url,
                    }
                )

    return reports


# ============================================================
# REPORT SELECTION
# ============================================================


def select_annual_report(
    question: str,
    reports: list[dict],
) -> dict | None:

    if not reports:
        return None

    requested_year = (
        extract_requested_year(
            question
        )
    )

    if not requested_year:

        # Temporary behavior.
        # Later this will be replaced with
        # explicit latest-report selection.
        return reports[0]

    requested_normalized = (
        normalize_report_year(
            requested_year
        )
    )

    first_year = (
        requested_normalized
        .split("/")[0]
    )

    second_year = None

    if "/" in requested_normalized:
        second_year = (
            requested_normalized
            .split("/")[1]
        )

    best_report = None
    best_score = 0

    for report in reports:

        haystack = (
            (
                report.get("title", "")
                + " "
                + report.get("filename", "")
                + " "
                + report.get("url", "")
            )
            .lower()
            .replace("-", "/")
        )

        score = 0

        if requested_normalized in haystack:
            score += 100

        if first_year in haystack:
            score += 40

        if (
            second_year
            and second_year in haystack
        ):
            score += 40

        if (
            second_year
            and second_year[-2:]
            in haystack
        ):
            score += 20

        if score > best_score:

            best_score = score
            best_report = report

    if best_score <= 0:
        return None

    return best_report


# ============================================================
# DOWNLOAD REPORT
# ============================================================


def download_annual_report(
    report: dict,
) -> str:

    url = report["url"]

    headers = {
        "User-Agent":
            USER_AGENT,

        "Accept":
            "application/pdf,*/*",
    }

    response = httpx.get(
        url,
        timeout=60.0,
        follow_redirects=True,
        headers=headers,
    )

    response.raise_for_status()

    suffix = ".pdf"

    handle = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
    )

    try:

        handle.write(
            response.content
        )

        handle.flush()

        return handle.name

    finally:

        handle.close()


# ============================================================
# TEST EXTRACTION
# ============================================================


def extract_annual_report(
    question: str,
) -> dict:

    reports = (
        discover_annual_reports()
    )

    report = (
        select_annual_report(
            question=question,
            reports=reports,
        )
    )

    if not report:

        return {
            "success": False,
            "error":
                "No matching NIB annual report was found.",
        }

    file_path = (
        download_annual_report(
            report
        )
    )

    try:

        pages = (
            extract_document(
                file_path
            )
        )

        return {
            "success": True,
            "report": report,
            "page_count":
                len(pages),
            "pages":
                pages,
        }

    finally:

        try:
            os.unlink(
                file_path
            )

        except Exception:
            pass
        
# ============================================================
# ANNUAL REPORT CACHE
# ============================================================


ANNUAL_REPORT_SOURCE_CODE = (
    "NIB_ANNUAL_REPORTS"
)


def get_annual_report_data_source_id(
    database: Session,
) -> int:

    source = (
        database.query(
            DataSource
        )
        .filter(
            DataSource.code
            == ANNUAL_REPORT_SOURCE_CODE
        )
        .first()
    )

    if source is None:
        raise ValueError(
            "NIB Annual Reports data source "
            "is not configured."
        )

    if not source.is_active:
        raise ValueError(
            "NIB Annual Reports data source "
            "is inactive."
        )

    return int(source.id)


def get_annual_report_external_id(
    report: dict,
) -> int:
    """
    Convert the financial year into a stable integer.

    Example:
        2024/2025 -> 20242025
        2023/2024 -> 20232024
    """

    identity = (
        (
            report.get("title", "")
            + " "
            + report.get("filename", "")
        )
    )

    years = re.findall(
        r"\b(20\d{2})\b",
        identity,
    )

    unique_years = []

    for year in years:

        if year not in unique_years:
            unique_years.append(
                year
            )

    if len(unique_years) < 2:
        raise ValueError(
            "Could not determine the annual "
            "report financial year."
        )

    first_year = unique_years[0]
    second_year = unique_years[1]

    return int(
        first_year
        + second_year
    )


def get_cached_annual_report(
    database: Session,
    report: dict,
) -> DocumentIndex | None:

    data_source_id = (
        get_annual_report_data_source_id(
            database
        )
    )

    external_document_id = (
        get_annual_report_external_id(
            report
        )
    )

    return (
        database.query(
            DocumentIndex
        )
        .filter(
            DocumentIndex.data_source_id
            == data_source_id,

            DocumentIndex.external_document_id
            == external_document_id,
        )
        .first()
    )


def index_annual_report(
    database: Session,
    report: dict,
    force: bool = False,
) -> dict:

    data_source_id = (
        get_annual_report_data_source_id(
            database
        )
    )

    external_document_id = (
        get_annual_report_external_id(
            report
        )
    )

    filename = (
        report.get("filename")
        or ""
    ).strip()

    title = (
        report.get("title")
        or filename
    ).strip()

    if not filename:
        raise ValueError(
            "Annual report does not have "
            "a filename."
        )

    # --------------------------------------------------------
    # 1. Check existing PostgreSQL cache first.
    #
    # Annual reports are treated as published immutable
    # documents. Therefore a ready cache is reused without
    # downloading the PDF again.
    # --------------------------------------------------------

    cached_document = (
        get_cached_annual_report(
            database=database,
            report=report,
        )
    )

    if (
        cached_document
        and not force
        and cached_document.status == "ready"
    ):

        cached_chunks = (
            get_cached_chunks(
                database=database,
                document_index_id=(
                    cached_document.id
                ),
            )
        )

        if cached_chunks:

            return {
                "status":
                    "cached",

                "document_index_id":
                    cached_document.id,

                "external_document_id":
                    external_document_id,

                "filename":
                    cached_document.filename,

                "title":
                    cached_document.title,

                "page_count":
                    cached_document.page_count,

                "chunk_count":
                    len(cached_chunks),

                "fingerprint":
                    cached_document.file_fingerprint,

                "chunks":
                    cached_chunks,
            }

    # --------------------------------------------------------
    # 2. Download official NIB PDF.
    # --------------------------------------------------------

    file_path = (
        download_annual_report(
            report
        )
    )

    try:

        fingerprint = (
            calculate_file_fingerprint(
                file_path
            )
        )

        # ----------------------------------------------------
        # 3. If force=True but physical file did not change,
        #    reuse the existing cache.
        # ----------------------------------------------------

        if (
            cached_document
            and cached_document.status == "ready"
            and cached_document.file_fingerprint
            == fingerprint
        ):

            cached_chunks = (
                get_cached_chunks(
                    database=database,
                    document_index_id=(
                        cached_document.id
                    ),
                )
            )

            if cached_chunks:

                return {
                    "status":
                        "cached",

                    "document_index_id":
                        cached_document.id,

                    "external_document_id":
                        external_document_id,

                    "filename":
                        cached_document.filename,

                    "title":
                        cached_document.title,

                    "page_count":
                        cached_document.page_count,

                    "chunk_count":
                        len(cached_chunks),

                    "fingerprint":
                        fingerprint,

                    "chunks":
                        cached_chunks,
                }

        # ----------------------------------------------------
        # 4. Create/update document_index.
        # ----------------------------------------------------

        if cached_document is None:

            cached_document = DocumentIndex(
                data_source_id=(
                    data_source_id
                ),
                external_document_id=(
                    external_document_id
                ),
                filename=filename,
                title=title,
                department=None,
                status="processing",
            )

            database.add(
                cached_document
            )

            database.flush()

        else:

            cached_document.filename = (
                filename
            )

            cached_document.title = (
                title
            )

            cached_document.status = (
                "processing"
            )

            cached_document.error_message = (
                None
            )

            # Remove old chunks before re-indexing.
            (
                database.query(
                    DocumentChunk
                )
                .filter(
                    DocumentChunk.document_index_id
                    == cached_document.id
                )
                .delete(
                    synchronize_session=False
                )
            )

            database.flush()

        # ----------------------------------------------------
        # 5. Extract PDF.
        # ----------------------------------------------------

        pages = (
            extract_document(
                file_path
            )
        )

        # ----------------------------------------------------
        # 6. Parse/chunk using the existing NIBGPT
        #    document parser.
        # ----------------------------------------------------

        chunks = (
            chunk_pages(
                pages=pages,
                chunk_size=3500,
                overlap=0,
            )
        )

        if not chunks:
            raise ValueError(
                "Annual report extraction produced "
                "no searchable chunks."
            )

        # ----------------------------------------------------
        # 7. Store chunks.
        # ----------------------------------------------------

        for index, chunk in enumerate(
            chunks,
            start=1,
        ):

            content = (
                chunk.get("content")
                or ""
            ).strip()

            if not content:
                continue

            record = DocumentChunk(
                document_index_id=(
                    cached_document.id
                ),

                page_number=(
                    chunk.get(
                        "page_number"
                    )
                ),

                start_page=(
                    chunk.get(
                        "start_page"
                    )
                ),

                end_page=(
                    chunk.get(
                        "end_page"
                    )
                ),

                section_number=(
                    chunk.get(
                        "section_number"
                    )
                ),

                section_title=(
                    chunk.get(
                        "section_title"
                    )
                ),

                parent_section_number=(
                    chunk.get(
                        "parent_section_number"
                    )
                ),

                parent_section_title=(
                    chunk.get(
                        "parent_section_title"
                    )
                ),

                content=content,

                extraction_method=(
                    chunk.get(
                        "extraction_method"
                    )
                ),

                chunk_order=index,
            )

            database.add(
                record
            )

        # ----------------------------------------------------
        # 8. Finalize index.
        # ----------------------------------------------------

        cached_document.file_fingerprint = (
            fingerprint
        )

        cached_document.status = (
            "ready"
        )

        cached_document.page_count = (
            len(pages)
        )

        cached_document.indexed_at = (
            datetime.now(
                timezone.utc
            )
        )

        cached_document.error_message = (
            None
        )

        database.commit()

        stored_chunks = (
            get_cached_chunks(
                database=database,
                document_index_id=(
                    cached_document.id
                ),
            )
        )

        return {
            "status":
                "indexed",

            "document_index_id":
                cached_document.id,

            "external_document_id":
                external_document_id,

            "filename":
                filename,

            "title":
                title,

            "page_count":
                len(pages),

            "chunk_count":
                len(stored_chunks),

            "fingerprint":
                fingerprint,

            "chunks":
                stored_chunks,
        }

    except Exception as error:

        database.rollback()

        raise

    finally:

        try:

            os.unlink(
                file_path
            )

        except Exception:
            pass


def load_cached_annual_report_chunks(
    database: Session,
    report: dict,
) -> list[dict]:

    cached_document = (
        get_cached_annual_report(
            database=database,
            report=report,
        )
    )

    if (
        cached_document is None
        or cached_document.status
        != "ready"
    ):
        return []

    return get_cached_chunks(
        database=database,
        document_index_id=(
            cached_document.id
        ),
    )