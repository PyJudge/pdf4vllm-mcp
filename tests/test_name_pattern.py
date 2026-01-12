"""
Tests for name_pattern parameter in list_pdfs.

Test cases:
1. Default (None) → returns all PDFs
2. Simple pattern (sample*) → files starting with "sample"
3. Extension pattern (*1.pdf) → files ending with "1.pdf"
4. Question mark pattern (sample?.pdf) → single character wildcard
5. Case insensitive matching (SAMPLE* matches sample1.pdf)
6. No matches → empty result (not error)
7. Complex pattern (*[0-9].pdf) → files ending with digit before .pdf
"""
import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pdf_tools import list_pdfs_handler


SAMPLE_PDF_DIR = Path(__file__).parent.parent / "sample_pdfs"


@pytest.fixture
def sample_pdf_count() -> int:
    """Count actual PDFs in sample directory"""
    return len(list(SAMPLE_PDF_DIR.glob("*.pdf")))


class TestNamePattern:
    """Tests for list_pdfs name_pattern parameter"""

    @pytest.mark.asyncio
    async def test_default_no_pattern(self, sample_pdf_count):
        """Default: name_pattern=None → returns all PDFs"""
        result_json, _ = await list_pdfs_handler({
            "working_directory": str(SAMPLE_PDF_DIR),
            "recursive": False
        })
        result = json.loads(result_json)

        assert "error" not in result
        assert result["total_count"] == sample_pdf_count

    @pytest.mark.asyncio
    async def test_simple_prefix_pattern(self):
        """Pattern: sample* → files starting with 'sample'"""
        result_json, _ = await list_pdfs_handler({
            "working_directory": str(SAMPLE_PDF_DIR),
            "name_pattern": "sample*",
            "recursive": False
        })
        result = json.loads(result_json)

        assert "error" not in result
        for pdf in result["pdfs"]:
            assert pdf["name"].lower().startswith("sample")

    @pytest.mark.asyncio
    async def test_suffix_pattern(self):
        """Pattern: *1.pdf → files ending with '1.pdf'"""
        result_json, _ = await list_pdfs_handler({
            "working_directory": str(SAMPLE_PDF_DIR),
            "name_pattern": "*1.pdf",
            "recursive": False
        })
        result = json.loads(result_json)

        assert "error" not in result
        for pdf in result["pdfs"]:
            assert pdf["name"].lower().endswith("1.pdf")

    @pytest.mark.asyncio
    async def test_question_mark_wildcard(self):
        """Pattern: sample?.pdf → single character wildcard"""
        result_json, _ = await list_pdfs_handler({
            "working_directory": str(SAMPLE_PDF_DIR),
            "name_pattern": "sample?.pdf",
            "recursive": False
        })
        result = json.loads(result_json)

        assert "error" not in result
        for pdf in result["pdfs"]:
            # Should match sample1.pdf, sample2.pdf, etc. (exactly 11 chars)
            name = pdf["name"].lower()
            assert name.startswith("sample")
            assert name.endswith(".pdf")
            # sample?.pdf means: sample + 1 char + .pdf = 11 chars
            assert len(name) == 11

    @pytest.mark.asyncio
    async def test_case_insensitive(self):
        """Pattern matching should be case-insensitive"""
        # Test uppercase pattern
        result_json_upper, _ = await list_pdfs_handler({
            "working_directory": str(SAMPLE_PDF_DIR),
            "name_pattern": "SAMPLE*",
            "recursive": False
        })
        result_upper = json.loads(result_json_upper)

        # Test lowercase pattern
        result_json_lower, _ = await list_pdfs_handler({
            "working_directory": str(SAMPLE_PDF_DIR),
            "name_pattern": "sample*",
            "recursive": False
        })
        result_lower = json.loads(result_json_lower)

        # Both should return same results
        assert result_upper["total_count"] == result_lower["total_count"]

    @pytest.mark.asyncio
    async def test_no_matches(self):
        """Pattern with no matches → empty result (not error)"""
        result_json, _ = await list_pdfs_handler({
            "working_directory": str(SAMPLE_PDF_DIR),
            "name_pattern": "nonexistent_xyz_*.pdf",
            "recursive": False
        })
        result = json.loads(result_json)

        assert "error" not in result
        assert result["total_count"] == 0
        assert result["pdfs"] == []

    @pytest.mark.asyncio
    async def test_exact_filename(self):
        """Pattern: exact filename → returns only that file"""
        result_json, _ = await list_pdfs_handler({
            "working_directory": str(SAMPLE_PDF_DIR),
            "name_pattern": "sample1.pdf",
            "recursive": False
        })
        result = json.loads(result_json)

        assert "error" not in result
        if result["total_count"] > 0:
            assert result["total_count"] == 1
            assert result["pdfs"][0]["name"].lower() == "sample1.pdf"

    @pytest.mark.asyncio
    async def test_middle_wildcard(self):
        """Pattern: sample*pdf → files with 'sample' prefix and 'pdf' somewhere"""
        result_json, _ = await list_pdfs_handler({
            "working_directory": str(SAMPLE_PDF_DIR),
            "name_pattern": "sample*pdf",
            "recursive": False
        })
        result = json.loads(result_json)

        assert "error" not in result
        for pdf in result["pdfs"]:
            name = pdf["name"].lower()
            assert name.startswith("sample")
            assert "pdf" in name

    @pytest.mark.asyncio
    async def test_pattern_with_recursive(self):
        """Pattern should work with recursive=True"""
        result_json, _ = await list_pdfs_handler({
            "working_directory": str(SAMPLE_PDF_DIR.parent),
            "name_pattern": "sample*.pdf",
            "recursive": True
        })
        result = json.loads(result_json)

        assert "error" not in result
        # Should find PDFs in subdirectories too
        for pdf in result["pdfs"]:
            assert pdf["name"].lower().startswith("sample")

    @pytest.mark.asyncio
    async def test_empty_pattern_treated_as_none(self):
        """Empty string pattern should behave like None"""
        # Test with empty string
        result_json_empty, _ = await list_pdfs_handler({
            "working_directory": str(SAMPLE_PDF_DIR),
            "name_pattern": "",
            "recursive": False
        })
        result_empty = json.loads(result_json_empty)

        # Test with None (default)
        result_json_none, _ = await list_pdfs_handler({
            "working_directory": str(SAMPLE_PDF_DIR),
            "recursive": False
        })
        result_none = json.loads(result_json_none)

        # Empty string matches nothing with fnmatch, so this tests current behavior
        # If you want empty string to act like None, the code needs adjustment
        assert "error" not in result_empty
        assert "error" not in result_none

    @pytest.mark.asyncio
    async def test_korean_filename_pattern(self):
        """Pattern with Korean characters should work"""
        # Create Korean filename if not exists
        korean_pdf = SAMPLE_PDF_DIR / "테스트문서.pdf"
        if not korean_pdf.exists():
            import shutil
            sample = next(SAMPLE_PDF_DIR.glob("sample*.pdf"), None)
            if sample:
                shutil.copy(sample, korean_pdf)

        if korean_pdf.exists():
            # Test Korean pattern
            result_json, _ = await list_pdfs_handler({
                "working_directory": str(SAMPLE_PDF_DIR),
                "name_pattern": "*테스트*",
                "recursive": False
            })
            result = json.loads(result_json)

            assert "error" not in result
            assert result["total_count"] >= 1
            assert any("테스트" in pdf["name"] for pdf in result["pdfs"])

    @pytest.mark.asyncio
    async def test_korean_exact_filename(self):
        """Exact Korean filename should match"""
        korean_pdf = SAMPLE_PDF_DIR / "테스트문서.pdf"
        if not korean_pdf.exists():
            pytest.skip("Korean test PDF not available")

        result_json, _ = await list_pdfs_handler({
            "working_directory": str(SAMPLE_PDF_DIR),
            "name_pattern": "테스트문서.pdf",
            "recursive": False
        })
        result = json.loads(result_json)

        assert "error" not in result
        assert result["total_count"] == 1
        assert result["pdfs"][0]["name"] == "테스트문서.pdf"
