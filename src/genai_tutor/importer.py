"""Content import utilities: extraction from URLs, PDFs, DOCX, text, and JSON packs."""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

try:
    import pypdf  # type: ignore
    _PYPDF_AVAILABLE = True
except ImportError:
    _PYPDF_AVAILABLE = False

try:
    import docx  # type: ignore
    _DOCX_AVAILABLE = True
except ImportError:
    _DOCX_AVAILABLE = False

from genai_tutor.db import get_connection
from genai_tutor.models import ImportedContent


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ContentImportError(Exception):
    """Raised when content cannot be extracted or is invalid."""


# ---------------------------------------------------------------------------
# HTML stripping
# ---------------------------------------------------------------------------

class _HTMLStripper(HTMLParser):
    """Minimal HTML → plain-text converter using stdlib only."""

    _SKIP_TAGS = {"script", "style", "nav", "header", "footer", "aside"}

    def __init__(self) -> None:
        super().__init__()
        self._skip_depth: int = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self._parts.append(stripped)

    def get_text(self) -> str:
        return "\n".join(self._parts)


def _strip_html(html: str) -> str:
    """Return plain text extracted from an HTML string."""
    stripper = _HTMLStripper()
    stripper.feed(html)
    return stripper.get_text()


# ---------------------------------------------------------------------------
# Extraction functions
# ---------------------------------------------------------------------------

def extract_from_url(url: str, timeout: int = 15) -> str:
    """Fetch *url* and return its plain-text body.

    Raises:
        ContentImportError: on HTTP/network errors or if the result is empty.
    """
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "genai-tutor/1.0 (content importer)"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw_bytes = response.read()
            charset = response.headers.get_content_charset("utf-8") or "utf-8"
            html = raw_bytes.decode(charset, errors="replace")
    except urllib.error.HTTPError as exc:
        raise ContentImportError(f"HTTP {exc.code} fetching {url}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise ContentImportError(f"Network error fetching {url}: {exc.reason}") from exc
    except Exception as exc:
        raise ContentImportError(f"Failed to fetch {url}: {exc}") from exc

    text = _strip_html(html)
    if not text.strip():
        raise ContentImportError(f"No text content found at {url}")
    return text


def extract_from_pdf(path: Path) -> str:
    """Extract text from a PDF file.

    Raises:
        ContentImportError: if pypdf is not installed, the file doesn't exist,
                            or no text could be extracted.
    """
    if not _PYPDF_AVAILABLE:
        raise ContentImportError(
            "pypdf is required to import PDF files. "
            "Install it with: pip install 'pypdf>=4.0.0'"
        )
    if not path.exists():
        raise ContentImportError(f"File not found: {path}")
    try:
        reader = pypdf.PdfReader(str(path))
        pages_text = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages_text).strip()
    except Exception as exc:
        raise ContentImportError(f"Failed to read PDF {path}: {exc}") from exc

    if not text:
        raise ContentImportError(f"No text could be extracted from PDF: {path}")
    return text


def extract_from_docx(path: Path) -> str:
    """Extract text from a DOCX file.

    Raises:
        ContentImportError: if python-docx is not installed, file is missing,
                            or no text could be extracted.
    """
    if not _DOCX_AVAILABLE:
        raise ContentImportError(
            "python-docx is required to import DOCX files. "
            "Install it with: pip install 'python-docx>=1.1.0'"
        )
    if not path.exists():
        raise ContentImportError(f"File not found: {path}")
    try:
        document = docx.Document(str(path))
        paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
        text = "\n".join(paragraphs).strip()
    except Exception as exc:
        raise ContentImportError(f"Failed to read DOCX {path}: {exc}") from exc

    if not text:
        raise ContentImportError(f"No text could be extracted from DOCX: {path}")
    return text


def extract_from_text(path: Path) -> str:
    """Read a plain-text file, trying common encodings.

    Raises:
        ContentImportError: if the file is not found or cannot be decoded.
    """
    if not path.exists():
        raise ContentImportError(f"File not found: {path}")
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            text = path.read_text(encoding=encoding).strip()
            if text:
                return text
            # File exists but is empty
            raise ContentImportError(f"File is empty: {path}")
        except UnicodeDecodeError:
            continue
        except ContentImportError:
            raise
        except Exception as exc:
            raise ContentImportError(f"Failed to read {path}: {exc}") from exc
    raise ContentImportError(f"Could not decode {path} with any supported encoding")


