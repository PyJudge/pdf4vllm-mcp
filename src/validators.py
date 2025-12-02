"""
Validation logic for PDF MCP server
Enforces page and image limits with intelligent error messages
"""
import pikepdf
from typing import Optional
from .schemas import ValidationResult, SuggestedRange
from .config import config


def validate_pdf_read_request(
    pdf_path: str,
    start_page: int,
    end_page: Optional[int]
) -> ValidationResult:
    """
    Validate PDF read request against page and image limits

    Pre-scans PDF to count pages and images before processing.
    Returns validation result with error details and suggested ranges if limits exceeded.

    Args:
        pdf_path: Path to PDF file
        start_page: Start page (1-indexed)
        end_page: End page (1-indexed, None = last page)

    Returns:
        ValidationResult with validation status and suggestions
    """
    try:
        # Open PDF
        doc = pikepdf.open(pdf_path)
        total_pages = len(doc.pages)

        # Validate page range exists
        if start_page > total_pages:
            doc.close()
            return ValidationResult(
                valid=False,
                error="INVALID_PAGE_RANGE",
                message=(
                    f"Start page ({start_page}) is out of document range. "
                    f"This document has {total_pages} pages. "
                    f"Please request pages between 1-{total_pages}."
                ),
                total_pages=total_pages
            )

        if end_page is not None and end_page < start_page:
            doc.close()
            return ValidationResult(
                valid=False,
                error="INVALID_PAGE_RANGE",
                message=(
                    f"End page ({end_page}) is less than start page ({start_page}). "
                    f"This document has {total_pages} pages. "
                    f"Please request a valid range (e.g., {start_page}-{min(start_page + 9, total_pages)})."
                ),
                total_pages=total_pages
            )

        # Automatically adjust end_page if it exceeds document range
        # Example: 15-page document with request 10-19 → auto-adjust to 10-15
        actual_end = min(end_page or total_pages, total_pages)
        page_count = actual_end - start_page + 1

        # Validate page count
        max_pages = config.max_pages_per_request
        max_images = config.max_images_per_request

        if page_count > max_pages:
            suggested_ranges = calculate_suggested_ranges(
                doc, start_page, actual_end,
                max_pages, max_images
            )
            doc.close()
            return ValidationResult(
                valid=False,
                error="PAGE_LIMIT_EXCEEDED",
                message=(
                    f"Requested page count ({page_count}) exceeds the limit ({max_pages}). "
                    f"This document has {total_pages} pages. "
                    f"Please read in multiple batches using the suggested ranges or invoke a separate agent."
                ),
                total_pages=total_pages,
                suggested_ranges=suggested_ranges
            )

        # Count images in range
        total_images = 0
        for page_num in range(start_page - 1, actual_end):
            if page_num >= total_pages:
                break
            page = doc.pages[page_num]
            total_images += len(page.images)

        # Validate image count
        if total_images > max_images:
            suggested_ranges = calculate_suggested_ranges(
                doc, start_page, actual_end,
                max_pages, max_images
            )
            doc.close()
            return ValidationResult(
                valid=False,
                error="IMAGE_LIMIT_EXCEEDED",
                message=(
                    f"Image count in the requested range ({total_images}) exceeds the limit ({max_images}). "
                    f"Please read in smaller batches using the suggested ranges, select a page range with fewer images, "
                    f"or invoke a separate agent to process."
                ),
                total_pages=total_pages,
                total_images=total_images,
                suggested_ranges=suggested_ranges
            )

        doc.close()
        return ValidationResult(valid=True)

    except FileNotFoundError:
        return ValidationResult(
            valid=False,
            error="FILE_NOT_FOUND",
            message=f"PDF file not found: {pdf_path}"
        )
    except PermissionError:
        return ValidationResult(
            valid=False,
            error="PERMISSION_DENIED",
            message=f"Permission denied accessing PDF: {pdf_path}"
        )
    except pikepdf.PdfError as e:
        return ValidationResult(
            valid=False,
            error="INVALID_PDF",
            message=f"Invalid or corrupted PDF file: {str(e)}"
        )
    except Exception as e:
        return ValidationResult(
            valid=False,
            error="INVALID_PDF",
            message=f"PDF file validation failed: {str(e)}"
        )


def calculate_suggested_ranges(
    doc: pikepdf.Pdf,
    start_page: int,
    end_page: int,
    max_pages: int,
    max_images: int
) -> list[SuggestedRange]:
    """
    Calculate optimal page ranges that respect both page and image limits

    Intelligently splits the requested range into smaller chunks that:
    1. Don't exceed max_pages
    2. Don't exceed max_images
    3. Account for image density variations

    Args:
        doc: Opened pikepdf.Pdf
        start_page: Start page (1-indexed)
        end_page: End page (1-indexed)
        max_pages: Maximum pages per range
        max_images: Maximum images per range

    Returns:
        List of suggested ranges (up to MAX_SUGGESTED_RANGES)
    """
    ranges = []
    current_start = start_page
    total_doc_pages = len(doc.pages)

    while current_start <= end_page and len(ranges) < config.max_suggested_ranges:
        # Start with max allowed pages
        current_end = min(current_start + max_pages - 1, end_page)
        current_images = 0
        final_end = current_start  # Track last valid page

        # Count images and adjust end if needed
        for page_num in range(current_start - 1, current_end):
            if page_num >= total_doc_pages:
                break

            page = doc.pages[page_num]
            page_images = len(page.images)

            # Check if adding this page would exceed image limit
            if current_images + page_images > max_images:
                # If we haven't added any pages yet, include at least this one
                if page_num == current_start - 1:
                    current_images += page_images
                    final_end = page_num + 1
                else:
                    # Stop before this page
                    final_end = page_num
                break

            current_images += page_images
            final_end = page_num + 1

        # Add range if valid
        if final_end >= current_start:
            ranges.append(SuggestedRange(
                start_page=current_start,
                end_page=final_end,
                estimated_images=current_images,
                page_count=final_end - current_start + 1
            ))

        # Move to next range
        current_start = final_end + 1

    return ranges