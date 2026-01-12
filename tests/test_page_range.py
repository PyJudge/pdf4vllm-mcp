"""
Tests for start_page/end_page parameter handling in read_pdf and grep_pdf.

Test cases:
1. Default values (start=1, end=None) → all pages
2. start_page only (start=3, end=None) → page 3 to end
3. end_page only (start=1, end=2) → pages 1-2
4. Both specified (start=2, end=3) → pages 2-3
5. Invalid range (start > end) → error
6. Out of range (start > total_pages) → error or empty
7. end_page > total_pages → reads up to last page
"""
import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pdf_tools import read_pdf_handler, grep_pdf_handler


SAMPLE_PDF_DIR = Path(__file__).parent.parent / "sample_pdfs"


def get_sample_pdf() -> str:
    """Get first available sample PDF path"""
    pdfs = list(SAMPLE_PDF_DIR.glob("*.pdf"))
    if not pdfs:
        pytest.skip("No sample PDFs available")
    return str(pdfs[0])


class TestReadPdfPageRange:
    """Tests for read_pdf start_page/end_page handling"""

    @pytest.mark.asyncio
    async def test_default_values(self):
        """Default: start=1, end=None → reads from page 1"""
        pdf_path = get_sample_pdf()
        result_json, _ = await read_pdf_handler({
            "file_path": pdf_path
        })
        result = json.loads(result_json)

        assert "error" not in result
        assert "pages" in result
        assert len(result["pages"]) >= 1
        assert result["pages"][0]["page_number"] == 1

    @pytest.mark.asyncio
    async def test_start_page_only(self):
        """start_page=2, end=None → reads from page 2 to end"""
        pdf_path = get_sample_pdf()
        result_json, _ = await read_pdf_handler({
            "file_path": pdf_path,
            "start_page": 2
        })
        result = json.loads(result_json)

        # May error if PDF has only 1 page, or succeed starting from page 2
        if "error" not in result:
            assert result["pages"][0]["page_number"] == 2

    @pytest.mark.asyncio
    async def test_end_page_only(self):
        """start=1, end_page=1 → reads only page 1"""
        pdf_path = get_sample_pdf()
        result_json, _ = await read_pdf_handler({
            "file_path": pdf_path,
            "start_page": 1,
            "end_page": 1
        })
        result = json.loads(result_json)

        assert "error" not in result
        assert len(result["pages"]) == 1
        assert result["pages"][0]["page_number"] == 1

    @pytest.mark.asyncio
    async def test_both_specified(self):
        """start=1, end=2 → reads pages 1-2"""
        pdf_path = get_sample_pdf()
        result_json, _ = await read_pdf_handler({
            "file_path": pdf_path,
            "start_page": 1,
            "end_page": 2
        })
        result = json.loads(result_json)

        # May error if PDF has only 1 page
        if "error" not in result:
            assert len(result["pages"]) <= 2
            assert result["pages"][0]["page_number"] == 1

    @pytest.mark.asyncio
    async def test_invalid_range_start_greater_than_end(self):
        """start > end → should error (validation in Pydantic)"""
        pdf_path = get_sample_pdf()

        # Pydantic validation should catch this
        with pytest.raises(ValueError):
            from src.schemas import ReadPDFInput
            ReadPDFInput(file_path=pdf_path, start_page=5, end_page=2)

    @pytest.mark.asyncio
    async def test_start_page_exceeds_total(self):
        """start > total_pages → error INVALID_PAGE_RANGE"""
        pdf_path = get_sample_pdf()
        result_json, _ = await read_pdf_handler({
            "file_path": pdf_path,
            "start_page": 9999
        })
        result = json.loads(result_json)

        assert "error" in result
        assert result["error"] == "INVALID_PAGE_RANGE"

    @pytest.mark.asyncio
    async def test_end_page_exceeds_total(self):
        """end > total_pages → reads up to last page (no error)"""
        pdf_path = get_sample_pdf()
        result_json, _ = await read_pdf_handler({
            "file_path": pdf_path,
            "start_page": 1,
            "end_page": 9999
        })
        result = json.loads(result_json)

        # Should succeed (capped at total pages) or hit page limit
        # Either way, should not be INVALID_PAGE_RANGE for end > total
        if "error" in result:
            assert result["error"] in ["PAGE_LIMIT_EXCEEDED"]
        else:
            assert len(result["pages"]) >= 1

    @pytest.mark.asyncio
    async def test_zero_start_page(self):
        """start=0 → should error (minimum is 1)"""
        pdf_path = get_sample_pdf()

        with pytest.raises(ValueError):
            from src.schemas import ReadPDFInput
            ReadPDFInput(file_path=pdf_path, start_page=0)

    @pytest.mark.asyncio
    async def test_negative_start_page(self):
        """start=-1 → should error"""
        pdf_path = get_sample_pdf()

        with pytest.raises(ValueError):
            from src.schemas import ReadPDFInput
            ReadPDFInput(file_path=pdf_path, start_page=-1)


