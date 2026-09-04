from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document_index import (
    DocumentIndex,
)
from app.models.document_chunk import (
    DocumentChunk,
)

from app.ai.document_file_resolver import (
    fetch_document_file,
)

from app.ai.document_extractor import (
    extract_document,
)

from app.ai.document_retriever import (
    chunk_pages,
)


# ============================================================
# HELPERS
# ============================================================


def get_document_data_source_id() -> int:
    """
    Return the configured DMS datasource ID.
    """

    value = getattr(
        settings,
        "dms_data_source_id",
        None,
    )

    if value is None:
        raise ValueError(
            "DMS_DATA_SOURCE_ID is not configured."
        )

    return int(value)


def calculate_file_fingerprint(
    file_path: str,
) -> str:
    """
    Calculate SHA-256 fingerprint of the physical document.

    This allows NIBGPT to determine whether the DMS file
    changed after it was indexed.
    """

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file_handle:

        while True:

            block = file_handle.read(
                1024 * 1024
            )

            if not block:
                break

            sha256.update(block)

    return sha256.hexdigest()


def get_cached_document(
    database: Session,
    external_document_id: int,
) -> DocumentIndex | None:

    print(
        "DEBUG INDEX 0C: BEFORE DATA SOURCE"
    )

    data_source_id = (
        get_document_data_source_id()
    )

    print(
        "DEBUG INDEX 0D: AFTER DATA SOURCE:",
        data_source_id,
    )

    return (
        database.query(
            DocumentIndex
        )
        .filter(
            DocumentIndex.data_source_id
            == data_source_id,
            DocumentIndex.external_document_id
            == int(external_document_id),
        )
        .first()
    )


def get_cached_chunks(
    database: Session,
    document_index_id: int,
) -> list[dict]:
    """
    Load indexed chunks from PostgreSQL using the same
    structure expected by document_retriever.py.
    """

    records = (
        database.query(
            DocumentChunk
        )
        .filter(
            DocumentChunk.document_index_id
            == document_index_id
        )
        .order_by(
            DocumentChunk.chunk_order.asc()
        )
        .all()
    )

    chunks = []

    for record in records:

        chunks.append(
            {
                # Internal retrieval identifiers.
                #
                # They do not represent DMS clause numbers.
                # They are only used for deduplication and
                # ordering inside document_retriever.py.
                "section_id":
                    record.id,

                "chunk_no":
                    record.chunk_order,

                "page_number":
                    record.page_number,

                "start_page":
                    record.start_page,

                "end_page":
                    record.end_page,

                "section_number":
                    record.section_number,

                "section_title":
                    record.section_title,

                "parent_section_number":
                    record.parent_section_number,

                "parent_section_title":
                    record.parent_section_title,

                "content":
                    record.content,

                "extraction_method":
                    record.extraction_method,

                "score":
                    0.0,
            }
        )

    return chunks

