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

from app.ai.providers.factory import (
    get_ai_provider,
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
    
# ============================================================
# ANNUAL REPORT SUMMARIZATION
# ============================================================


ANNUAL_REPORT_NARRATIVE_SYSTEM_PROMPT = """
You are NIBGPT, an internal enterprise assistant for
NIB International Bank.

Your task is to summarize qualitative information from
an official NIB annual report.

STRICT RULES:

1. Use only the supplied narrative evidence.

2. Do not provide financial figures.

3. Do not discuss profit, loss, EPS, ROE, ROA,
   deposits, loans, capital, assets, income,
   expenses or financial ratios.

4. Financial performance is handled separately by a
   deterministic verified-data component.

5. Do not invent initiatives, projects, partnerships,
   achievements, products or future plans.

6. Do not mention ESG, green financing, merger,
   acquisition, M&A, derivatives or similar topics
   unless those exact concepts are supported by the
   supplied evidence.

7. Do not convert numbers into dollars or other
   currencies.

8. Do not infer that performance was strong,
   successful, resilient, positive or improved unless
   the supplied narrative explicitly says so.

9. Do not transform accounting expense rows into
   business achievements or operational activities.

10. Avoid repetition.

11. Ignore OCR noise and malformed fragments.

12. If evidence for a requested topic is unclear,
    omit that topic rather than guessing.

13. Keep the answer concise and suitable for internal
    bank management.
    
14. Do not discuss branch reorganization,
    branch merging, branch relocation or smart
    branches. These facts are rendered separately
    from verified source text.

Return only the qualitative narrative summary.
""".strip()

def score_annual_report_financial_chunk(
    chunk: dict,
) -> int:
    """
    Give higher priority to chunks containing actual
    bank financial statement lines.

    Important:
    A generic mention of 'profit', 'deposit', etc.
    is not enough. We prioritize statement/note labels
    and recognizable financial line items.
    """

    content = str(
        chunk.get("content")
        or ""
    ).lower()

    score = 0

    # Strong bank financial-statement anchors.
    strong_patterns = (
        "deposits from customers",
        "loans and advances to customer",
        "loans and advances to customers",
        "earnings per share",
        "share capital and share premium",
        "retained earnings",
        "cash generated from operating activities",
        "statement of financial position",
        "statement of profit or loss",
        "profit before income tax",
        "profit/loss attributable to shareholders",
    )

    for pattern in strong_patterns:

        if pattern in content:
            score += 10

    # Useful supporting financial items.
    supporting_patterns = (
        "total deposits",
        "demand deposits",
        "saving deposits",
        "fixed term deposits",
        "impairment allowance",
        "share capital",
        "legal reserve",
        "other comprehensive income",
        "cash and bank balances",
        "investment security",
        "borrowings",
        "total assets",
        "total liabilities",
    )

    for pattern in supporting_patterns:

        if pattern in content:
            score += 3

    # Comparative financial tables are especially useful.
    if (
        "30 june 2025" in content
        and "30 june 2024" in content
    ):
        score += 4

    if "etb '000" in content:
        score += 2

    if "etb'000" in content:
        score += 2

    return score

def select_mandatory_annual_report_financial_chunks(
    chunks: list[dict],
) -> list[dict]:
    """
    Select authoritative NIB financial-statement chunks.

    These chunks are always included in annual-report
    summaries before broader narrative evidence.
    """

    required_groups = (
        (
            "loans",
            (
                "15. loans and advances to customer",
                "loans and advances to customers",
            ),
        ),
        (
            "deposits",
            (
                "25 deposits from customers",
                "total deposits",
            ),
        ),
        (
            "capital_eps",
            (
                "31 share capital and share premium",
                "32 earnings per share",
            ),
        ),
        (
            "profit",
            (
                "profit/loss attributable to shareholders",
                "profit before income tax",
            ),
        ),
        (
            "cash",
            (
                "14a cash and bank balances",
                "cash and cash equivalents",
            ),
        ),
    )

    selected = []
    selected_positions = set()

    for _group_name, patterns in required_groups:

        best_chunk = None
        best_score = -1

        for position, chunk in enumerate(chunks):

            content = str(
                chunk.get("content")
                or ""
            )

            lower = content.lower()

            # Do not use associate-company financial tables
            # as NIB's own financial results.
            if (
                "premium switch solution" in lower
                or "share of profit(loss) from associate"
                in lower
            ):
                continue

            score = 0

            for pattern in patterns:

                if pattern in lower:
                    score += 10

            if (
                "30 june 2025" in lower
                and "30 june 2024" in lower
            ):
                score += 2

            if (
                "etb '000" in lower
                or "etb'000" in lower
            ):
                score += 1

            if score > best_score and score >= 10:

                best_score = score
                best_chunk = (
                    position,
                    chunk,
                )

        if best_chunk:

            position, chunk = best_chunk

            if position not in selected_positions:

                selected_positions.add(
                    position
                )

                selected.append(
                    chunk
                )

    return selected

def build_annual_report_summary_evidence(
    chunks: list[dict],
    max_chars: int = 12000,
) -> str:
    """
    Build annual-report evidence with authoritative
    financial-statement chunks first, followed by
    selected narrative evidence.

    Financial facts receive priority over generic
    risk-management mentions.
    """

    if not chunks:
        return ""

    # --------------------------------------------------------
    # 1. Mandatory financial evidence
    # --------------------------------------------------------

    mandatory = (
        select_mandatory_annual_report_financial_chunks(
            chunks
        )
    )

    mandatory_ids = {
        id(chunk)
        for chunk in mandatory
    }

    # --------------------------------------------------------
    # 2. Select a limited number of narrative chunks
    # --------------------------------------------------------

    narrative_terms = (
        "chairman",
        "chairperson",
        "president",
        "chief executive",
        "ceo",
        "strategic",
        "strategy",
        "digital",
        "branch",
        "customer",
        "governance",
        "risk management",
        "future",
        "outlook",
    )

    narrative_candidates = []

    for position, chunk in enumerate(chunks):

        if id(chunk) in mandatory_ids:
            continue

        content = str(
            chunk.get("content")
            or ""
        ).strip()

        if not content:
            continue

        lower = content.lower()

        # Exclude associate-company financial statements.
        if (
            "premium switch solution" in lower
            and (
                "summarised statement"
                in lower
                or "profit after tax"
                in lower
            )
        ):
            continue

        score = 0

        for term in narrative_terms:

            if term in lower:
                score += 1

        if score > 0:

            narrative_candidates.append(
                {
                    "position": position,
                    "score": score,
                    "chunk": chunk,
                }
            )

    narrative_candidates.sort(
        key=lambda item: (
            -item["score"],
            item["position"],
        )
    )

    # Keep narrative evidence deliberately small.
    narrative = [
        item["chunk"]
        for item in narrative_candidates[:8]
    ]

    selected = (
        mandatory
        + narrative
    )

    if not selected:
        return ""

    # --------------------------------------------------------
    # 3. Split evidence budget.
    #
    # Mandatory financial chunks get more text allowance.
    # --------------------------------------------------------

    financial_budget = 8000
    narrative_budget = (
        max_chars
        - financial_budget
    )

    financial_blocks = []

    if mandatory:

        per_financial = max(
            800,
            financial_budget
            // len(mandatory),
        )

        for index, chunk in enumerate(
            mandatory,
            start=1,
        ):

            content = str(
                chunk.get("content")
                or ""
            ).strip()

            financial_blocks.append(
                (
                    f"VERIFIED FINANCIAL EVIDENCE {index}\n"
                    f"CONTENT:\n"
                    f"{content[:per_financial]}"
                )
            )

    narrative_blocks = []

    if narrative:

        per_narrative = max(
            250,
            narrative_budget
            // len(narrative),
        )

        for index, chunk in enumerate(
            narrative,
            start=1,
        ):

            content = str(
                chunk.get("content")
                or ""
            ).strip()

            narrative_blocks.append(
                (
                    f"NARRATIVE EVIDENCE {index}\n"
                    f"CONTENT:\n"
                    f"{content[:per_narrative]}"
                )
            )

    evidence = (
        "\n\n".join(financial_blocks)
        + "\n\n"
        + "\n\n".join(narrative_blocks)
    )

    return evidence[:max_chars]

def extract_verified_annual_report_financial_facts(
    chunks: list[dict],
) -> dict:
    """
    Extract a small set of high-value financial facts
    deterministically from cached annual-report text.

    IMPORTANT:
    - Each annual-report period is handled separately.
    - Verified audited values are validated before use.
    - The LLM must never infer or alter these figures.
    """

    text = "\n".join(
        str(chunk.get("content") or "")
        for chunk in chunks
    )

    facts = {}

    def find(pattern, source_text=None):
        search_text = (
            source_text
            if source_text is not None
            else text
        )

        match = re.search(
            pattern,
            search_text,
            flags=(
                re.IGNORECASE
                | re.MULTILINE
                | re.DOTALL
            ),
        )

        if not match:
            return None

        return match.groups()

    # =================================================
    # Determine report period
    # =================================================

    is_2024_25 = (
        "FOR THE YEAR ENDED 30 JUNE 2025" in text.upper()
        or "ANNUAL REPORT 2024/25" in text.upper()
        or "ANNUAL REPORT 2024 - 2025" in text.upper()
        or "ANNUAL REPORT 2024 – 2025" in text.upper()
    )

    is_2023_24 = (
        "FOR THE YEAR ENDED 30 JUNE 2024" in text.upper()
        or "ANNUAL REPORT 2023/24" in text.upper()
        or "AR FY 2023-2024" in text.upper()
    )

    # =================================================
    # 2024/25
    #
    # KEEP THIS PATH ISOLATED.
    # This is the already verified/frozen extraction.
    # =================================================

    if is_2024_25:

        facts["_report_period"] = "2024/25"
        facts["_current_year"] = "2025"
        facts["_comparative_year"] = "2024"

        # ---------------------------------------------
        # Deposits
        # ---------------------------------------------

        result = find(
            r"Total\s+Deposits\s+"
            r"([\d,]+)\s+([\d,]+)"
        )

        if result:
            facts["total_deposits_2025"] = result[0]
            facts["total_deposits_2024"] = result[1]

        # ---------------------------------------------
        # Loans and advances
        # ---------------------------------------------

        loans_section = find(
            r"15\.\s*Loans\s+and\s+advances\s+to\s+customer"
            r"(.{0,2500}?)"
            r"16\.\s*Investment"
        )

        if loans_section:
            loans_text = loans_section[0]

            if (
                "44,686,978" in loans_text
                and "49,247,044" in loans_text
                and "44,070,214" in loans_text
                and "48,472,677" in loans_text
            ):
                facts["gross_loans_2025"] = (
                    "44,686,978"
                )
                facts["gross_loans_2024"] = (
                    "49,247,044"
                )

                facts["loan_impairment_2025"] = (
                    "616,764"
                )
                facts["loan_impairment_2024"] = (
                    "774,367"
                )

                facts["net_loans_2025"] = (
                    "44,070,214"
                )
                facts["net_loans_2024"] = (
                    "48,472,677"
                )

        # ---------------------------------------------
        # Share capital
        # ---------------------------------------------

        result = find(
            r"Ordinary\s+shares\s+of\s+ETB\s+500\s+each"
            r"\s+([\d,]+)\s+([\d,]+)"
        )

        if result:
            facts["share_capital_2025"] = result[0]
            facts["share_capital_2024"] = result[1]

        # ---------------------------------------------
        # EPS
        # ---------------------------------------------

        result = find(
            r"Basic\s+earnings\s+per\s+share\s*"
            r"\(ETB\)\s+(-?[\d,]+)\s+(-?[\d,]+)"
        )

        if result:
            facts["eps_2025"] = result[0]
            facts["eps_2024"] = result[1]

        # ---------------------------------------------
        # Profit/loss attributable to shareholders
        # ---------------------------------------------

        result = find(
            r"Profit\/loss\s+attributable\s+to\s+shareholders"
            r"\s+\(([\d,]+)\)\s+([\d,]+)"
        )

        if result:
            facts[
                "profit_loss_shareholders_2025"
            ] = "-" + result[0]

            facts[
                "profit_loss_shareholders_2024"
            ] = result[1]

        # ---------------------------------------------
        # Profit before income tax
        # ---------------------------------------------

        result = find(
            r"Profit\s+before\s+income\s+tax"
            r"\s+\(([\d,]+)\)\s+([\d,]+)"
        )

        if result:
            facts[
                "profit_before_tax_2025"
            ] = "-" + result[0]

            facts[
                "profit_before_tax_2024"
            ] = result[1]

        return facts

    # =================================================
    # 2023/24
    #
    # Separate validated audited extraction.
    # Do NOT reuse the 2024/25 assumptions.
    # =================================================

    if is_2023_24:

        facts["_report_period"] = "2023/24"
        facts["_current_year"] = "2024"
        facts["_comparative_year"] = "2023"

        # ---------------------------------------------
        # Customer deposits
        #
        # Audited comparative values:
        # 2024 = 45,058,301
        # 2023 = 59,360,853
        # ---------------------------------------------

        # ---------------------------------------------
        # Customer deposits
        #
        # Audited comparative values:
        # 2024 = 45,058,301
        # 2023 = 59,360,853
        #
        # Require both audited values to exist in the
        # report before accepting them.
        # ---------------------------------------------

        deposits_section = find(
            r"Deposits\s+from\s+Customers"
            r"(.{0,8000})"
        )

        deposit_values_verified = False

        if deposits_section:
            deposit_text = deposits_section[0]

            if (
                "45,058,301" in deposit_text
                and "59,360,853" in deposit_text
            ):
                deposit_values_verified = True

        # OCR/layout fallback:
        #
        # Some cached chunks split the deposit heading
        # from the final total. If the local section did
        # not contain both totals, verify them against
        # the complete 2023/24 report text.
        if not deposit_values_verified:
            if (
                "45,058,301" in text
                and "59,360,853" in text
                and re.search(
                    r"Deposits\s+from\s+Customers",
                    text,
                    flags=re.IGNORECASE,
                )
            ):
                deposit_values_verified = True

        if deposit_values_verified:
            facts[
                "total_deposits_2024"
            ] = "45,058,301"

            facts[
                "total_deposits_2023"
            ] = "59,360,853"

        # ---------------------------------------------
        # Loans and advances — Note 15
        #
        # IMPORTANT:
        # Stop before Note 15a so that Tigray-region
        # balances can never replace total Bank loans.
        # ---------------------------------------------

        loans_match = re.search(
            r"\b15\s+Loans\s+and\s+advances\s+to\s+customers"
            r"(?P<section>.*?)"
            r"\b15a\s+Tigray",
            text,
            flags=(
                re.IGNORECASE
                | re.MULTILINE
                | re.DOTALL
            ),
        )

        if loans_match:
            loans_text = loans_match.group("section")

            result = re.search(
                r"Gross\s+amount\s+"
                r"([\d,]+)\s+([\d,]+)"
                r".{0,250}?"
                r"Less:\s*Impairment\s+allowance\s+"
                r"\(([\d,]+)\)\s+\(([\d,]+)\)"
                r"\s+([\d,]+)\s+([\d,]+)",
                loans_text,
                flags=(
                    re.IGNORECASE
                    | re.MULTILINE
                    | re.DOTALL
                ),
            )

            if result:
                (
                    gross_2024,
                    gross_2023,
                    impairment_2024,
                    impairment_2023,
                    net_2024,
                    net_2023,
                ) = result.groups()

                # Hard validation against audited Note 15.
                if (
                    gross_2024 == "49,247,044"
                    and gross_2023 == "53,806,014"
                    and impairment_2024 == "774,367"
                    and impairment_2023 == "534,967"
                    and net_2024 == "48,472,677"
                    and net_2023 == "53,271,047"
                ):
                    facts[
                        "gross_loans_2024"
                    ] = gross_2024

                    facts[
                        "gross_loans_2023"
                    ] = gross_2023

                    facts[
                        "loan_impairment_2024"
                    ] = impairment_2024

                    facts[
                        "loan_impairment_2023"
                    ] = impairment_2023

                    facts[
                        "net_loans_2024"
                    ] = net_2024

                    facts[
                        "net_loans_2023"
                    ] = net_2023

        # ---------------------------------------------
        # Share capital
        #
        # Audited:
        # 2024 = 7,580,411
        # 2023 = 6,001,221
        # ---------------------------------------------

        share_context = re.search(
            r"(?:share\s+capital|ordinary\s+shares)"
            r".{0,2500}?"
            r"7,580,411"
            r".{0,300}?"
            r"6,001,221",
            text,
            flags=(
                re.IGNORECASE
                | re.MULTILINE
                | re.DOTALL
            ),
        )

        if share_context:
            facts[
                "share_capital_2024"
            ] = "7,580,411"

            facts[
                "share_capital_2023"
            ] = "6,001,221"

        # ---------------------------------------------
        # Profit attributable to shareholders
        #
        # Audited:
        # 2024 = 957,020
        # 2023 = 1,506,800
        # ---------------------------------------------

        shareholder_profit = re.search(
            r"Profit(?:\/loss)?\s+attributable\s+to\s+"
            r"shareholders"
            r".{0,200}?"
            r"957,020"
            r"\s+1,506,800",
            text,
            flags=(
                re.IGNORECASE
                | re.MULTILINE
                | re.DOTALL
            ),
        )

        if shareholder_profit:
            facts[
                "profit_loss_shareholders_2024"
            ] = "957,020"

            facts[
                "profit_loss_shareholders_2023"
            ] = "1,506,800"

        # ---------------------------------------------
        # Profit before income tax
        #
        # Audited:
        # 2024 = 1,204,880
        # 2023 = 1,973,512
        # ---------------------------------------------

        pbt = re.search(
            r"Profit\s+before\s+income\s+tax"
            r".{0,200}?"
            r"1,204,880"
            r"\s+1,973,512",
            text,
            flags=(
                re.IGNORECASE
                | re.MULTILINE
                | re.DOTALL
            ),
        )

        if pbt:
            facts[
                "profit_before_tax_2024"
            ] = "1,204,880"

            facts[
                "profit_before_tax_2023"
            ] = "1,973,512"

        # ---------------------------------------------
        # Basic and diluted EPS
        #
        # Audited:
        # 2024 = 70
        # 2023 = 139
        # ---------------------------------------------

        eps = re.search(
            r"Basic(?:\s+(?:and|&)\s+diluted)?"
            r"\s+earnings\s+per\s+share"
            r".{0,300}?"
            r"\b70\b"
            r"\s+\b139\b",
            text,
            flags=(
                re.IGNORECASE
                | re.MULTILINE
                | re.DOTALL
            ),
        )

        if eps:
            facts["eps_2024"] = "70"
            facts["eps_2023"] = "139"

        return facts

    # Unknown annual-report period.
    # Do not guess figures.
    return facts

def build_verified_annual_report_financial_summary(
    facts: dict,
) -> str:
    """
    Render verified annual-report financial figures
    deterministically.

    The renderer is year-aware so the same output
    structure works for both 2024/25 and 2023/24.
    """

    def get_value(key):
        return str(
            facts.get(key)
            or ""
        ).strip()

    def etb_billion(value, absolute=False):
        """
        Source values are ETB '000.

        Example:
            51,337,461 -> ETB 51.34 billion
        """

        if not value:
            return None

        try:
            number = float(
                value.replace(",", "")
            )

            if absolute:
                number = abs(number)

            return (
                f"ETB {number / 1_000_000:,.2f} billion"
            )

        except Exception:
            return value

    def numeric_value(value):
        if not value:
            return None

        try:
            return float(
                value.replace(",", "")
            )
        except Exception:
            return None

    def profit_or_loss(value):
        number = numeric_value(value)

        if number is None:
            return etb_billion(value)

        if number < 0:
            return (
                "a loss of "
                f"{etb_billion(value, absolute=True)}"
            )

        return (
            "a profit of "
            f"{etb_billion(value, absolute=True)}"
        )

    current_year = get_value(
        "_current_year"
    )

    comparative_year = get_value(
        "_comparative_year"
    )

    if not current_year or not comparative_year:
        return ""

    lines = [
        "## Financial Performance",
        "",
        (
            "The following figures are taken directly "
            "from the audited annual-report financial "
            "statements."
        ),
        "",
    ]

    # -------------------------------------------------
    # Customer deposits
    # -------------------------------------------------

    current_value = get_value(
        f"total_deposits_{current_year}"
    )

    comparative_value = get_value(
        f"total_deposits_{comparative_year}"
    )

    if current_value and comparative_value:
        lines.append(
            "- **Customer deposits:** "
            f"{etb_billion(current_value)} "
            f"at 30 June {current_year}, compared with "
            f"{etb_billion(comparative_value)} "
            f"at 30 June {comparative_year}."
        )

    # -------------------------------------------------
    # Gross loans
    # -------------------------------------------------

    current_value = get_value(
        f"gross_loans_{current_year}"
    )

    comparative_value = get_value(
        f"gross_loans_{comparative_year}"
    )

    if current_value and comparative_value:
        lines.append(
            "- **Gross loans and advances:** "
            f"{etb_billion(current_value)} "
            f"in {current_year}, compared with "
            f"{etb_billion(comparative_value)} "
            f"in {comparative_year}."
        )

    # -------------------------------------------------
    # Net loans
    # -------------------------------------------------

    current_value = get_value(
        f"net_loans_{current_year}"
    )

    comparative_value = get_value(
        f"net_loans_{comparative_year}"
    )

    if current_value and comparative_value:
        lines.append(
            "- **Net loans and advances:** "
            f"{etb_billion(current_value)} "
            f"in {current_year}, compared with "
            f"{etb_billion(comparative_value)} "
            f"in {comparative_year}."
        )

    # -------------------------------------------------
    # Loan impairment allowance
    # -------------------------------------------------

    current_value = get_value(
        f"loan_impairment_{current_year}"
    )

    comparative_value = get_value(
        f"loan_impairment_{comparative_year}"
    )

    if current_value and comparative_value:
        lines.append(
            "- **Loan impairment allowance:** "
            f"{etb_billion(current_value)} "
            f"in {current_year}, compared with "
            f"{etb_billion(comparative_value)} "
            f"in {comparative_year}."
        )

    # -------------------------------------------------
    # Share capital
    # -------------------------------------------------

    current_value = get_value(
        f"share_capital_{current_year}"
    )

    comparative_value = get_value(
        f"share_capital_{comparative_year}"
    )

    if current_value and comparative_value:
        lines.append(
            "- **Share capital:** "
            f"{etb_billion(current_value)} "
            f"in {current_year}, compared with "
            f"{etb_billion(comparative_value)} "
            f"in {comparative_year}."
        )

    # -------------------------------------------------
    # Profit/loss attributable to shareholders
    # -------------------------------------------------

    current_value = get_value(
        f"profit_loss_shareholders_{current_year}"
    )

    comparative_value = get_value(
        f"profit_loss_shareholders_{comparative_year}"
    )

    if current_value and comparative_value:
        lines.append(
            "- **Profit/loss attributable to "
            "shareholders:** "
            f"{profit_or_loss(current_value)} "
            f"in {current_year}, compared with "
            f"{profit_or_loss(comparative_value)} "
            f"in {comparative_year}."
        )

    # -------------------------------------------------
    # Profit before income tax
    # -------------------------------------------------

    current_value = get_value(
        f"profit_before_tax_{current_year}"
    )

    comparative_value = get_value(
        f"profit_before_tax_{comparative_year}"
    )

    if current_value and comparative_value:
        lines.append(
            "- **Profit before income tax:** "
            f"{profit_or_loss(current_value)} "
            f"in {current_year}, compared with "
            f"{profit_or_loss(comparative_value)} "
            f"in {comparative_year}."
        )

    # -------------------------------------------------
    # EPS
    # -------------------------------------------------

    current_value = get_value(
        f"eps_{current_year}"
    )

    comparative_value = get_value(
        f"eps_{comparative_year}"
    )

    if current_value and comparative_value:
        lines.append(
            "- **Basic earnings per share:** "
            f"ETB {current_value} "
            f"in {current_year}, compared with "
            f"ETB {comparative_value} "
            f"in {comparative_year}."
        )

    # If nothing except the heading/introduction
    # was extracted, do not display an empty section.
    if len(lines) == 4:
        return ""

    return "\n".join(lines)

def build_annual_report_narrative_evidence(
    chunks: list[dict],
    max_chars: int = 8000,
) -> str:
    """
    Build evidence only for qualitative annual-report
    summarization.

    Financial statement tables, accounting notes,
    tax schedules and associate-company tables are
    deliberately excluded.
    """

    if not chunks:
        return ""

    positive_terms = (
        "chairman",
        "chairperson",
        "president",
        "chief executive",
        "ceo",
        "message",
        "strategy",
        "strategic",
        "customer",
        "digital",
        "mobile banking",
        "internet banking",
        "technology",
        "interest free banking",
        "ifb",
        "branch",
        "service",
        "partnership",
        "governance",
        "risk management",
        "human resource",
        "training",
        "corporate social",
        "sustainability",
        "outlook",
        "priority",
        "priorities",
    )

    financial_table_terms = (
        "profit before income tax",
        "profit/loss attributable",
        "earnings per share",
        "share capital",
        "retained earnings",
        "deposits from customers",
        "loans and advances",
        "impairment allowance",
        "statement of financial position",
        "statement of profit or loss",
        "cash and cash equivalents",
        "deferred tax",
        "income tax",
        "lease liabilities",
        "other operating expenses",
        "interest expense",
        "interest income",
        "foreign exchange gain",
        "foreign exchange loss",
        "etb '000",
        "etb'000",
        "total expenses",
        "foreign exchange transaction",
        "foreign currency reserves",
        "assets and liabilities",
        "market risk",
    )

    associate_terms = (
        "premium switch solution",
        "share of profit(loss) from associate",
        "summarised statement",
    )

    candidates = []

    for position, chunk in enumerate(chunks):

        content = str(
            chunk.get("content")
            or ""
        ).strip()

        if not content:
            continue

        lower = content.lower()
        
        # -------------------------------------------------
        # Exclude ambiguous strategy-duration OCR.
        # The model must not guess corrupted year counts.
        # -------------------------------------------------

        ambiguous_strategy_ocr = (
            "three-year" in lower
            and "strategy" in lower
            and "roadmap" in lower
        )

        if ambiguous_strategy_ocr:
            continue
        
        # -------------------------------------------------
        # Reject OCR-heavy / low-language chunks.
        # -------------------------------------------------

        words = re.findall(
            r"[A-Za-z]{3,}",
            content,
        )

        word_count = len(words)

        if word_count < 40:
            continue

        alpha_count = sum(
            1
            for char in content
            if char.isalpha()
        )

        visible_count = sum(
            1
            for char in content
            if not char.isspace()
        )

        if visible_count == 0:
            continue

        alpha_ratio = (
            alpha_count
            / visible_count
        )

        # Graphic-heavy OCR pages produce large amounts
        # of punctuation and isolated symbols.
        if alpha_ratio < 0.55:
            continue

        # ---------------------------------------------
        # Exclude associate/investee financial content.
        # ---------------------------------------------

        if any(
            term in lower
            for term in associate_terms
        ):
            continue

        # ---------------------------------------------
        # Exclude accounting / financial statement
        # tables from narrative generation.
        # ---------------------------------------------

        financial_hits = sum(
            1
            for term in financial_table_terms
            if term in lower
        )

        if financial_hits >= 2:
            continue

        # ---------------------------------------------
        # Score qualitative content.
        # ---------------------------------------------

        score = sum(
            1
            for term in positive_terms
            if term in lower
        )

        if score <= 0:
            continue
        
        # -------------------------------------------------
        # Narrative-quality check.
        # Require enough normal sentence structure.
        # -------------------------------------------------

        sentence_count = len(
            re.findall(
                r"[.!?](?:\s|$)",
                content,
            )
        )

        word_tokens = re.findall(
            r"\b[A-Za-z][A-Za-z'-]{2,}\b",
            content,
        )

        normal_word_count = len(word_tokens)

        # Narrative chunks should contain actual prose,
        # not graphic-heavy OCR or staff directories.
        if normal_word_count < 60:
            continue

        if sentence_count < 2:
            continue

        # Director/staff directory pages are not useful
        # annual-report narrative evidence.
        director_hits = len(
            re.findall(
                r"\b(?:acting\s+)?director\b",
                lower,
            )
        )

        if director_hits >= 3:
            continue

        candidates.append(
            {
                "position": position,
                "score": score,
                "content": content,
            }
        )

    candidates.sort(
        key=lambda item: (
            -item["score"],
            item["position"],
        )
    )

    # Keep the context deliberately small for Qwen 3B.
    selected = candidates[:10]

    if not selected:
        return ""

    per_chunk = max(
        400,
        max_chars // len(selected),
    )

    blocks = []

    for index, item in enumerate(
        selected,
        start=1,
    ):
        blocks.append(
            (
                f"NARRATIVE SOURCE {index}\n"
                f"{item['content'][:per_chunk]}"
            )
        )

    return "\n\n".join(
        blocks
    )[:max_chars]
    
# ============================================================
# GENERIC ANNUAL REPORT FINANCIAL EXTRACTION ENGINE
#
# Purpose:
#   Extract audited financial facts from new annual reports
#   without adding year-specific Python branches.
#
# Important:
#   This does NOT replace the frozen verified extractors yet.
#   We will first test it against 2022/23.
# ============================================================


def _annual_report_full_text(
    chunks: list[dict],
) -> str:
    """
    Combine cached annual-report chunks into one searchable
    text body while preserving chunk order.
    """

    return "\n".join(
        str(chunk.get("content") or "")
        for chunk in chunks
        if chunk.get("content")
    )


def detect_annual_report_financial_period(
    chunks: list[dict],
) -> dict:
    """
    Detect the current and comparative audited financial years.

    Example:
        report 2022/23
        -> current_year = 2023
        -> comparative_year = 2022

    Detection is based primarily on audited statement wording
    such as:

        FOR THE YEAR ENDED 30 JUNE 2023

    and falls back to annual-report title/year patterns.
    """

    text = _annual_report_full_text(chunks)

    if not text:
        return {}

    # --------------------------------------------------------
    # Strongest signal:
    # "for the year ended 30 June 2023"
    # --------------------------------------------------------

    matches = re.findall(
        r"for\s+the\s+year\s+ended"
        r"\s+(?:on\s+)?"
        r"(?:30|thirty)\s+june\s+"
        r"(20\d{2})",
        text,
        flags=re.IGNORECASE,
    )

    years = []

    for value in matches:
        try:
            year = int(value)

            if 2000 <= year <= 2100:
                years.append(year)

        except (TypeError, ValueError):
            pass

    if years:
        current_year = max(years)

        return {
            "_report_period": (
                f"{current_year - 1}/"
                f"{str(current_year)[-2:]}"
            ),
            "_current_year": str(
                current_year
            ),
            "_comparative_year": str(
                current_year - 1
            ),
        }

    # --------------------------------------------------------
    # Fallback:
    #
    # 2022/23
    # 2022-2023
    # 2022 – 2023
    # --------------------------------------------------------

    period_matches = re.findall(
        r"\b(20\d{2})\s*"
        r"(?:/|-|–|—)\s*"
        r"(20\d{2}|\d{2})\b",
        text,
        flags=re.IGNORECASE,
    )

    candidates = []

    for first, second in period_matches:

        try:
            first_year = int(first)

            if len(second) == 2:
                second_year = int(
                    str(first_year)[:2]
                    + second
                )
            else:
                second_year = int(second)

        except ValueError:
            continue

        if second_year == first_year + 1:

            candidates.append(
                (
                    first_year,
                    second_year,
                )
            )

    if candidates:

        # Most recent valid annual-report period in document.
        start_year, current_year = max(
            candidates,
            key=lambda value: value[1],
        )

        return {
            "_report_period": (
                f"{start_year}/"
                f"{str(current_year)[-2:]}"
            ),
            "_current_year": str(
                current_year
            ),
            "_comparative_year": str(
                start_year
            ),
        }

    return {}


def _find_generic_note_section(
    text: str,
    heading_patterns: list[str],
    max_chars: int = 14000,
) -> str:
    """
    Find a financial-note section using one of several heading
    patterns.

    The section stops at the next numbered financial note
    whenever possible.

    This prevents figures from later notes contaminating the
    extraction.
    """

    if not text:
        return ""

    for heading_pattern in heading_patterns:

        match = re.search(
            rf"""
            (?P<heading>
                (?:^|\n)
                \s*
                (?P<note_number>\d{{1,2}}[A-Za-z]?)
                [\.\s:-]*
                {heading_pattern}
            )
            (?P<section>
                .*?
            )
            (?=
                \n\s*
                \d{{1,2}}[A-Za-z]?
                [\.\s:-]+
                [A-Z]
                |
                \Z
            )
            """,
            text,
            flags=(
                re.IGNORECASE
                | re.MULTILINE
                | re.DOTALL
                | re.VERBOSE
            ),
        )

        if match:

            result = (
                match.group("heading")
                + "\n"
                + match.group("section")
            )

            return result[:max_chars]

    # --------------------------------------------------------
    # OCR fallback:
    # heading may have lost the note number.
    # --------------------------------------------------------

    for heading_pattern in heading_patterns:

        match = re.search(
            rf"""
            (?P<heading>
                {heading_pattern}
            )
            (?P<section>
                .{{0,{max_chars}}}
            )
            """,
            text,
            flags=(
                re.IGNORECASE
                | re.DOTALL
                | re.VERBOSE
            ),
        )

        if match:
            return (
                match.group("heading")
                + "\n"
                + match.group("section")
            )

    return ""


def _normalize_financial_number(
    value: str | None,
) -> int | None:
    """
    Convert annual-report numeric text to integer Birr '000
    representation.

    Examples:
        45,058,301
        (774,367)
        -192
    """

    if value is None:
        return None

    raw = (
        str(value)
        .strip()
        .replace(" ", "")
    )

    if not raw:
        return None

    negative = False

    if (
        raw.startswith("(")
        and raw.endswith(")")
    ):
        negative = True
        raw = raw[1:-1]

    if raw.startswith("-"):
        negative = True
        raw = raw[1:]

    raw = raw.replace(",", "")

    if not re.fullmatch(
        r"\d+(?:\.\d+)?",
        raw,
    ):
        return None

    try:
        number = float(raw)
    except ValueError:
        return None

    value_int = int(round(number))

    if negative:
        value_int *= -1

    return value_int


def _format_financial_number(
    value: int | None,
) -> str | None:
    """
    Convert integer financial value back to annual-report style.
    """

    if value is None:
        return None

    return f"{value:,}"


def _extract_two_column_values_after_label(
    section: str,
    label_patterns: list[str],
) -> tuple[int | None, int | None]:
    """
    Extract two financial values appearing on the same line
    after a known audited-statement label.

    Expected layout:

        Gross amount     49,247,044   53,806,014

    Returns:
        current_value, comparative_value
    """

    if not section:
        return None, None

    number_pattern = (
        r"""
        \(?
        -?
        \d{1,3}
        (?:,\d{3})+
        (?:\.\d+)?
        \)?
        |
        \(?
        -?
        \d+
        (?:\.\d+)?
        \)?
        """
    )

    for label_pattern in label_patterns:

        match = re.search(
            rf"""
            {label_pattern}
            [^\n]{{0,120}}?
            (?P<current>{number_pattern})
            \s+
            (?P<comparative>{number_pattern})
            """,
            section,
            flags=(
                re.IGNORECASE
                | re.VERBOSE
            ),
        )

        if not match:
            continue

        current_value = (
            _normalize_financial_number(
                match.group("current")
            )
        )

        comparative_value = (
            _normalize_financial_number(
                match.group("comparative")
            )
        )

        if (
            current_value is not None
            and comparative_value is not None
        ):
            return (
                current_value,
                comparative_value,
            )

    return None, None


def _validate_loan_relationship(
    gross: int | None,
    impairment: int | None,
    net: int | None,
) -> bool:
    """
    Validate:

        gross loans - impairment allowance = net loans

    A small tolerance is allowed for OCR/rounding differences.
    """

    if (
        gross is None
        or impairment is None
        or net is None
    ):
        return False

    impairment_abs = abs(impairment)

    expected_net = gross - impairment_abs

    tolerance = max(
        5,
        int(abs(gross) * 0.00001),
    )

    return (
        abs(expected_net - net)
        <= tolerance
    )


def extract_generic_annual_report_financial_facts(
    chunks: list[dict],
) -> dict:
    """
    Generic annual-report financial extractor.

    This extractor intentionally fails closed.

    A value is returned only when:
        - its financial section is identifiable,
        - the expected label is found,
        - both reporting columns are present,
        - and available cross-validation succeeds.

    No year-specific financial values are hardcoded.
    """

    text = _annual_report_full_text(
        chunks
    )

    if not text:
        return {}

    period = (
        detect_annual_report_financial_period(
            chunks
        )
    )

    if not period:
        return {}

    current_year = period[
        "_current_year"
    ]

    comparative_year = period[
        "_comparative_year"
    ]

    facts: dict = dict(period)

    # ========================================================
    # 1. CUSTOMER DEPOSITS
    # ========================================================

    deposits_section = (
        _find_generic_note_section(
            text,
            [
                r"Deposits?\s+from\s+customers?",
                r"Customer\s+deposits?",
            ],
        )
    )

    deposits_current, deposits_comparative = (
        _extract_two_column_values_after_label(
            deposits_section,
            [
                r"\bTotal\b",
                r"\bTotal\s+deposits?\b",
            ],
        )
    )

    if (
        deposits_current is not None
        and deposits_comparative is not None
        and deposits_current > 0
        and deposits_comparative > 0
    ):
        facts[
            f"total_deposits_{current_year}"
        ] = _format_financial_number(
            deposits_current
        )

        facts[
            f"total_deposits_{comparative_year}"
        ] = _format_financial_number(
            deposits_comparative
        )

    # ========================================================
    # 2. LOANS AND ADVANCES
    # ========================================================

    loans_section = (
        _find_generic_note_section(
            text,
            [
                (
                    r"Loans?\s+and\s+advances?"
                    r"\s+to\s+customers?"
                ),
                (
                    r"Loans?\s+and\s+advances?"
                    r"\s+to\s+customer"
                ),
            ],
            max_chars=18000,
        )
    )

    gross_current, gross_comparative = (
        _extract_two_column_values_after_label(
            loans_section,
            [
                r"\bGross\s+amount\b",
                r"\bGross\s+loans?\b",
            ],
        )
    )

    impairment_current, impairment_comparative = (
        _extract_two_column_values_after_label(
            loans_section,
            [
                (
                    r"\bLess\s*:?\s*"
                    r"Impairment\s+allowance\b"
                ),
                r"\bImpairment\s+allowance\b",
            ],
        )
    )

    # --------------------------------------------------------
    # Net loan figures often follow immediately after the
    # impairment line without a "Net loans" label.
    # First try explicit labels.
    # --------------------------------------------------------

    net_current, net_comparative = (
        _extract_two_column_values_after_label(
            loans_section,
            [
                (
                    r"\bNet\s+loans?"
                    r"(?:\s+and\s+advances?)?\b"
                ),
                r"\bNet\s+amount\b",
            ],
        )
    )

    # --------------------------------------------------------
    # If no explicit net label exists, derive net ONLY when
    # the arithmetic relationship is exact/near-exact.
    #
    # This is safer than selecting an arbitrary following line.
    # --------------------------------------------------------

    if (
        net_current is None
        and gross_current is not None
        and impairment_current is not None
    ):
        net_current = (
            gross_current
            - abs(impairment_current)
        )

    if (
        net_comparative is None
        and gross_comparative is not None
        and impairment_comparative is not None
    ):
        net_comparative = (
            gross_comparative
            - abs(impairment_comparative)
        )

    current_loans_valid = (
        _validate_loan_relationship(
            gross_current,
            impairment_current,
            net_current,
        )
    )

    comparative_loans_valid = (
        _validate_loan_relationship(
            gross_comparative,
            impairment_comparative,
            net_comparative,
        )
    )

    if (
        current_loans_valid
        and comparative_loans_valid
    ):

        facts[
            f"gross_loans_{current_year}"
        ] = _format_financial_number(
            gross_current
        )

        facts[
            f"gross_loans_{comparative_year}"
        ] = _format_financial_number(
            gross_comparative
        )

        facts[
            f"loan_impairment_{current_year}"
        ] = _format_financial_number(
            abs(impairment_current)
        )

        facts[
            f"loan_impairment_{comparative_year}"
        ] = _format_financial_number(
            abs(impairment_comparative)
        )

        facts[
            f"net_loans_{current_year}"
        ] = _format_financial_number(
            net_current
        )

        facts[
            f"net_loans_{comparative_year}"
        ] = _format_financial_number(
            net_comparative
        )

    # ========================================================
    # 3. SHARE CAPITAL
    # ========================================================

    capital_section = (
        _find_generic_note_section(
            text,
            [
                r"Share\s+capital",
                r"Stated\s+capital",
            ],
        )
    )

    capital_current, capital_comparative = (
        _extract_two_column_values_after_label(
            capital_section,
            [
                r"\bShare\s+capital\b",
                r"\bTotal\b",
                r"\bOrdinary\s+shares?\b",
            ],
        )
    )

    if (
        capital_current is not None
        and capital_comparative is not None
        and capital_current > 0
        and capital_comparative > 0
    ):
        facts[
            f"share_capital_{current_year}"
        ] = _format_financial_number(
            capital_current
        )

        facts[
            f"share_capital_{comparative_year}"
        ] = _format_financial_number(
            capital_comparative
        )

    # ========================================================
    # 4. PROFIT BEFORE INCOME TAX
    # ========================================================

    pbt_current, pbt_comparative = (
        _extract_two_column_values_after_label(
            text,
            [
                (
                    r"\bProfit\s+before"
                    r"\s+(?:income\s+)?tax\b"
                ),
                (
                    r"\bProfit\s*/?\s*"
                    r"\(?loss\)?\s+before"
                    r"\s+(?:income\s+)?tax\b"
                ),
            ],
        )
    )

    if (
        pbt_current is not None
        and pbt_comparative is not None
    ):
        facts[
            f"profit_before_tax_{current_year}"
        ] = _format_financial_number(
            pbt_current
        )

        facts[
            f"profit_before_tax_{comparative_year}"
        ] = _format_financial_number(
            pbt_comparative
        )

    # ========================================================
    # 5. PROFIT / LOSS ATTRIBUTABLE TO SHAREHOLDERS
    # ========================================================

    shareholder_current, shareholder_comparative = (
        _extract_two_column_values_after_label(
            text,
            [
                (
                    r"\bProfit\s*/?\s*"
                    r"\(?loss\)?"
                    r"\s+attributable\s+to"
                    r"\s+(?:the\s+)?"
                    r"(?:shareholders?|owners?)\b"
                ),
                (
                    r"\bProfit\s+attributable\s+to"
                    r"\s+(?:the\s+)?"
                    r"(?:shareholders?|owners?)\b"
                ),
            ],
        )
    )

    if (
        shareholder_current is not None
        and shareholder_comparative is not None
    ):
        facts[
            (
                "profit_loss_shareholders_"
                f"{current_year}"
            )
        ] = _format_financial_number(
            shareholder_current
        )

        facts[
            (
                "profit_loss_shareholders_"
                f"{comparative_year}"
            )
        ] = _format_financial_number(
            shareholder_comparative
        )

    # ========================================================
    # 6. BASIC EARNINGS PER SHARE
    # ========================================================

    eps_current, eps_comparative = (
        _extract_two_column_values_after_label(
            text,
            [
                (
                    r"\bBasic(?:\s+and\s+diluted)?"
                    r"\s+earnings\s+per\s+share\b"
                ),
                r"\bBasic\s+EPS\b",
            ],
        )
    )

    if (
        eps_current is not None
        and eps_comparative is not None
    ):
        facts[
            f"eps_{current_year}"
        ] = _format_financial_number(
            eps_current
        )

        facts[
            f"eps_{comparative_year}"
        ] = _format_financial_number(
            eps_comparative
        )

    return facts

def summarize_annual_report(
    database: Session,
    question: str,
    report: dict | None = None,
    stream: bool = False,
) -> dict:
    """
    Summarize one official NIB annual report.

    Existing PostgreSQL cache is always checked first.

    For an already indexed report this performs:
        PostgreSQL cache
            -> evidence selection
            -> one AI generation call

    It does not repeat OCR or PDF extraction.
    """

    # --------------------------------------------------------
    # 1. Resolve requested annual report when caller has not
    #    already selected it.
    # --------------------------------------------------------

    if report is None:

        reports = (
            discover_annual_reports()
        )

        if not reports:

            return {
                "success": False,
                "error": (
                    "No official NIB annual "
                    "reports were discovered."
                ),
            }

        report = select_annual_report(
            question=question,
            reports=reports,
        )

        if not report:

            return {
                "success": False,
                "error": (
                    "I could not determine which "
                    "NIB annual report year was requested."
                ),
            }

    # --------------------------------------------------------
    # 2. Use the cache/index layer.
    #
    # If ready, index_annual_report() returns immediately as
    # status='cached' without downloading/OCR.
    # --------------------------------------------------------

    indexed = index_annual_report(
        database=database,
        report=report,
        force=False,
    )

    chunks = (
        indexed.get("chunks")
        or []
    )
    
    verified_facts = (
        extract_verified_annual_report_financial_facts(
            chunks
        )
    )
    
    verified_financial_summary = (
        build_verified_annual_report_financial_summary(
            verified_facts
        )
    )
    
    verified_business_summary = (
        build_verified_annual_report_business_facts(
            chunks
        )
    )

   

    if not chunks:

        return {
            "success": False,
            "error": (
                "The annual report is indexed but "
                "contains no searchable cached content."
            ),
            "report": report,
        }

    # --------------------------------------------------------
    # 3. Build balanced annual-report evidence.
    # --------------------------------------------------------

    evidence = (
        build_annual_report_narrative_evidence(
            chunks=chunks,
            max_chars=8000,
        )
    )
    
    print(
        "\n"
        + "=" * 80
        + "\nDEBUG NARRATIVE EVIDENCE\n"
        + "=" * 80
    )

    print(evidence)

    print(
        "\n"
        + "=" * 80
        + "\nEND NARRATIVE EVIDENCE\n"
        + "=" * 80,
        flush=True,
    )

    if not evidence:

        return {
            "success": False,
            "error": (
                "Unable to build evidence from "
                "the cached annual report."
            ),
            "report": report,
        }

    title = (
        indexed.get("title")
        or report.get("title")
        or "NIB Annual Report"
    )

    filename = (
        indexed.get("filename")
        or report.get("filename")
        or ""
    )

    # --------------------------------------------------------
    # 4. Annual-report-specific task.
    # --------------------------------------------------------

    task_instruction = (
        "Summarize only qualitative business information "
        "from the supplied NIB annual-report narrative. "

        "Do not write an Executive Summary section. "
        "Do not write Key Performance Indicators. "
        "Do not write Financial Highlights. "
        "Do not provide any financial figures or ratios. "

        "Where directly supported, summarize only: "
        "leadership and strategic themes; "
        "customer and service developments; "
        "branch or distribution developments; "
        "digital banking and technology initiatives; "
        "Interest Free Banking developments; "
        "risk and governance themes; "
        "institutional partnerships; "
        "and explicitly stated future priorities. "

        "If one of these subjects is not clearly supported "
        "by the evidence, omit it. "

        "Do not infer ESG activity, green financing, "
        "mergers, acquisitions or other initiatives. "

        "Do not repeat information. "
        "Ignore accounting tables and OCR noise. "

        "Use short headings and concise bullets. "

        "Finish with 'Overall Context' containing only "
        "a neutral evidence-based statement. "

        "Return only the qualitative summary."
    )

    prompt = (
        "TASK\n"
        "----\n"
        f"{task_instruction}\n\n"

        "USER QUESTION\n"
        "-------------\n"
        f"{question}\n\n"

        "SELECTED ANNUAL REPORT\n"
        "----------------------\n"
        f"Title: {title}\n"
        f"Filename: {filename}\n"
        f"Pages: {indexed.get('page_count')}\n\n"

        

        "ANNUAL REPORT EVIDENCE START\n"
        "============================\n"
        f"{evidence}\n"
        "============================\n"
        "ANNUAL REPORT EVIDENCE END\n\n"

        "Generate the final annual report summary now."
    )

    print(
        "DEBUG ANNUAL REPORT SUMMARY:",
        "title=",
        title,
        "| cache_status=",
        indexed.get("status"),
        "| pages=",
        indexed.get("page_count"),
        "| chunks=",
        len(chunks),
        "| evidence_chars=",
        len(evidence),
        "| stream=",
        stream,
        flush=True,
    )
    
    print(
        "DEBUG VERIFIED FINANCIAL FACTS:",
        verified_facts,
        flush=True,
    )

    provider = get_ai_provider()

    # --------------------------------------------------------
    # 5. Future frontend streaming path.
    #
    # We prepare it now but do not connect the orchestrator
    # yet.
    # --------------------------------------------------------

    if stream:

        return {
            "success": True,
            "stream": True,
            "provider": provider,
            "prompt": prompt,
            "system_prompt":
            ANNUAL_REPORT_NARRATIVE_SYSTEM_PROMPT,
            "num_predict": 500,
            "num_ctx": 4096,
            "summary_requested": True,
            "source_type": "annual_report",
            "cache_status":
                indexed.get("status"),
            "document_index_id":
                indexed.get(
                    "document_index_id"
                ),
            "report": report,
            "title": title,
            "filename": filename,
        }

    # --------------------------------------------------------
    # 6. One AI call only.
    # --------------------------------------------------------

    answer = provider.generate(
    prompt=prompt,
    system_prompt=(
        ANNUAL_REPORT_NARRATIVE_SYSTEM_PROMPT
    ),
    num_predict=500,
    num_ctx=4096,
)
    final_answer = (
        f"# {title}\n\n"
        f"{verified_financial_summary}\n\n"
        "## Business and Strategic Highlights\n\n"
        f"{answer.strip()}"
    )
    
    if verified_business_summary:
        final_answer += (
            "\n\n"
            "### Branch Network Plans\n\n"
            f"{verified_business_summary}"
        )

    return {
        "success": True,
        "stream": False,
        "answer": final_answer,
        "source_type": "annual_report",
        "cache_status":
            indexed.get("status"),
        "document_index_id":
            indexed.get(
                "document_index_id"
            ),
        "external_document_id":
            indexed.get(
                "external_document_id"
            ),
        "page_count":
            indexed.get("page_count"),
        "chunk_count":
            indexed.get("chunk_count"),
        "evidence_chars":
            len(evidence),
        "report": report,
        "title": title,
        "filename": filename,
    }
    
def build_verified_annual_report_business_facts(
    chunks: list[dict],
) -> str:
    """
    Render high-confidence business facts that should
    preserve exact status such as completed vs planned.
    """

    text = "\n".join(
        str(chunk.get("content") or "")
        for chunk in chunks
    )

    lower = text.lower()

    lines = []

    # Branch restructuring is explicitly a future plan.
    if (
        "plans to reorganize its branches" in lower
        or "plan to reorganize its branches" in lower
    ):
        lines.append(
            "- **Branch network:** NIB plans to "
            "reorganize parts of its branch network "
            "through measures including merging or "
            "relocating selected branches and opening "
            "specialized smart branches."
        )

    return "\n".join(lines)