class TestGrepPdfPageRange:
    """Tests for grep_pdf start_page/end_page handling"""

    @pytest.fixture
    def check_pdfgrep(self):
        """Skip tests if pdfgrep is not installed"""
        import shutil
        if not shutil.which("pdfgrep"):
            pytest.skip("pdfgrep not installed")

    @pytest.mark.asyncio
    async def test_default_values(self, check_pdfgrep):
        """Default: start=1, end=None → searches all pages"""
        result_json, _ = await grep_pdf_handler({
            "pattern": ".",  # Match any character
            "working_directory": str(SAMPLE_PDF_DIR),
            "max_count": 5
        })
        result = json.loads(result_json)

        # Should not error (unless no PDFs match)
        if "error" not in result:
            assert "matches" in result

    @pytest.mark.asyncio
    async def test_start_page_only(self, check_pdfgrep):
        """start_page=2 → searches from page 2"""
        result_json, _ = await grep_pdf_handler({
            "pattern": ".",
            "working_directory": str(SAMPLE_PDF_DIR),
            "start_page": 2,
            "max_count": 5
        })
        result = json.loads(result_json)

        if "error" not in result and result.get("matches"):
            # All matches should be from page 2 or later
            for match in result["matches"]:
                assert match["page"] >= 2

    @pytest.mark.asyncio
    async def test_end_page_only(self, check_pdfgrep):
        """end_page=1 → searches only page 1"""
        result_json, _ = await grep_pdf_handler({
            "pattern": ".",
            "working_directory": str(SAMPLE_PDF_DIR),
            "end_page": 1,
            "max_count": 5
        })
        result = json.loads(result_json)

        if "error" not in result and result.get("matches"):
            # All matches should be from page 1
            for match in result["matches"]:
                assert match["page"] == 1

    @pytest.mark.asyncio
    async def test_both_specified(self, check_pdfgrep):
        """start=1, end=2 → searches pages 1-2"""
        result_json, _ = await grep_pdf_handler({
            "pattern": ".",
            "working_directory": str(SAMPLE_PDF_DIR),
            "start_page": 1,
            "end_page": 2,
            "max_count": 10
        })
        result = json.loads(result_json)

        if "error" not in result and result.get("matches"):
            for match in result["matches"]:
                assert 1 <= match["page"] <= 2

    @pytest.mark.asyncio
    async def test_start_page_exceeds_total(self, check_pdfgrep):
        """start=9999 → no matches (pdfgrep handles gracefully)"""
        result_json, _ = await grep_pdf_handler({
            "pattern": ".",
            "working_directory": str(SAMPLE_PDF_DIR),
            "start_page": 9999
        })
        result = json.loads(result_json)

        # pdfgrep should return no matches, not error
        if "error" not in result:
            assert result.get("matches", []) == []

    @pytest.mark.asyncio
    async def test_no_page_limit_unlike_read_pdf(self, check_pdfgrep):
        """grep_pdf has no 10-page limit unlike read_pdf"""
        result_json, _ = await grep_pdf_handler({
            "pattern": ".",
            "working_directory": str(SAMPLE_PDF_DIR),
            "start_page": 1,
            "end_page": 100,  # Would exceed read_pdf's limit
            "max_count": 5
        })
        result = json.loads(result_json)

        # Should NOT return PAGE_LIMIT_EXCEEDED error
        if "error" in result:
            assert result["error"] != "PAGE_LIMIT_EXCEEDED"