def retrieve_cached_major_section_chunks(
    database,
    document_index_id: int,
    major_section_number: str,
) -> list[dict]:
    """
    Retrieve all cached chunks belonging to one
    logical major numbered section.

    The explicit section number found in the title
    takes priority over OCR/parser section_number.

    Example:
        section_number = "7"
        section_title  = "6. CREDIT DECISION"

    This belongs to major section 6, not 7.
    """

    import re

    major = str(
        major_section_number
        or ""
    ).strip()

    if not major:
        return []

    rows = (
        database.query(DocumentChunk)
        .filter(
            DocumentChunk.document_index_id
            == document_index_id
        )
        .order_by(
            DocumentChunk.chunk_order.asc()
        )
        .all()
    )

    results = []

    # ---------------------------------------------
    # Common front-matter headings.
    # These should not contaminate numbered
    # operational/policy sections when OCR assigns
    # them an incorrect section number.
    # ---------------------------------------------

    front_matter_titles = {
        "acronym",
        "acronyms",
        "abbreviation",
        "abbreviations",
        "table of contents",
        "contents",
        "glossary",
        "list of acronyms",
        "list of abbreviations",
    }
    
    def major_from_content(
        value,
    ) -> str | None:

        import re

        text = str(
            value
            or ""
        )

        if not text:
            return None

        sample = text[:1200]

        match = re.search(
            r"(?m)^\s*"
            r"(\d+)"
            r"\.\d+"
            r"(?:\.\d+)*"
            r"[\.\)]?"
            r"\s+",
            sample,
        )

        if not match:
            return None

        return match.group(1)

    def normalize_title(
        value,
    ) -> str:

        text = str(
            value
            or ""
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return (
            text
            .strip()
            .lower()
            .strip(
                " .:-–—'\"‘’"
            )
        )

    def explicit_major_from_title(
        value,
    ) -> str | None:
        """
        Extract explicit leading major number
        from a heading.

        Examples:
            "6. CREDIT DECISION" -> "6"
            "10 LOAN COLLECTION" -> "10"
            "8.2 Credit Monitoring" -> "8"
        """

        text = str(
            value
            or ""
        ).strip()

        if not text:
            return None

        match = re.match(
            r"^\s*(\d+)"
            r"(?:\.\d+)*"
            r"(?:\s*[\.\):\-–—]|\s+)",
            text,
        )

        if not match:
            return None

        return match.group(1)

    def major_from_number(
        value,
    ) -> str | None:

        text = str(
            value
            or ""
        ).strip()

        if not text:
            return None

        match = re.match(
            r"^(\d+)",
            text,
        )

        if not match:
            return None

        return match.group(1)

    for row in rows:

        section_number = str(
            getattr(
                row,
                "section_number",
                "",
            )
            or ""
        ).strip()

        section_title = str(
            getattr(
                row,
                "section_title",
                "",
            )
            or ""
        ).strip()

        parent_number = str(
            getattr(
                row,
                "parent_section_number",
                "",
            )
            or ""
        ).strip()

        parent_title = str(
            getattr(
                row,
                "parent_section_title",
                "",
            )
            or ""
        ).strip()
        
        content = str(
            getattr(
                row,
                "content",
                "",
            )
            or ""
        )

        # -----------------------------------------
        # 1. Ignore obvious front matter
        # -----------------------------------------

        normalized_title = (
            normalize_title(
                section_title
            )
        )

        if (
            normalized_title
            in front_matter_titles
        ):
            continue

        # -----------------------------------------
        # 2. Determine logical major section
        #
        # Priority:
        # explicit section title
        # -> section_number
        # -> explicit parent title
        # -> parent_number
        # -----------------------------------------

        title_major = (
            explicit_major_from_title(
                section_title
            )
        )

        section_major = (
            major_from_number(
                section_number
            )
        )

        parent_title_major = (
            explicit_major_from_title(
                parent_title
            )
        )

        parent_major = (
            major_from_number(
                parent_number
            )
        )
        
        content_major = (
            major_from_content(
                content
            )
        )

        normalized_title = (
            normalize_title(
                section_title
            )
        )

        title_words = (
            normalized_title.split()
        )

        weak_title = (
            not normalized_title
            or len(normalized_title) <= 5
            or (
                len(title_words) <= 2
                and not title_major
            )
        )

        # Explicit numbered title remains strongest.
        if title_major:

            effective_major = (
                title_major
            )

        # For weak OCR headings, hierarchical numbering
        # inside the actual body is more reliable than
        # corrupted parser metadata.
        elif (
            content_major
            and weak_title
        ):

            effective_major = (
                content_major
            )

        elif section_major:

            effective_major = (
                section_major
            )

        elif parent_title_major:

            effective_major = (
                parent_title_major
            )

        else:

            effective_major = (
                parent_major
            )

        if effective_major != major:
            continue

        results.append(
            {
                "id": row.id,

                "section_number": getattr(
                    row,
                    "section_number",
                    None,
                ),

                "section_title": getattr(
                    row,
                    "section_title",
                    None,
                ),

                "parent_section_number":
                    getattr(
                        row,
                        "parent_section_number",
                        None,
                    ),

                "parent_section_title":
                    getattr(
                        row,
                        "parent_section_title",
                        None,
                    ),

                "content": getattr(
                    row,
                    "content",
                    "",
                )
                or "",

                "page_number": getattr(
                    row,
                    "page_number",
                    None,
                ),

                "chunk_order": getattr(
                    row,
                    "chunk_order",
                    0,
                ),

                "extraction_method":
                    getattr(
                        row,
                        "extraction_method",
                        None,
                    ),

                "score": 0.0,
            }
        )

    return results

def expand_summary_groups_with_cached_chunks(
    database,
    document_index_id: int,
    groups: list[dict],
) -> list[dict]:
    """
    Replace representative summary chunks with the
    full cached chunks for each numbered major section.

    Unnumbered groups are kept unchanged.
    """

    expanded_groups = []

    for group in groups:

        major_number = (
            group.get("major_section_number")
        )

        # Keep unnumbered groups as they are.
        if not major_number:

            expanded_groups.append(
                group
            )

            continue

        full_chunks = (
            retrieve_cached_major_section_chunks(
                database=database,
                document_index_id=document_index_id,
                major_section_number=str(
                    major_number
                ),
            )
        )

        expanded_group = {
            **group,
            "chunks": (
                full_chunks
                if full_chunks
                else group.get("chunks", [])
            ),
        }

        expanded_groups.append(
            expanded_group
        )

    return expanded_groups

def build_hierarchical_summary_evidence(
    groups: list[dict],
    max_chars: int = 8500,
) -> str:
    """
    Build balanced whole-document evidence from
    already-expanded major section groups.

    Each major section receives its own evidence
    budget so later sections are not lost simply
    because earlier sections contain more text.
    """

    if not groups:
        return ""

    # Remove completely empty groups.
    usable_groups = [
        group
        for group in groups
        if group.get("chunks")
    ]

    if not usable_groups:
        return ""

    separator = "\n\n" + ("-" * 50) + "\n\n"

    # Reserve room for section headings/separators.
    metadata_reserve = (
        len(usable_groups) * 120
    )

    available_chars = max(
        1000,
        max_chars - metadata_reserve,
    )

    per_group_budget = max(
        280,
        available_chars
        // len(usable_groups),
    )

    blocks = []

    for group in usable_groups:

        major_number = (
            group.get(
                "major_section_number"
            )
        )

        major_title = str(
            group.get(
                "major_section_title"
            )
            or "Document Section"
        ).strip()

        # The document-introduction group usually
        # needs much less space than substantive
        # numbered sections.
        if major_number is None:
            group_budget = min(
                450,
                per_group_budget,
            )
        else:
            group_budget = (
                per_group_budget
            )

        evidence = (
            build_summary_group_evidence(
                group=group,
                max_chars=group_budget,
            )
        )

        if not evidence:
            continue

        blocks.append(
            evidence
        )

    combined = separator.join(
        blocks
    )

    return combined[:max_chars]


# ============================================================
# INDEX DOCUMENT
# ============================================================


def index_document(
    database: Session,
    document: dict,
    force: bool = False,
) -> dict:
    """
    Download, extract/OCR, parse and cache one DMS document.

    The DMS remains the source of truth.
    PostgreSQL stores only the searchable representation.
    """
    
    print(
    "DEBUG INDEX 0A: ENTERED index_document"
)

    external_document_id = (
        document.get("id")
    )

    filename = (
        document.get("filename")
    )

    if external_document_id is None:
        raise ValueError(
            "DMS document does not contain an ID."
        )

    if not filename:
        raise ValueError(
            "DMS document does not contain a filename."
        )

    data_source_id = (
        get_document_data_source_id()
    )

    print(
        "DEBUG INDEX 0E: BEFORE GET CACHED DOCUMENT"
    )

    cached_document = (
        get_cached_document(
            database=database,
            external_document_id=(
                int(external_document_id)
            ),
        )
    )

    print(
        "DEBUG INDEX 0F: AFTER GET CACHED DOCUMENT:",
        cached_document.id
        if cached_document
        else None,
    )

    # --------------------------------------------------------
    # Download current physical file
    # --------------------------------------------------------

    print(
        "DEBUG INDEX 1: BEFORE DOWNLOAD:",
        filename,
    )

    file_path = fetch_document_file(
        filename
    )

    print(
        "DEBUG INDEX 2: AFTER DOWNLOAD:",
        file_path,
    )

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Document file not found: {file_path}"
        )

    print(
        "DEBUG INDEX 3: BEFORE FINGERPRINT"
    )

    current_fingerprint = (
        calculate_file_fingerprint(
            file_path
        )
    )

    print(
        "DEBUG INDEX 4: AFTER FINGERPRINT"
    )

    # --------------------------------------------------------
    # Existing valid cache
    # --------------------------------------------------------

    if (
        cached_document
        and not force
        and cached_document.status == "ready"
        and cached_document.file_fingerprint
        == current_fingerprint
    ):

        chunks = get_cached_chunks(
            database=database,
            document_index_id=(
                cached_document.id
            ),
        )

        if chunks:

            return {
                "status": "cached",
                "document_index_id":
                    cached_document.id,
                "external_document_id":
                    int(external_document_id),
                "filename":
                    filename,
                "page_count":
                    cached_document.page_count,
                "chunk_count":
                    len(chunks),
                "fingerprint":
                    current_fingerprint,
                "chunks":
                    chunks,
            }

    # --------------------------------------------------------
    # Create/update index record
    # --------------------------------------------------------

    if cached_document is None:

        cached_document = DocumentIndex(
            data_source_id=data_source_id,
            external_document_id=(
                int(external_document_id)
            ),
            filename=filename,
            title=(
                document.get("file_desc")
                or filename
            ),
            department=(
                document.get("department")
            ),
            file_fingerprint=(
                current_fingerprint
            ),
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
            document.get("file_desc")
            or filename
        )

        cached_document.department = (
            document.get("department")
        )

        cached_document.file_fingerprint = (
            current_fingerprint
        )

        cached_document.status = (
            "processing"
        )

        cached_document.error_message = (
            None
        )

        # Remove previous chunks before rebuilding.
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

    try:
        
        print(
            "DEBUG INDEX 5: DB RECORD READY:",
            cached_document.id,
        )

        # ----------------------------------------------------
        # Extract/OCR document
        # ----------------------------------------------------

        print(
            "DEBUG INDEX 6: BEFORE EXTRACT_DOCUMENT"
        )

        pages = extract_document(
            file_path
        )

        print(
            "DEBUG INDEX 7: AFTER EXTRACT_DOCUMENT:",
            len(pages) if pages else 0,
        )

        if not pages:
            raise ValueError(
                "Document extraction returned no pages."
            )

        # ----------------------------------------------------
        # Convert extracted pages into structured chunks
        # ----------------------------------------------------

        print(
            "DEBUG INDEX 8: BEFORE CHUNK_PAGES"
        )

        chunks = chunk_pages(
            pages
        )

        print(
            "DEBUG INDEX 9: AFTER CHUNK_PAGES:",
            len(chunks) if chunks else 0,
        )

        if not chunks:
            raise ValueError(
                "Document chunking returned no content."
            )

        # ----------------------------------------------------
        # Save chunks
        # ----------------------------------------------------

        for order, chunk in enumerate(
            chunks,
            start=1,
        ):

            start_page = (
                chunk.get("start_page")
                or chunk.get("page_number")
            )

            end_page = (
                chunk.get("end_page")
                or start_page
            )

            record = DocumentChunk(
                document_index_id=(
                    cached_document.id
                ),
                page_number=(
                    chunk.get("page_number")
                    or start_page
                ),
                start_page=start_page,
                end_page=end_page,
                section_number=(
                    chunk.get("section_number")
                ),
                section_title=(
                    chunk.get("section_title")
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
                content=(
                    chunk.get("content")
                    or ""
                ),
                extraction_method=(
                    chunk.get(
                        "extraction_method"
                    )
                ),
                chunk_order=order,
            )

            database.add(
                record
            )

        cached_document.status = (
            "ready"
        )

        cached_document.page_count = (
            len(pages)
        )

        cached_document.error_message = (
            None
        )

        cached_document.indexed_at = (
            datetime.now(
                timezone.utc
            )
        )
        
        print(
            "DEBUG INDEX 10: BEFORE COMMIT:",
            len(chunks),
        )

        database.commit()
        
        print(
            "DEBUG INDEX 11: AFTER COMMIT"
        )

        # Reload chunks from PostgreSQL.
        cached_chunks = (
            get_cached_chunks(
                database=database,
                document_index_id=(
                    cached_document.id
                ),
            )
        )

        return {
            "status": "indexed",
            "document_index_id":
                cached_document.id,
            "external_document_id":
                int(external_document_id),
            "filename":
                filename,
            "page_count":
                len(pages),
            "chunk_count":
                len(cached_chunks),
            "fingerprint":
                current_fingerprint,
            "chunks":
                cached_chunks,
        }

    except Exception as error:
        
        print(
            "DEBUG INDEX ERROR:",
            type(error).__name__,
            str(error),
        )

        database.rollback()

        # Save failure status separately.
        failed_document = (
            get_cached_document(
                database=database,
                external_document_id=(
                    int(external_document_id)
                ),
            )
        )

        if failed_document:

            failed_document.status = (
                "failed"
            )

            failed_document.error_message = (
                str(error)
            )

            database.commit()

        raise
    
def retrieve_cached_chunks(
    database: Session,
    document_index_id: int,
    question: str,
    limit: int = 6,
) -> list[dict]:
    """
    Retrieve the most relevant already-indexed document
    chunks directly from PostgreSQL.

    This avoids PDF extraction, OCR and section parsing.
    """

    chunks = get_cached_chunks(
        database=database,
        document_index_id=document_index_id,
    )

    if not chunks:
        return []

    from app.ai.document_retriever import (
        score_chunk,
        expand_related_sections,
    )

    scored_chunks = []

    for chunk in chunks:

        score = score_chunk(
            question=question,
            chunk=chunk,
        )

        scored_chunk = dict(
            chunk
        )

        scored_chunk["score"] = (
            score
        )

        scored_chunks.append(
            scored_chunk
        )

    scored_chunks.sort(
        key=lambda item: item.get(
            "score",
            0,
        ),
        reverse=True,
    )

    selected = (
        scored_chunks[:limit]
    )

    selected = expand_related_sections(
        question=question,
        selected_chunks=selected,
        all_chunks=scored_chunks,
        limit=limit,
    )

    return selected

def retrieve_cached_chunks(
    database: Session,
    document_index_id: int,
    question: str,
    limit: int = 6,
) -> list[dict]:
    """
    Rank already-indexed PostgreSQL chunks without
    downloading, OCR-processing or reparsing the PDF.
    """

    from app.ai.document_retriever import (
        score_chunk,
        expand_related_sections,
    )

    chunks = get_cached_chunks(
        database=database,
        document_index_id=document_index_id,
    )

    if not chunks:
        return []

    scored = []

    for chunk in chunks:

        score = score_chunk(
            question=question,
            content=(
                chunk.get("content")
                or ""
            ),
            section_title=(
                chunk.get("section_title")
            ),
            parent_section_title=(
                chunk.get(
                    "parent_section_title"
                )
            ),
        )

        scored_chunk = dict(
            chunk
        )

        scored_chunk["score"] = (
            score
        )

        scored.append(
            scored_chunk
        )

    # Highest relevance first.
    scored.sort(
        key=lambda item:
            item.get(
                "score",
                0.0,
            ),
        reverse=True,
    )

    # Prefer positively matching chunks.
    relevant = [
        chunk
        for chunk in scored
        if (
            chunk.get(
                "score",
                0.0,
            )
            > 0
        )
    ]

    # If lexical scoring produced nothing,
    # retain the best available chunks rather
    # than failing immediately.
    if relevant:

        selected = (
            relevant[:limit]
        )

    else:

        selected = (
            scored[:limit]
        )

    # Preserve responsibility / authority hierarchy.
    expanded = (
        expand_related_sections(
            selected=selected,
            all_chunks=scored,
            limit=limit,
        )
    )

    return expanded

def retrieve_cached_responsibility_chunks(
    database: Session,
    document_index_id: int,
) -> list[dict]:
    """
    Retrieve all cached chunks that belong to a
    responsibilities / authorities hierarchy.

    This is deterministic and uses PostgreSQL only.
    It does not download the document, run OCR,
    reparse the PDF, or call an AI provider.
    """

    chunks = get_cached_chunks(
        database=database,
        document_index_id=document_index_id,
    )

    if not chunks:
        return []

    responsibility_chunks = []

    for chunk in chunks:

        parent_title = (
            chunk.get("parent_section_title")
            or ""
        ).lower()

        if (
            "responsib" not in parent_title
            and "authorit" not in parent_title
        ):
            continue

        responsibility_chunks.append(
            chunk
        )

    def sort_key(chunk: dict):

        section_number = (
            chunk.get("section_number")
            or ""
        )

        chunk_order = (
            chunk.get("chunk_order")
            or 0
        )

        try:
            section_parts = tuple(
                int(part)
                for part
                in section_number.split(".")
            )
        except ValueError:
            section_parts = (999999,)

        return (
            section_parts,
            chunk_order,
        )

    responsibility_chunks.sort(
        key=sort_key
    )

    return responsibility_chunks

def retrieve_cached_section_chunks(
    database: Session,
    document_index_id: int,
    section_title: str,
) -> list[dict]:
    """
    Retrieve a complete cached document section
    and its child clauses/sections.

    Example:
        section_title = "purpose"

    Returns:
        2 Purpose
        2.1 ...
        2.2 ...
        2.3 ...
        etc.

    PostgreSQL cache only.
    No OCR and no AI provider call.
    """

    chunks = get_cached_chunks(
        database=database,
        document_index_id=document_index_id,
    )

    if not chunks:
        return []

    target = (
        " ".join(
            (section_title or "")
            .lower()
            .strip()
            .split()
        )
    )

    if not target:
        return []

    parent_section_numbers = set()

    # First identify the section itself.
    for chunk in chunks:

        title = (
            " ".join(
                (
                    chunk.get("section_title")
                    or ""
                )
                .lower()
                .strip()
                .split()
            )
        )

        if title == target:

            section_number = (
                chunk.get("section_number")
                or ""
            )

            if section_number:
                parent_section_numbers.add(
                    section_number
                )

    if not parent_section_numbers:
        return []

    selected = []

    for chunk in chunks:
        
        if chunk.id in selected_ids:
            continue

        section_number = (
            chunk.get("section_number")
            or ""
        )

        parent_section_number = (
            chunk.get("parent_section_number")
            or ""
        )

        include = False

        for parent_number in (
            parent_section_numbers
        ):

            # Exact parent section.
            if section_number == parent_number:
                include = True

            # Direct child.
            elif (
                parent_section_number
                == parent_number
            ):
                include = True

            # Nested child:
            # 2 -> 2.1 -> 2.1.1
            elif section_number.startswith(
                parent_number + "."
            ):
                include = True

            if include:
                break

        if include:
            selected.append(
                dict(chunk)
            )

    def sort_key(chunk: dict):

        section_number = (
            chunk.get("section_number")
            or ""
        )

        chunk_order = (
            chunk.get("chunk_order")
            or 0
        )

        try:
            parts = tuple(
                int(part)
                for part
                in section_number.split(".")
            )

        except ValueError:
            parts = (999999,)

        return (
            parts,
            chunk_order,
        )

    selected.sort(
        key=sort_key
    )

    return selected

def split_summary_chunks_by_major_boundaries(
    chunks: list[dict],
) -> list[dict]:
    """
    Split summary chunks into virtual segments when OCR
    placed multiple major sections inside one cached chunk.

    This affects summarization only.
    It does NOT modify stored document chunks.

    Examples detected:
        1. INTRODUCTION
        2. Main Policy Statements
        4. AUTHORITY AND RESPONSIBILITY
        CHAPTER TWO: POLICY STATEMENTS
        2. Main Policy Statements
    """

    import re

    if not chunks:
        return []

    output = []

    # A major heading must:
    # - start on its own line
    # - use a whole number only
    # - have actual title text after it
    #
    # This avoids matching:
    # 3.14.1
    # 4.6.2
    # etc.
    major_heading_pattern = re.compile(
        r"(?m)^"
        r"\s*"
        r"(\d{1,3})"
        r"\s*[\.\)\-:]"
        r"\s+"
        r"([^\n]{2,100})"
        r"\s*$"
    )
    
    chapter_heading_pattern = re.compile(
        r"(?im)^"
        r"\s*[-–—•|]*\s*"
        r"(?:CHAPTER|CAHPTER)\s+"
        r"(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|"
        r"ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN|SIXTEEN|"
        r"SEVENTEEN|EIGHTEEN|NINETEEN|TWENTY|\d{1,3})"
        r"\s*[:\.\-]?"
        r"\s+"
        r"([^\n]{2,100})"
        r"(?:"
            r"\n"
            r"\s*"
            r"([A-Za-z][^\n]{1,80})"
        r")?"
    )

    chapter_number_map = {
        "ONE": "1",
        "TWO": "2",
        "THREE": "3",
        "FOUR": "4",
        "FIVE": "5",
        "SIX": "6",
        "SEVEN": "7",
        "EIGHT": "8",
        "NINE": "9",
        "TEN": "10",
        "ELEVEN": "11",
        "TWELVE": "12",
        "THIRTEEN": "13",
        "FOURTEEN": "14",
        "FIFTEEN": "15",
        "SIXTEEN": "16",
        "SEVENTEEN": "17",
        "EIGHTEEN": "18",
        "NINETEEN": "19",
        "TWENTY": "20",
    }

    def clean_title(
        value: str,
    ) -> str:

        title = (
            value
            or ""
        ).strip()

        # Remove obvious OCR trailing symbols.
        title = re.sub(
            r"[|_=~]+$",
            "",
            title,
        ).strip()

        return title

    def title_is_plausible(
        title: str,
    ) -> bool:

        value = clean_title(
            title
        )

        if not value:
            return False

        if len(value) > 100:
            return False

        words = value.split()

        if len(words) > 14:
            return False

        # Reject lines that look like normal prose.
        if value.endswith(
            (
                ",",
                ";",
            )
        ):
            return False

        # Require at least one alphabetic word.
        if not any(
            char.isalpha()
            for char in value
        ):
            return False

        return True

    for chunk in chunks:

        content = str(
            chunk.get("content")
            or ""
        )

        if not content.strip():

            output.append(
                chunk
            )

            continue

        matches = []

        for match in (
            major_heading_pattern
            .finditer(content)
        ):

            number = (
                match.group(1)
                or ""
            ).strip()

            title = clean_title(
                match.group(2)
            )

            if not title_is_plausible(
                title
            ):
                continue

            matches.append(
                {
                    "start": match.start(),
                    "end": match.end(),
                    "number": number,
                    "title": title,
                }
            )
            
        # -----------------------------------------
        # Detect chapter-style major headings.
        #
        # Examples:
        # CHAPTER FOUR: AUTHORITIES AND RESPONSIBILITIES
        # CHAPTER 4: AUTHORITIES AND RESPONSIBILITIES
        # -----------------------------------------

        for match in (
            chapter_heading_pattern
            .finditer(content)
        ):

            raw_number = (
                match.group(1)
                or ""
            ).strip().upper()

            if raw_number.isdigit():
                number = raw_number
            else:
                number = (
                    chapter_number_map.get(
                        raw_number
                    )
                )

            if not number:
                continue

            title = clean_title(
                match.group(2)
            )

            if not title_is_plausible(
                title
            ):
                continue

            matches.append(
                {
                    "start": match.start(),
                    "end": match.end(),
                    "number": number,
                    "title": title,
                }
            )

        # Heading types were discovered independently,
        # so restore physical document order.
        matches.sort(
            key=lambda item: item["start"]
        )

        # Remove duplicate boundaries if OCR exposes
        # the same heading in more than one form.
        deduplicated_matches = []

        for match in matches:

            if (
                deduplicated_matches
                and abs(
                    match["start"]
                    -
                    deduplicated_matches[-1]["start"]
                ) < 5
            ):
                continue

            deduplicated_matches.append(
                match
            )

        matches = deduplicated_matches

        # No internal major heading found.
        if not matches:

            output.append(
                chunk
            )

            continue

        # -----------------------------------------
        # Preserve text before the first discovered
        # heading as its own virtual segment.
        # -----------------------------------------

        first_start = (
            matches[0]["start"]
        )

        prefix = (
            content[:first_start]
            .strip()
        )

        if prefix:

            prefix_chunk = dict(
                chunk
            )

            prefix_chunk[
                "content"
            ] = prefix

            prefix_chunk[
                "_virtual_summary_segment"
            ] = True

            output.append(
                prefix_chunk
            )

        # -----------------------------------------
        # Create one virtual chunk for each detected
        # major section.
        # -----------------------------------------

        for index, match in enumerate(
            matches
        ):

            start = (
                match["start"]
            )

            if (
                index + 1
                < len(matches)
            ):

                end = (
                    matches[
                        index + 1
                    ]["start"]
                )

            else:

                end = len(
                    content
                )

            segment_content = (
                content[start:end]
                .strip()
            )

            if not segment_content:
                continue

            virtual_chunk = dict(
                chunk
            )

            virtual_chunk[
                "section_number"
            ] = match["number"]

            virtual_chunk[
                "section_title"
            ] = match["title"]

            virtual_chunk[
                "parent_section_number"
            ] = None

            virtual_chunk[
                "parent_section_title"
            ] = None

            virtual_chunk[
                "content"
            ] = segment_content

            virtual_chunk[
                "_virtual_summary_segment"
            ] = True

            output.append(
                virtual_chunk
            )

    return output

def group_summary_chunks_by_major_section(
    chunks: list[dict],
) -> list[dict]:
    """
    Group summary chunks by major document section.

    Generic logic:
    - uses section hierarchy
    - rejects obvious OCR/body-text headings
    - resolves duplicate major section numbers
    - preserves document order
    """

    if not chunks:
        return []
    
    chunks = (
        split_summary_chunks_by_major_boundaries(
            chunks
        )
    )

    def is_good_major_heading(
        section_number: str,
        section_title: str,
    ) -> bool:

        number = (
            section_number
            or ""
        ).strip()

        title = (
            section_title
            or ""
        ).strip()

        if not number or not title:
            return False

        # Major sections should normally be whole
        # numbers: 1, 2, 3, 10, 13, etc.
        if not number.isdigit():
            return False

        # Body paragraphs accidentally detected as
        # headings are usually long.
        if len(title) > 80:
            return False

        words = title.split()

        # Major headings should normally be short.
        if len(words) > 12:
            return False

        # Reject sentence-like text.
        if title.endswith((".", ",", ";")):
            return False

        return True


    def heading_score(
        title: str,
    ) -> int:
        """
        Rank competing headings that share the
        same major section number.
        """

        value = (
            title
            or ""
        ).strip()

        if not value:
            return -100

        score = 0

        word_count = len(
            value.split()
        )

        # Concise headings are preferable.
        if 2 <= word_count <= 10:
            score += 20

        if len(value) <= 60:
            score += 10

        # Uppercase headings are common in policies.
        letters = [
            char
            for char in value
            if char.isalpha()
        ]

        if letters:

            uppercase_ratio = (
                sum(
                    1
                    for char in letters
                    if char.isupper()
                )
                / len(letters)
            )

            if uppercase_ratio >= 0.70:
                score += 20

        # Sentence-like text is less likely to be
        # a real major heading.
        if len(value) > 80:
            score -= 50

        if word_count > 12:
            score -= 40

        return score
    def extract_heading_number(
        title: str,
    ) -> str | None:
        """
        Extract an explicit major section number
        appearing at the beginning of a heading.

        Examples:
            "6. CREDIT DECISION" -> "6"
            "10 LOAN COLLECTION" -> "10"
            "CREDIT DECISION" -> None
        """

        import re

        value = (
            title
            or ""
        ).strip()

        match = re.match(
            r"^(\d+)\s*[\.\)\-:]?\s+",
            value,
        )

        if not match:
            return None

        return match.group(1)
    
    def recover_group_title_from_content(
        content: str,
        major_number: str,
    ) -> str | None:

        import re

        text = str(
            content
            or ""
        )

        if not text or not major_number:
            return None
        
        # -------------------------------------------------
        # Prefer explicit chapter headings.
        #
        # Examples:
        # CHAPTER FOUR: AUTHORITIES AND RESPONSIBILITIES
        # CHAPTER 4: AUTHORITIES AND RESPONSIBILITIES
        # -------------------------------------------------

        number_words = {
            "1": "ONE",
            "2": "TWO",
            "3": "THREE",
            "4": "FOUR",
            "5": "FIVE",
            "6": "SIX",
            "7": "SEVEN",
            "8": "EIGHT",
            "9": "NINE",
            "10": "TEN",
            "11": "ELEVEN",
            "12": "TWELVE",
            "13": "THIRTEEN",
            "14": "FOURTEEN",
            "15": "FIFTEEN",
            "16": "SIXTEEN",
            "17": "SEVENTEEN",
            "18": "EIGHTEEN",
            "19": "NINETEEN",
            "20": "TWENTY",
        }

        chapter_word = number_words.get(
            str(major_number)
        )

        chapter_patterns = [
            rf"(?im)^\s*CHAPTER\s+"
            rf"{re.escape(str(major_number))}"
            rf"\s*[:\.\-]?\s*"
            rf"([^\n]{{2,100}})\s*$",
        ]

        if chapter_word:
            chapter_patterns.append(
                rf"(?im)^\s*CHAPTER\s+"
                rf"{chapter_word}"
                rf"\s*[:\.\-]?\s*"
                rf"([^\n]{{2,100}})\s*$"
            )

        for pattern in chapter_patterns:

            chapter_match = re.search(
                pattern,
                text,
            )

            if chapter_match:

                chapter_title = (
                    chapter_match.group(1)
                    .strip()
                )

                if (
                    chapter_title
                    and len(
                        chapter_title.split()
                    ) <= 14
                ):
                    return chapter_title

        # Prefer an exact major heading:
        # 2. Main Policy Statements
        major_match = re.search(
            rf"(?m)^\s*"
            rf"{re.escape(major_number)}"
            rf"\s*[\.\)\-:]"
            rf"\s+"
            rf"([^\n]{{2,100}})"
            rf"\s*$",
            text,
        )

        if major_match:

            title = (
                major_match.group(1)
                .strip()
            )

            if (
                title
                and len(title.split()) <= 14
            ):
                return title

        # Otherwise use the first child heading:
        # 1.4 Governing Rules
        # 3.14 IFB Portfolio Management
        # 4.1 Board of Directors
        child_match = re.search(
            rf"(?m)^\s*"
            rf"{re.escape(major_number)}"
            rf"\.\d+"
            rf"(?:\.\d+)*"
            rf"\.?\s+"
            rf"([^\n]{{2,100}})"
            rf"\s*$",
            text,
        )

        if not child_match:
            return None

        title = (
            child_match.group(1)
            .strip()
        )

        if (
            not title
            or len(title.split()) > 14
        ):
            return None

        return title
    
    def extract_major_from_content(
        content: str,
    ) -> str | None:
        """
        Recover a major section number from OCR body text
        when section metadata is unreliable.

        Only hierarchical numbers are trusted:
            1.3.2 -> 1
            3.14  -> 3
            4.6.1 -> 4

        Plain list numbers such as "13." are deliberately
        ignored to avoid confusing paragraph numbering
        with major document sections.
        """

        import re

        value = str(
            content
            or ""
        )

        if not value:
            return None

        # Examine the beginning of the chunk only.
        sample = value[:1200]

        match = re.search(
            r"(?m)^\s*"
            r"(\d+)"
            r"\.\d+"
            r"(?:\.\d+)*"
            r"[\.\)]?"
            r"\s+",
            sample,
        )

        if not match:
            return None

        return match.group(1)

    groups = []
    group_map = {}

    for chunk in chunks:

        section_number = str(
            chunk.get("section_number")
            or ""
        ).strip()

        section_title = str(
            chunk.get("section_title")
            or ""
        ).strip()

        parent_number = str(
            chunk.get("parent_section_number")
            or ""
        ).strip()

        parent_title = str(
            chunk.get("parent_section_title")
            or ""
        ).strip()
        
        content = str(
            chunk.get("content")
            or ""
        )

        # -----------------------------------------
        # Determine major number
        # -----------------------------------------

        major_number = ""

        if section_number:

            cleaned = (
                section_number
                .replace(" ", "")
                .strip(".")
            )

            first_part = (
                cleaned.split(".")[0]
            )

            if first_part.isdigit():
                major_number = first_part
                
            # -----------------------------------------
            # Correct obvious OCR/parser numbering drift.
            #
            # If a major heading explicitly begins with
            # another section number, prefer that number.
            #
            # Example:
            # stored section_number = "7"
            # title = "6. CREDIT DECISION"
            # -> major section = "6"
            # -----------------------------------------

            if (
                section_number.isdigit()
                and section_title
            ):

                title_number = (
                    extract_heading_number(
                        section_title
                    )
                )

                if (
                    title_number
                    and title_number != major_number
                ):
                    major_number = title_number

        if (
            not major_number
            and parent_number
        ):

            cleaned_parent = (
                parent_number
                .replace(" ", "")
                .strip(".")
            )

            first_parent = (
                cleaned_parent.split(".")[0]
            )

            if first_parent.isdigit():
                major_number = (
                    first_parent
                )
        # -----------------------------------------
        # Recover from OCR body when heading metadata
        # appears weak or malformed.
        #
        # Example:
        # section_number = "4"
        # section_title  = "Za ip"
        # content begins with "3.14.1 ..."
        # -> logical major section = 3
        # -----------------------------------------

        content_major = (
            extract_major_from_content(
                content
            )
        )

        current_title_score = (
            heading_score(
                section_title
            )
        )

        weak_heading = (
            not section_title
            or current_title_score < 20
            or len(section_title) <= 5
        )

        if (
            content_major
            and weak_heading
        ):
            major_number = (
                content_major
            )
    
        # -----------------------------------------
        # Determine candidate major title
        # -----------------------------------------

        candidate_title = (
            section_title
        )
        
        # -----------------------------------------
        # Recover a usable title from OCR content
        # when stored metadata is weak.
        # -----------------------------------------

        candidate_score = (
            heading_score(
                candidate_title
            )
        )

        candidate_is_weak = (
            not candidate_title
            or candidate_score < 20
            or len(candidate_title.strip()) <= 5
        )

        if (
            major_number
            and candidate_is_weak
        ):

            recovered_title = (
                recover_group_title_from_content(
                    content=content,
                    major_number=major_number,
                )
            )

            if recovered_title:
                candidate_title = (
                    recovered_title
                )

        title_number = (
            extract_heading_number(
                candidate_title
            )
        )

        if title_number:

            import re

            candidate_title = re.sub(
                r"^\d+\s*[\.\)\-:]?\s+",
                "",
                candidate_title,
                count=1,
            ).strip()

        if (
            "." in section_number
            and parent_title
        ):
            candidate_title = (
                parent_title
            )

        # -----------------------------------------
        # Unnumbered introduction/content
        # -----------------------------------------

        if not major_number:

            group_key = (
                f"unnumbered:"
                f"{candidate_title.lower()}"
            )

        else:

            group_key = (
                f"section:{major_number}"
            )

        # -----------------------------------------
        # Create the group
        # -----------------------------------------

        if group_key not in group_map:

            group = {
                "major_section_number": (
                    major_number
                    or None
                ),
                "major_section_title": (
                    candidate_title
                    or "Unnumbered"
                ),
                "chunks": [],
            }

            group_map[group_key] = group
            groups.append(group)

        group = group_map[group_key]

        group["chunks"].append(
            chunk
        )
        
        # -----------------------------------------
        # Promote a recovered candidate title when
        # it is better than the group's current OCR
        # title.
        # -----------------------------------------

        if (
            major_number
            and candidate_title
        ):

            current_group_title = str(
                group.get(
                    "major_section_title"
                )
                or ""
            ).strip()

            candidate_title_score = (
                heading_score(
                    candidate_title
                )
            )

            current_group_score = (
                heading_score(
                    current_group_title
                )
            )

            current_group_is_weak = (
                not current_group_title
                or current_group_score < 20
                or len(
                    current_group_title
                ) <= 5
            )

            candidate_is_better = (
                candidate_title_score
                >
                current_group_score
            )

            if (
                current_group_is_weak
                or candidate_is_better
            ):
                group[
                    "major_section_title"
                ] = candidate_title

        # -----------------------------------------
        # Improve the group title when we encounter
        # a stronger genuine major heading.
        # -----------------------------------------

        if (
            major_number
            and is_good_major_heading(
                section_number,
                section_title,
            )
        ):

            current_title = (
                group[
                    "major_section_title"
                ]
            )

            if (
                heading_score(
                    section_title
                )
                >
                heading_score(
                    current_title
                )
            ):

                clean_title = section_title

                if extract_heading_number(
                    clean_title
                ):
                    import re

                    clean_title = re.sub(
                        r"^\d+\s*[\.\)\-:]?\s+",
                        "",
                        clean_title,
                        count=1,
                    ).strip()

                group[
                    "major_section_title"
                ] = clean_title

            # -------------------------------------------------
    # Preserve logical document section order
    # -------------------------------------------------

    def group_sort_key(group):

        number = group.get(
            "major_section_number"
        )

        # Keep unnumbered introductory material first.
        if number is None:
            return (0, 0)

        try:
            return (
                1,
                int(number),
            )

        except (
            TypeError,
            ValueError,
        ):
            return (
                2,
                999999,
            )

    groups.sort(
        key=group_sort_key
    )

    return groups

def build_summary_group_evidence(
    group: dict,
    max_chars: int = 1800,
) -> str:
    """
    Build compact evidence for one major document
    section.

    Generic:
    - works with any document
    - preserves subsection information
    - keeps the prompt small
    - distributes available space across chunks
    """

    chunks = group.get("chunks") or []

    if not chunks:
        return ""

    major_number = (
        group.get("major_section_number")
        or ""
    )

    major_title = (
        group.get("major_section_title")
        or "Document Section"
    )

    header = (
        f"MAJOR SECTION: "
        f"{major_number} {major_title}\n"
    ).strip()

    # Leave space for metadata and separators.
    available_chars = max(
        500,
        max_chars - len(header) - 100,
    )

    per_chunk_budget = max(
        180,
        available_chars // len(chunks),
    )

    blocks = []

    for chunk in chunks:

        section_number = str(
            chunk.get("section_number")
            or ""
        ).strip()

        section_title = str(
            chunk.get("section_title")
            or ""
        ).strip()

        content = str(
            chunk.get("content")
            or ""
        ).strip()

        content = content[
            :per_chunk_budget
        ]

        block = (
            f"{section_number} "
            f"{section_title}\n"
            f"{content}"
        ).strip()

        blocks.append(block)

    evidence = (
        header
        + "\n\n"
        + "\n\n".join(blocks)
    )

    return evidence[:max_chars]

def retrieve_cached_document_summary_chunks(
    database,
    document_index_id: int,
    max_chunks: int = 24,
) -> list[dict]:
    """
    Select a balanced set of chunks for whole-document
    summarization.

    The goal is to represent the document structure
    without sending every cached chunk to the LLM.

    Selection strategy:
    1. Load all chunks for the document.
    2. Prefer major/top-level sections.
    3. Include important child sections.
    4. Avoid duplicate sections.
    5. Preserve original document order.
    6. Respect max_chunks.
    """

    

    chunks = (
        database.query(DocumentChunk)
        .filter(
            DocumentChunk.document_index_id
            == document_index_id
        )
        .order_by(
            DocumentChunk.chunk_order.asc()
        )
        .all()
    )

    if not chunks:
        return []

    def to_dict(chunk) -> dict:
        return {
            "id": chunk.id,
            "document_index_id":
                chunk.document_index_id,
            "chunk_order":
                chunk.chunk_order,
            "section_number":
                chunk.section_number,
            "section_title":
                chunk.section_title,
            "parent_section_number":
                chunk.parent_section_number,
            "parent_section_title":
                chunk.parent_section_title,
            "page_number":
                chunk.page_number,
            "content":
                chunk.content,
        }

    selected = []
    selected_ids = set()
    selected_sections = set()
    
    # --------------------------------------------------------
    # PASS 0
    # Preserve chunks containing explicit major chapter
    # headings before applying normal summary selection.
    #
    # This protects major sections near the end of long
    # documents from being lost because of max_chunks.
    #
    # Supports common OCR variation:
    # CHAPTER SIX: ...
    # CHAPTER 6: ...
    # CAHPTER 5: ...
    # --------------------------------------------------------

    import re

    chapter_heading_pattern = re.compile(
        r"(?im)^"
        r"\s*(?:CHAPTER|CAHPTER)\s+"
        r"(?:"
        r"ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|"
        r"EIGHT|NINE|TEN|ELEVEN|TWELVE|THIRTEEN|"
        r"FOURTEEN|FIFTEEN|SIXTEEN|SEVENTEEN|"
        r"EIGHTEEN|NINETEEN|TWENTY|"
        r"\d{1,3}"
        r")"
        r"\s*[:\.\-]?"
        r"\s+"
        r"[^\n]{2,100}"
        r"\s*$"
    )

    for chunk in chunks:

        content = str(
            chunk.content
            or ""
        )

        if not chapter_heading_pattern.search(
            content
        ):
            continue

        if chunk.id in selected_ids:
            continue

        selected.append(
            to_dict(chunk)
        )

        selected_ids.add(
            chunk.id
        )

        # Keep the metadata key too so later passes
        # do not unnecessarily reselect the same
        # structural metadata group.
        section_key = (
            (
                chunk.section_number
                or ""
            ).strip().lower(),
            (
                chunk.section_title
                or ""
            ).strip().lower(),
        )

        selected_sections.add(
            section_key
        )

        if len(selected) >= max_chunks:
            break

    # --------------------------------------------------------
    # PASS 1
    # Major/top-level sections.
    # --------------------------------------------------------

    for chunk in chunks:

        section_number = (
            chunk.section_number or ""
        ).strip()

        section_title = (
            chunk.section_title or ""
        ).strip()

        parent_number = (
            chunk.parent_section_number
            or ""
        ).strip()

        if not section_number:
            continue

        # Major section examples:
        # 1
        # 2
        # 3
        # 4
        #
        # Also allow structural headings with
        # no parent.
        is_top_level = (
            "." not in section_number
            or not parent_number
        )

        if not is_top_level:
            continue

        section_key = (
            section_number.lower(),
            section_title.lower(),
        )

        if section_key in selected_sections:
            continue

        selected.append(
            to_dict(chunk)
        )

        selected_ids.add(
            chunk.id
        )

        selected_sections.add(
            section_key
        )

        if len(selected) >= max_chunks:
            break

    # --------------------------------------------------------
    # PASS 2
    # Important child sections.
    #
    # This gives the summarizer enough detail to understand
    # the contents inside large top-level sections.
    # --------------------------------------------------------

    if len(selected) < max_chunks:

        priority_terms = [
            "introduction",
            "background",
            "purpose",
            "objective",
            "objectives",
            "scope",
            "definition",
            "definitions",
            "principle",
            "principles",
            "policy",
            "governance",
            "responsibility",
            "responsibilities",
            "authority",
            "authorities",
            "requirement",
            "requirements",
            "procedure",
            "procedures",
            "guideline",
            "guidelines",
            "risk",
            "risks",
            "control",
            "controls",
            "compliance",
            "monitoring",
            "reporting",
            "violation",
            "revision",
            "exception",
            "exceptions",
        ]

        for chunk in chunks:

            if chunk.id in selected_ids:
                continue

            section_title = (
                chunk.section_title or ""
            ).strip()

            parent_title = (
                chunk.parent_section_title
                or ""
            ).strip()

            searchable = (
                section_title
                + " "
                + parent_title
            ).lower()

            if not any(
                term in searchable
                for term in priority_terms
            ):
                continue

            section_key = (
                (
                    chunk.section_number
                    or ""
                ).lower(),
                section_title.lower(),
            )

            if (
                section_key
                in selected_sections
            ):
                continue

            selected.append(
                to_dict(chunk)
            )

            selected_ids.add(
                chunk.id
            )

            selected_sections.add(
                section_key
            )

            if (
                len(selected)
                >= max_chunks
            ):
                break

    # --------------------------------------------------------
    # PASS 3
    # Fill remaining capacity with evenly distributed chunks.
    #
    # This prevents long documents from being summarized only
    # from their opening sections.
    # --------------------------------------------------------

    remaining_slots = (
        max_chunks
        - len(selected)
    )

    if remaining_slots > 0:

        remaining = [
            chunk
            for chunk in chunks
            if chunk.id
            not in selected_ids
        ]

        if remaining:

            step = max(
                1,
                len(remaining)
                // remaining_slots
            )

            for index in range(
                0,
                len(remaining),
                step
            ):

                chunk = remaining[index]

                selected.append(
                    to_dict(chunk)
                )

                selected_ids.add(
                    chunk.id
                )

                if (
                    len(selected)
                    >= max_chunks
                ):
                    break

    # --------------------------------------------------------
    # Restore original document order.
    # --------------------------------------------------------

    selected.sort(
        key=lambda item: (
            item.get(
                "chunk_order"
            )
            or 0
        )
    )

    return selected

def retrieve_cached_matching_section(
    database: Session,
    document_index_id: int,
    requested_section: str,
) -> list[dict]:
    """
    Find the best matching section in any cached document
    and return that section plus all of its descendants.

    Examples:
        requested_section = "purpose"

    Can match titles such as:
        Purpose
        Purpose of the Policy
        Policy Purpose
        Purpose and Objectives
    """

    chunks = get_cached_chunks(
        database=database,
        document_index_id=document_index_id,
    )

    if not chunks:
        return []

    requested = (
        " ".join(
            (requested_section or "")
            .lower()
            .strip()
            .split()
        )
    )

    if not requested:
        return []

    # ==========================================
    # Generic section concept aliases
    # ==========================================

    section_aliases = {

        "purpose": {
            "purpose",
            "purposes",
            "objective",
            "objectives",
            "aim",
            "aims",
            "goal",
            "goals",
        },

        "objective": {
            "objective",
            "objectives",
            "purpose",
            "purposes",
            "aim",
            "aims",
            "goal",
            "goals",
        },

        "objectives": {
            "objective",
            "objectives",
            "purpose",
            "purposes",
            "aim",
            "aims",
            "goal",
            "goals",
        },

        "scope": {
            "scope",
            "scope of application",
            "applicability",
            "application",
            "coverage",
        },

        "definitions": {
            "definition",
            "definitions",
            "definitions of terms",
            "terminology",
        },

        "principles": {
            "principle",
            "principles",
            "guiding principles",
        },

        "governance": {
            "governance",
            "governance framework",
            "oversight",
        },

        "roles and responsibilities": {
            "roles and responsibilities",
            "role and responsibility",
            "authority and responsibility",
            "authorities and responsibilities",
            "responsibility",
            "responsibilities",
            "roles",
            "duties",
        },

        "authorities and responsibilities": {
            "authority and responsibility",
            "authorities and responsibilities",
            "roles and responsibilities",
            "responsibility",
            "responsibilities",
            "duties",
        },

        "procedures": {
            "procedure",
            "procedures",
            "process",
            "processes",
        },

        "requirements": {
            "requirement",
            "requirements",
            "mandatory requirements",
        },

        "guidelines": {
            "guideline",
            "guidelines",
            "guidance",
        },

        "exceptions": {
            "exception",
            "exceptions",
            "exemption",
            "exemptions",
        },

        "compliance": {
            "compliance",
            "regulatory compliance",
            "policy compliance",
        },

        "monitoring": {
            "monitoring",
            "monitoring and evaluation",
            "evaluation",
            "oversight",
        },

        "reporting": {
            "reporting",
            "report",
            "reports",
        },
    }

    requested_variants = (
        section_aliases.get(
            requested,
            {requested},
        )
    )

    candidates = []

    for chunk in chunks:

        section_number = (
            chunk.get("section_number")
            or ""
        )

        section_title = (
            chunk.get("section_title")
            or ""
        )

        normalized_title = (
            " ".join(
                section_title
                .lower()
                .strip()
                .split()
            )
        )

        if (
            not section_number
            or not normalized_title
        ):
            continue

        title_words = {
            word
            for word in normalized_title.split()
            if len(word) > 2
        }

        score = 0.0

        for variant in requested_variants:

            normalized_variant = (
                " ".join(
                    variant
                    .lower()
                    .strip()
                    .split()
                )
            )

            if not normalized_variant:
                continue

            variant_words = {
                word
                for word
                in normalized_variant.split()
                if len(word) > 2
            }

            variant_score = 0.0

            # Exact conceptual match.
            if (
                normalized_title
                == normalized_variant
            ):
                variant_score += 100

            # Variant appears in section title.
            elif (
                normalized_variant
                in normalized_title
            ):
                variant_score += 50

            # Section title appears in variant.
            elif (
                normalized_title
                in normalized_variant
            ):
                variant_score += 40

            overlap = (
                variant_words
                & title_words
            )

            variant_score += (
                len(overlap)
                * 10
            )

            if variant_words:

                coverage = (
                    len(overlap)
                    / len(variant_words)
                )

                variant_score += (
                    coverage
                    * 20
                )

            score = max(
                score,
                variant_score,
            )

        if score > 0:

            candidates.append(
                {
                    "score": score,
                    "section_number":
                        section_number,
                    "section_title":
                        section_title,
                }
            )

    if not candidates:
        return []

    candidates.sort(
        key=lambda item:
            item["score"],
        reverse=True,
    )

    best = candidates[0]

    # Require a reasonable match.
    if best["score"] < 20:
        return []

    parent_number = (
        best["section_number"]
    )

    selected = []

    for chunk in chunks:

        section_number = (
            chunk.get("section_number")
            or ""
        )

        parent_section_number = (
            chunk.get(
                "parent_section_number"
            )
            or ""
        )

        include = False

        # Section itself.
        if (
            section_number
            == parent_number
        ):
            include = True

        # Direct child.
        elif (
            parent_section_number
            == parent_number
        ):
            include = True

        # Any nested descendant.
        elif section_number.startswith(
            parent_number + "."
        ):
            include = True

        if include:
            selected.append(
                dict(chunk)
            )

    def sort_key(chunk: dict):

        section_number = (
            chunk.get("section_number")
            or ""
        )

        chunk_order = (
            chunk.get("chunk_order")
            or 0
        )

        try:

            parts = tuple(
                int(part)
                for part
                in section_number.split(".")
            )

        except ValueError:

            parts = (
                999999,
            )

        return (
            parts,
            chunk_order,
        )

    selected.sort(
        key=sort_key
    )

    return selected

def get_ready_cached_document(
    database: Session,
    external_document_id: int,
) -> DocumentIndex | None:
    """
    Return a ready cached document only when it has
    indexed chunks available.
    """

    cached_document = (
        get_cached_document(
            database=database,
            external_document_id=(
                external_document_id
            ),
        )
    )

    if cached_document is None:
        return None

    if cached_document.status != "ready":
        return None

    chunk_exists = (
        database.query(
            DocumentChunk.id
        )
        .filter(
            DocumentChunk.document_index_id
            == cached_document.id
        )
        .first()
    )

    if chunk_exists is None:
        return None

    return cached_document