def extract_content(source: str) -> tuple[str, str]:
    """Route *source* to the appropriate extractor.

    Returns:
        (text, source_ref) tuple.

    Raises:
        ValueError("json"): for .json file paths — caller should handle JSON pack logic.
        ContentImportError: on extraction failure.
    """
    if source.startswith(("http://", "https://")):
        text = extract_from_url(source)
        return text, source

    path = Path(source)
    suffix = path.suffix.lower()

    if suffix == ".json":
        raise ValueError("json")
    elif suffix == ".pdf":
        text = extract_from_pdf(path)
    elif suffix == ".docx":
        text = extract_from_docx(path)
    else:
        text = extract_from_text(path)

    return text, str(path)


# ---------------------------------------------------------------------------
# JSON content-pack parsing
# ---------------------------------------------------------------------------

def parse_json_pack(path: Path) -> list[dict]:
    """Parse a JSON content pack file.

    Expected format: a JSON array of objects, each containing:
        domain_id   (int)
        subtopic_id (int)
        title       (str)
        content     (str)

    Raises:
        ContentImportError: if the file is missing, not valid JSON, not a list,
                            or any record is missing required fields.
    """
    if not path.exists():
        raise ContentImportError(f"File not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContentImportError(f"Invalid JSON in {path}: {exc}") from exc
    except Exception as exc:
        raise ContentImportError(f"Failed to read {path}: {exc}") from exc

    if not isinstance(data, list):
        raise ContentImportError(f"JSON content pack must be a list, got {type(data).__name__}")

    required_fields = {"domain_id", "subtopic_id", "title", "content"}
    records: list[dict] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ContentImportError(f"Record {i} is not an object")
        missing = required_fields - item.keys()
        if missing:
            raise ContentImportError(
                f"Record {i} is missing required fields: {', '.join(sorted(missing))}"
            )
        records.append(item)

    return records


# ---------------------------------------------------------------------------
# Database functions
# ---------------------------------------------------------------------------

def save_imported_content(
    title: str,
    source_ref: str,
    domain_id: int,
    subtopic_id: int,
    content: str,
) -> int:
    """Persist an imported content record and return its new ID."""
    imported_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO imported_content
               (title, source_ref, domain_id, subtopic_id, content, imported_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (title, source_ref, domain_id, subtopic_id, content, imported_at),
        )
        return cursor.lastrowid  # type: ignore[return-value]


def get_imported_for_domain_subtopic(
    domain_id: int, subtopic_id: int
) -> list[ImportedContent]:
    """Return all imported content records matching the given domain and subtopic."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, title, source_ref, domain_id, subtopic_id, content, imported_at
               FROM imported_content
               WHERE domain_id = ? AND subtopic_id = ?
               ORDER BY imported_at DESC""",
            (domain_id, subtopic_id),
        ).fetchall()
    return [
        ImportedContent(
            id=r["id"],
            title=r["title"],
            source_ref=r["source_ref"],
            domain_id=r["domain_id"],
            subtopic_id=r["subtopic_id"],
            content=r["content"],
            imported_at=r["imported_at"],
        )
        for r in rows
    ]


def get_all_imported_content() -> list[dict]:
    """Return all imported content with domain and subtopic names."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT ic.id, ic.title, ic.source_ref, ic.domain_id, ic.subtopic_id,
                      ic.content, ic.imported_at,
                      d.name AS domain_name, s.name AS subtopic_name
               FROM imported_content ic
               JOIN domains d ON ic.domain_id = d.id
               JOIN subtopics s ON ic.subtopic_id = s.id
               ORDER BY ic.imported_at DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


def delete_imported_content(record_id: int) -> bool:
    """Delete an imported content record by ID. Returns True if a row was deleted."""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM imported_content WHERE id = ?", (record_id,)
        )
        return cursor.rowcount > 0
