from pathlib import (
    Path,
)

from pypdf import (
    PdfReader,
)

from pdf2image import (
    convert_from_path,
)

import pytesseract


MINIMUM_USEFUL_CHARACTERS = 80


def clean_extracted_text(
    text: str,
) -> str:

    return "\n".join(
        line.strip()
        for line in (
            text
            or ""
        ).splitlines()
        if line.strip()
    )


def extract_native_pdf_pages(
    file_path: str,
) -> list[dict]:

    print(
        "DEBUG EXTRACT 1: OPEN PDF:",
        file_path,
        flush=True,
    )

    reader = PdfReader(
        file_path
    )

    print(
        "DEBUG EXTRACT 2: PDF OPENED, PAGES:",
        len(reader.pages),
        flush=True,
    )

    pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):

        print(
            f"DEBUG NATIVE PAGE {page_number}: START",
            flush=True,
        )

        try:

            raw_text = (
                page.extract_text()
                or ""
            )

        except Exception as error:

            print(
                f"DEBUG NATIVE PAGE {page_number}: ERROR:",
                type(error).__name__,
                str(error),
                flush=True,
            )

            raw_text = ""

        text = clean_extracted_text(
            raw_text
        )

        needs_ocr = (
            len(text)
            < MINIMUM_USEFUL_CHARACTERS
        )

        print(
            f"DEBUG NATIVE PAGE {page_number}: "
            f"{len(text)} chars | "
            f"OCR={needs_ocr}",
            flush=True,
        )

        pages.append(
            {
                "page_number":
                    page_number,

                "text":
                    text,

                "extraction_method":
                    "native",

                "needs_ocr":
                    needs_ocr,
            }
        )

    print(
        "DEBUG EXTRACT 3: NATIVE EXTRACTION COMPLETE",
        flush=True,
    )

    return pages


def ocr_pdf_page(
    file_path: str,
    page_number: int,
) -> str:

    print(
        f"DEBUG OCR PAGE {page_number}: RENDER START",
        flush=True,
    )

    images = convert_from_path(
        file_path,
        dpi=250,
        first_page=page_number,
        last_page=page_number,
        fmt="jpeg",
        thread_count=1,
    )

    print(
        f"DEBUG OCR PAGE {page_number}: RENDER COMPLETE",
        flush=True,
    )

    if not images:
        return ""

    image = images[0]

    print(
        f"DEBUG OCR PAGE {page_number}: TESSERACT START",
        flush=True,
    )

    raw_text = pytesseract.image_to_string(
        image,
        lang="eng",
        config="--psm 6",
    )

    print(
        f"DEBUG OCR PAGE {page_number}: TESSERACT COMPLETE",
        flush=True,
    )

    return clean_extracted_text(
        raw_text
    )


def extract_pdf_pages(
    file_path: str,
) -> list[dict]:

    print(
        "DEBUG PDF EXTRACTION: START",
        flush=True,
    )

    pages = extract_native_pdf_pages(
        file_path
    )

    print(
        "DEBUG PDF EXTRACTION: NATIVE PAGES:",
        len(pages),
        flush=True,
    )

    final_pages = []

    for page in pages:

        page_number = (
            page["page_number"]
        )

        if not page["needs_ocr"]:

            print(
                f"DEBUG PAGE {page_number}: "
                "USING NATIVE TEXT",
                flush=True,
            )

            final_pages.append(
                page
            )

            continue

        print(
            f"DEBUG PAGE {page_number}: "
            "OCR REQUIRED",
            flush=True,
        )

        try:

            ocr_text = ocr_pdf_page(
                file_path=file_path,
                page_number=page_number,
            )

        except Exception as error:

            print(
                f"DEBUG OCR PAGE {page_number}: ERROR:",
                type(error).__name__,
                str(error),
                flush=True,
            )

            final_pages.append(
                {
                    **page,
                    "ocr_error":
                        str(error),
                }
            )

            continue

        if (
            len(ocr_text)
            > len(page["text"])
        ):

            print(
                f"DEBUG PAGE {page_number}: "
                f"USING OCR "
                f"({len(ocr_text)} chars)",
                flush=True,
            )

            final_pages.append(
                {
                    "page_number":
                        page_number,

                    "text":
                        ocr_text,

                    "extraction_method":
                        "ocr",

                    "needs_ocr":
                        False,
                }
            )

        else:

            print(
                f"DEBUG PAGE {page_number}: "
                "KEEPING NATIVE TEXT",
                flush=True,
            )

            final_pages.append(
                page
            )

    print(
        "DEBUG PDF EXTRACTION: COMPLETE:",
        len(final_pages),
        "pages",
        flush=True,
    )

    return final_pages


def extract_document(
    file_path: str,
) -> list[dict]:

    extension = (
        Path(
            file_path
        ).suffix.lower()
    )

    if extension == ".pdf":

        return extract_pdf_pages(
            file_path
        )

    raise ValueError(
        f"Unsupported document type: "
        f"{extension}"
    )