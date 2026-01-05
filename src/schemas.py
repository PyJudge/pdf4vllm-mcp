"""
Pydantic schemas for PDF MCP server tool inputs and outputs
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal
from .config import config


# ============================================================================
# list_pdfs tool schemas
# ============================================================================

class ListPDFsInput(BaseModel):
    """Input schema for list_pdfs tool"""
    working_directory: Optional[str] = Field(
        default=".",
        description="Working directory to search for PDFs (relative or absolute)"
    )
    include_subdirectories: bool = Field(
        default=True,
        description="Include subdirectories in search"
    )
    max_depth: Optional[int] = Field(
        default_factory=lambda: config.max_recursion_depth,
        description="Maximum recursion depth (None = unlimited)"
    )
    name_pattern: Optional[str] = Field(
        default=None,
        description="Glob pattern for filename filtering (e.g., '*report*', 'doc_202?.pdf')"
    )


class PDFInfo(BaseModel):
    """Metadata for a single PDF file"""
    name: str = Field(description="File name with extension")
    path: str = Field(description="Absolute file path for use with read_pdf")
    pages: int = Field(description="Total number of pages")


class ListPDFsOutput(BaseModel):
    """Output schema for list_pdfs tool"""
    pdfs: List[PDFInfo] = Field(description="List of PDF files found")
    total_count: int = Field(description="Total number of PDFs found")
    working_directory: str = Field(description="Working directory that was searched")


class ListPDFsError(BaseModel):
    """Error response for list_pdfs tool"""
    error: Literal[
        "DIRECTORY_NOT_FOUND",
        "NOT_A_DIRECTORY",
        "PERMISSION_DENIED",
        "INTERNAL_ERROR"
    ] = Field(description="Error type")
    message: str = Field(description="Human-readable error message")


# ============================================================================
# read_pdf tool schemas
# ============================================================================

class ReadPDFInput(BaseModel):
    """Input schema for read_pdf tool"""
    file_path: str = Field(
        ...,
        description="Path to PDF file (relative to working directory or absolute)"
    )
    start_page: int = Field(
        default=1,
        ge=1,
        description="Start page number (1-indexed, inclusive)"
    )
    end_page: Optional[int] = Field(
        default=None,
        ge=1,
        description="End page number (1-indexed, inclusive). None = last page"
    )
    filter_header_footer: bool = Field(
        default=True,
        description="Filter out header/footer images based on size and position"
    )
    crop_images: bool = Field(
        default=True,
        description="Crop images to maximum dimension (A4 1/4 resolution)"
    )
    max_image_dimension: int = Field(
        default_factory=lambda: config.max_image_dimension,
        ge=28,
        le=4096,
        description="Maximum image dimension in pixels (28-4096)"
    )
    extraction_mode: str = Field(
        default="auto",
        description=(
            "Content extraction mode:\n"
            "- 'auto': Smart detection - extract text/tables/images, add page image only if corrupted (default)\n"
            "- 'text_only': Extract text/tables only, never add page image\n"
            "- 'image_only': Skip text extraction, provide only full page images (for scanned PDFs)"
        )
    )
    page_image_dpi: int = Field(
        default_factory=lambda: config.page_image_dpi,
        ge=50,
        le=300,
        description="DPI for page image rendering (50-300, default: 100)"
    )

    @field_validator('extraction_mode')
    @classmethod
    def validate_extraction_mode(cls, v):
        """Validate extraction mode"""
        valid_modes = ['auto', 'text_only', 'image_only']
        if v not in valid_modes:
            raise ValueError(f"extraction_mode must be one of {valid_modes}")
        return v

    @field_validator('end_page')
    @classmethod
    def validate_end_page(cls, v, info):
        """Validate end_page is >= start_page"""
        if v is not None and 'start_page' in info.data:
            if v < info.data['start_page']:
                raise ValueError("end_page must be >= start_page")
        return v


class ContentBlock(BaseModel):
    """Single content block (text, table, or image)"""
    type: Literal["text", "table", "image"] = Field(description="Content type: 'text', 'table', or 'image'")
    content: Optional[str] = Field(default=None, description="Text content, table markdown, or base64 image")


class PageData(BaseModel):
    """Data for a single PDF page"""
    page_number: int = Field(description="Page number (1-indexed)")
    content_blocks: List[ContentBlock] = Field(
        description="Ordered list of content blocks (text/table/image in reading order)"
    )
    text_corrupted: Optional[bool] = Field(
        default=None,
        description="Whether text is corrupted (auto-detected)"
    )
    corruption_ratio: Optional[float] = Field(
        default=None,
        description="Text corruption ratio (0.0-1.0)"
    )
    page_image: Optional[str] = Field(
        default=None,
        description="Full page as image (base64) if text corrupted or requested"
    )
    page_image_width: Optional[int] = Field(default=None, description="Page image width")
    page_image_height: Optional[int] = Field(default=None, description="Page image height")
    extractable_char_count: Optional[int] = Field(
        default=None,
        description="Number of extractable text characters (only in image_only mode)"
    )
    text_hint: Optional[str] = Field(
        default=None,
        description="Hint about text extraction availability (only in image_only mode)"
    )


class SuggestedRange(BaseModel):
    """Suggested page range that respects limits"""
    start_page: int = Field(description="Suggested start page")
    end_page: int = Field(description="Suggested end page")
    estimated_images: int = Field(description="Estimated number of images in range")
    page_count: int = Field(description="Number of pages in range")


class ReadPDFSuccess(BaseModel):
    """Successful read_pdf response"""
    file_path: str = Field(description="Path to the PDF file that was read")
    pages: List[PageData] = Field(description="List of page data in order")
    total_pages_read: int = Field(description="Total number of pages read")
    total_images: int = Field(description="Total number of images extracted")


class ReadPDFError(BaseModel):
    """Error response for read_pdf tool"""
    error: Literal[
        "PAGE_LIMIT_EXCEEDED",
        "IMAGE_LIMIT_EXCEEDED",
        "FILE_NOT_FOUND",
        "INVALID_PDF",
        "INVALID_PAGE_RANGE",
        "PERMISSION_DENIED"
    ] = Field(description="Error type")
    message: str = Field(description="Human-readable error message")
    total_pages: Optional[int] = Field(
        default=None,
        description="Total pages in document (if applicable)"
    )
    total_images: Optional[int] = Field(
        default=None,
        description="Total images in requested range (if applicable)"
    )
    suggested_ranges: Optional[List[SuggestedRange]] = Field(
        default=None,
        description="Suggested page ranges to read instead"
    )
    suggested_files: Optional[List[str]] = Field(
        default=None,
        description="Similar PDF filenames (when file not found)"
    )


# ============================================================================
# Validation result (internal)
# ============================================================================

class ValidationResult(BaseModel):
    """Internal validation result"""
    valid: bool
    error: Optional[str] = None
    message: Optional[str] = None
    total_pages: Optional[int] = None
    total_images: Optional[int] = None
    suggested_ranges: Optional[List[SuggestedRange]] = None


# ============================================================================
# grep_pdf tool schemas
# ============================================================================

class GrepPDFInput(BaseModel):
    """Input schema for grep_pdf tool"""
    pattern: str = Field(
        ...,
        description="Search pattern (regex by default)"
    )
    file_path: Optional[str] = Field(
        default=None,
        description="Specific PDF file. If not provided, searches ALL PDFs in working_directory"
    )
    working_directory: str = Field(
        default=".",
        description="Base directory for search (only used when file_path is not provided)"
    )
    ignore_case: bool = Field(
        default=False,
        description="Case-insensitive search"
    )
    fixed_strings: bool = Field(
        default=False,
        description="Treat pattern as literal string, not regex"
    )
    context: int = Field(
        default=0,
        ge=0,
        le=5,
        description="Lines of context before/after match (0-5)"
    )
    max_count: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum matches to return (1-100)"
    )
    recursive: bool = Field(
        default=True,
        description="Include subdirectories when searching directory"
    )


class GrepMatch(BaseModel):
    """Single match result from grep_pdf"""
    file: str = Field(description="PDF file path")
    page: int = Field(description="Page number (1-indexed)")
    text: str = Field(description="Matched line text")


class GrepPDFOutput(BaseModel):
    """Successful grep_pdf response"""
    matches: List[GrepMatch] = Field(description="List of matches found")
    total: int = Field(description="Total matches returned")
    truncated: bool = Field(description="True if results were limited by max_count")
    files_searched: int = Field(description="Number of PDF files searched")


class GrepPDFError(BaseModel):
    """Error response for grep_pdf tool"""
    error: Literal[
        "PDFGREP_NOT_INSTALLED",
        "DIRECTORY_NOT_FOUND",
        "FILE_NOT_FOUND",
        "PERMISSION_DENIED",
        "INVALID_PATTERN",
        "INTERNAL_ERROR"
    ] = Field(description="Error type")
    message: str = Field(description="Human-readable error message")
    install_hint: Optional[str] = Field(
        default=None,
        description="Installation command hint (only for PDFGREP_NOT_INSTALLED)"
    )