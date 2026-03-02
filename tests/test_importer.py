"""Unit tests for the importer module."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# _strip_html
# ---------------------------------------------------------------------------

def test_strip_html_removes_script_and_nav():
    from genai_tutor.importer import _strip_html

    html = """<html><head><script>alert(1)</script></head>
    <body>
    <nav>Navigation</nav>
    <p>Hello World</p>
    <footer>Footer text</footer>
    </body></html>"""
    result = _strip_html(html)
    assert "Hello World" in result
    assert "alert(1)" not in result
    assert "Navigation" not in result
    assert "Footer text" not in result


def test_strip_html_preserves_body_text():
    from genai_tutor.importer import _strip_html

    html = "<body><h1>Title</h1><p>Body paragraph.</p></body>"
    result = _strip_html(html)
    assert "Title" in result
    assert "Body paragraph." in result


def test_strip_html_empty():
    from genai_tutor.importer import _strip_html

    assert _strip_html("") == ""
    assert _strip_html("<script>x</script><style>y</style>") == ""


# ---------------------------------------------------------------------------
# extract_from_text
# ---------------------------------------------------------------------------

def test_extract_from_text_reads_file():
    from genai_tutor.importer import extract_from_text

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Hello, this is test content.")
        tmp = f.name
    try:
        result = extract_from_text(Path(tmp))
        assert result == "Hello, this is test content."
    finally:
        os.unlink(tmp)


def test_extract_from_text_file_not_found():
    from genai_tutor.importer import extract_from_text, ContentImportError

    with pytest.raises(ContentImportError, match="File not found"):
        extract_from_text(Path("/nonexistent/path/file.txt"))


def test_extract_from_text_empty_file():
    from genai_tutor.importer import extract_from_text, ContentImportError

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("")
        tmp = f.name
    try:
        with pytest.raises(ContentImportError, match="empty"):
            extract_from_text(Path(tmp))
    finally:
        os.unlink(tmp)


# ---------------------------------------------------------------------------
# extract_content routing
# ---------------------------------------------------------------------------

def test_extract_content_routes_text_file():
    from genai_tutor.importer import extract_content

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Some text content here.")
        tmp = f.name
    try:
        text, ref = extract_content(tmp)
        assert "Some text content here." in text
        assert ref == tmp
    finally:
        os.unlink(tmp)


def test_extract_content_routes_url_mock():
    from genai_tutor.importer import extract_content

    fake_response = MagicMock()
    fake_response.read.return_value = b"<html><body><p>Web content</p></body></html>"
    fake_response.headers.get_content_charset.return_value = "utf-8"
    fake_response.__enter__ = lambda s: s
    fake_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=fake_response):
        text, ref = extract_content("https://example.com/page")
    assert "Web content" in text
    assert ref == "https://example.com/page"


def test_extract_content_json_raises_value_error():
    from genai_tutor.importer import extract_content

    with pytest.raises(ValueError, match="json"):
        extract_content("/some/path/pack.json")


# ---------------------------------------------------------------------------
# parse_json_pack
# ---------------------------------------------------------------------------

def test_parse_json_pack_valid():
    from genai_tutor.importer import parse_json_pack

    pack = [
        {"domain_id": 1, "subtopic_id": 2, "title": "T1", "content": "Body 1"},
        {"domain_id": 2, "subtopic_id": 3, "title": "T2", "content": "Body 2"},
    ]
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(pack, f)
        tmp = f.name
    try:
        records = parse_json_pack(Path(tmp))
        assert len(records) == 2
        assert records[0]["title"] == "T1"
    finally:
        os.unlink(tmp)


def test_parse_json_pack_missing_fields():
    from genai_tutor.importer import parse_json_pack, ContentImportError

    pack = [{"domain_id": 1, "title": "T1"}]  # missing subtopic_id + content
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(pack, f)
        tmp = f.name
    try:
        with pytest.raises(ContentImportError, match="missing required fields"):
            parse_json_pack(Path(tmp))
    finally:
        os.unlink(tmp)


def test_parse_json_pack_not_a_list():
    from genai_tutor.importer import parse_json_pack, ContentImportError

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump({"key": "value"}, f)
        tmp = f.name
    try:
        with pytest.raises(ContentImportError, match="must be a list"):
            parse_json_pack(Path(tmp))
    finally:
        os.unlink(tmp)


# ---------------------------------------------------------------------------
# DB round-trip: save + retrieve + delete
# ---------------------------------------------------------------------------

def _patch_db(tmpdir: str):
    """Return a context manager that redirects DB to a temp directory."""
    import pathlib
    db_path = os.path.join(tmpdir, "test.db")
    return (
        patch("genai_tutor.db.DB_DIR", pathlib.Path(tmpdir)),
        patch("genai_tutor.db.DB_PATH", pathlib.Path(db_path)),
    )


def test_save_and_retrieve_imported_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_patch, path_patch = _patch_db(tmpdir)
        with db_patch, path_patch:
            from genai_tutor.db import init_db
            # Need seeded domain + subtopic rows for FK constraints
            from genai_tutor.db import get_connection
            init_db()
            with get_connection() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO domains (id, name, section_number, exam_weight, description)"
                    " VALUES (1, 'Domain One', 1, 30.0, 'Desc')"
                )
                conn.execute(
                    "INSERT OR IGNORE INTO subtopics (id, name, domain_id, description)"
                    " VALUES (10, 'Subtopic A', 1, 'Sub desc')"
                )

            from genai_tutor.importer import save_imported_content, get_imported_for_domain_subtopic
            new_id = save_imported_content(
                title="Test Article",
                source_ref="https://example.com/article",
                domain_id=1,
                subtopic_id=10,
                content="This is the article body.",
            )
            assert isinstance(new_id, int)
            assert new_id > 0

            records = get_imported_for_domain_subtopic(1, 10)
            assert len(records) == 1
            assert records[0].title == "Test Article"
            assert records[0].content == "This is the article body."
            assert records[0].id == new_id


def test_delete_imported_content_existing():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_patch, path_patch = _patch_db(tmpdir)
        with db_patch, path_patch:
            from genai_tutor.db import init_db, get_connection
            init_db()
            with get_connection() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO domains (id, name, section_number, exam_weight, description)"
                    " VALUES (1, 'Domain One', 1, 30.0, 'Desc')"
                )
                conn.execute(
                    "INSERT OR IGNORE INTO subtopics (id, name, domain_id, description)"
                    " VALUES (10, 'Subtopic A', 1, 'Sub desc')"
                )

            from genai_tutor.importer import save_imported_content, delete_imported_content
            new_id = save_imported_content("Del Test", "src", 1, 10, "body")
            assert delete_imported_content(new_id) is True


def test_delete_imported_content_missing():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_patch, path_patch = _patch_db(tmpdir)
        with db_patch, path_patch:
            from genai_tutor.db import init_db
            init_db()
            from genai_tutor.importer import delete_imported_content
            assert delete_imported_content(99999) is False


# ---------------------------------------------------------------------------
# Optional-dep guard tests
# ---------------------------------------------------------------------------

def test_extract_from_pdf_no_pypdf():
    from genai_tutor.importer import ContentImportError

    with patch("genai_tutor.importer._PYPDF_AVAILABLE", False):
        from genai_tutor import importer
        with pytest.raises(ContentImportError, match="pypdf"):
            importer.extract_from_pdf(Path("dummy.pdf"))


def test_extract_from_docx_no_docx():
    from genai_tutor.importer import ContentImportError

    with patch("genai_tutor.importer._DOCX_AVAILABLE", False):
        from genai_tutor import importer
        with pytest.raises(ContentImportError, match="python-docx"):
            importer.extract_from_docx(Path("dummy.docx"))


# ---------------------------------------------------------------------------
# Needed import at module level
# ---------------------------------------------------------------------------

import pytest
