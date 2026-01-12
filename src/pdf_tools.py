"""
PDF tool handlers for MCP server
Implements list_pdfs and read_pdf tools with intelligent limits

Backend: pdfplumber (text/tables) + pypdfium2 (page rendering) + pikepdf (image extraction)
"""
import pdfplumber
import pikepdf
import pypdfium2 as pdfium
from PIL import Image
import fnmatch
import unicodedata
import io
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from src.config import config
from .schemas import (
    ListPDFsInput, ListPDFsOutput, PDFInfo, ListPDFsError,
    ReadPDFInput, ReadPDFSuccess, ReadPDFError,
    PageData, ContentBlock,
    GrepPDFInput, GrepPDFOutput, GrepMatch, GrepPDFError
)
from .validators import validate_pdf_read_request
from .image_processor import crop_image_to_max_dimension, is_header_footer_image
from .file_matcher import find_similar_pdfs, get_file_not_found_message
from .text_validator import is_text_corrupted, check_pdf_corruption_with_pdfminer
from .table_converter import convert_table_to_markdown
from .content_orderer import order_content_blocks, merge_adjacent_text_blocks
from .text_extractor import extract_non_table_text_regions

logger = logging.getLogger(__name__)


def validate_path_security(path: Path, allowed_base: Path) -> bool:
    """
    Validate that a path is within the allowed base directory.
    Prevents path traversal attacks.

    Args:
        path: Path to validate
        allowed_base: Base directory that path must be within

    Returns:
        True if path is safe, False if potential path traversal
    """
    try:
        # Resolve both paths to eliminate symlinks and .. components
        resolved_path = path.resolve()
        resolved_base = allowed_base.resolve()

        # Check if the resolved path starts with the resolved base
        return resolved_path.is_relative_to(resolved_base)
    except (ValueError, RuntimeError):
        return False


async def list_pdfs_handler(arguments: dict[str, Any]) -> tuple[str, list[dict]]:
    """
    List all PDF files recursively from working directory

    Args:
        arguments: Dictionary matching ListPDFsInput schema

    Returns:
        Tuple of (JSON string, empty list) - no images for list_pdfs
    """
    try:
        # Validate input
        input_data = ListPDFsInput(**arguments)

        # Resolve working directory
        working_dir = Path(input_data.working_directory)

        # If not absolute path, use current directory as base
        if not working_dir.is_absolute():
            working_dir = Path.cwd() / working_dir

        working_dir = working_dir.resolve()

        if not working_dir.exists():
            # List all subdirectories of the current directory
            current_dir = Path.cwd()
            subdirs = []

            # Direct subdirectories of the current directory
            try:
                for item in sorted(current_dir.iterdir()):
                    if item.is_dir() and not item.name.startswith('.'):
                        subdirs.append(item.name)
            except (PermissionError, OSError) as e:
                logger.debug(f"Could not list directory {current_dir}: {e}")

            if subdirs:
                dir_list = "\n".join([f"  - {d}" for d in subdirs])
                msg = (
                    f"Working directory not found: {working_dir}\n\n"
                    f"Available folders in current directory ({current_dir}):\n{dir_list}"
                )
            else:
                msg = f"Working directory not found: {working_dir}"

            error = ListPDFsError(error="DIRECTORY_NOT_FOUND", message=msg)
            return error.model_dump_json(indent=2), []

        if not working_dir.is_dir():
            error = ListPDFsError(
                error="NOT_A_DIRECTORY",
                message=f"Path is not a directory: {working_dir}"
            )
            return error.model_dump_json(indent=2), []

        # Find PDF files
        pdfs = []
        pattern = "**/*.pdf" if input_data.recursive else "*.pdf"
        max_depth = input_data.max_depth

        for pdf_path in sorted(working_dir.glob(pattern)):
            try:
                # Skip if not a file
                if not pdf_path.is_file():
                    continue

                # Check depth limit
                if max_depth is not None and input_data.recursive:
                    relative_path = pdf_path.relative_to(working_dir)
                    depth = len(relative_path.parts) - 1  # -1 for filename
                    if depth > max_depth:
                        continue

                # Check name pattern filter (NFC normalize for macOS NFD filenames)
                if input_data.name_pattern:
                    normalized_name = unicodedata.normalize('NFC', pdf_path.name.lower())
                    normalized_pattern = unicodedata.normalize('NFC', input_data.name_pattern.lower())
                    if not fnmatch.fnmatch(normalized_name, normalized_pattern):
                        continue

                # Get page count using pypdfium2
                pdf_doc = pdfium.PdfDocument(str(pdf_path))
                total_pages = len(pdf_doc)
                pdf_doc.close()

                # Add to list
                pdfs.append(PDFInfo(
                    name=pdf_path.name,
                    path=str(pdf_path),
                    pages=total_pages
                ))

            except Exception:
                # Skip files that can't be opened (corrupted, not PDF, etc.)
                continue

        # Create output
        output = ListPDFsOutput(
            pdfs=pdfs,
            total_count=len(pdfs),
            working_directory=str(working_dir)
        )

        return output.model_dump_json(indent=2), []

    except PermissionError as e:
        error = ListPDFsError(
            error="PERMISSION_DENIED",
            message=f"Permission denied: {str(e)}"
        )
        return error.model_dump_json(indent=2), []
    except Exception as e:
        # Return error using schema
        error = ListPDFsError(
            error="INTERNAL_ERROR",
            message=f"Failed to list PDFs: {str(e)}"
        )
        return error.model_dump_json(indent=2), []


async def read_pdf_handler(arguments: dict[str, Any]) -> tuple[str, list[dict]]:
    """
    Read PDF with page and image limits, intelligent validation

    Implements:
    1. Pre-scan validation (page/image limits)
    2. Text/image ordering preservation (from comclerk_agent)
    3. Header/footer filtering
    4. Image cropping to A4 1/4 (from qwen-code)
    5. Suggested ranges on limit exceeded

    Args:
        arguments: Dictionary matching ReadPDFInput schema

    Returns:
        Tuple of (JSON string, list of image dicts)
        - JSON has image placeholders like [IMAGE_0], [IMAGE_1]
        - Images list: [{"data": bytes, "format": "jpeg"|"png"}, ...]
          (MCP SDK Image wrapper handles base64 encoding)
    """
    try:
        # Validate input
        input_data = ReadPDFInput(**arguments)

        # Resolve PDF path
        pdf_path = Path(input_data.file_path)
        if not pdf_path.is_absolute():
            pdf_path = Path.cwd() / pdf_path
        pdf_path = pdf_path.resolve()

        # Check file exists
        if not pdf_path.exists():
            # Find similar files
            similar_files = find_similar_pdfs(str(pdf_path), max_suggestions=3)
            error_message = get_file_not_found_message(str(pdf_path), similar_files)

            error = ReadPDFError(
                error="FILE_NOT_FOUND",
                message=error_message,
                suggested_files=similar_files if similar_files else None
            )
            return error.model_dump_json(indent=2), []

        # Security: Check for path traversal attacks
        # The file must be within the current working directory or its subdirectories
        cwd = Path.cwd().resolve()
        if not validate_path_security(pdf_path, cwd):
            error = ReadPDFError(
                error="PERMISSION_DENIED",
                message="Access denied: File path must be within the current working directory"
            )
            return error.model_dump_json(indent=2), []

        # Check read permission
        if not os.access(pdf_path, os.R_OK):
            error = ReadPDFError(
                error="PERMISSION_DENIED",
                message=f"Permission denied: Cannot read file {pdf_path}"
            )
            return error.model_dump_json(indent=2), []

        # Validate limits BEFORE processing
        validation = validate_pdf_read_request(
            str(pdf_path),
            input_data.start_page,
            input_data.end_page
        )

        if not validation.valid:
            # Return error with suggested ranges
            error = ReadPDFError(
                error=validation.error,
                message=validation.message,
                total_pages=validation.total_pages,
                total_images=validation.total_images,
                suggested_ranges=validation.suggested_ranges
            )
            return error.model_dump_json(indent=2), []

        # Open PDF with pdfplumber for text extraction
        # Also open pikepdf once for image extraction (if needed)
        with pdfplumber.open(str(pdf_path)) as pdf:
            total_pages = len(pdf.pages)
            end_page = min(input_data.end_page or total_pages, total_pages)

            pages_data = []
            total_images_count = 0
            extracted_images = []  # List of {"data": bytes, "format": "jpeg"|"png"}
            image_index = 0  # Global image index for placeholders

            # Check if we need pikepdf for image extraction
            mode = input_data.extraction_mode
            need_pikepdf = (mode == 'auto')  # Only auto mode extracts document images

            # Open pikepdf once outside the loop (if needed)
            pike_pdf = None
            if need_pikepdf:
                try:
                    pike_pdf = pikepdf.open(str(pdf_path))
                except Exception as e:
                    logger.warning(f"Failed to open PDF with pikepdf: {e}")

            try:
                # Process pages in order (preserves text/image ordering)
                for page_num in range(input_data.start_page, end_page + 1):
                    if page_num > total_pages:
                        break

                    page = pdf.pages[page_num - 1]  # 0-based index

                    # Check extraction mode (mode already set above)
                    skip_text_extraction = (mode == 'image_only')

                    # Variables for text extraction hint (image_only mode)
                    extractable_char_count = None
                    text_hint = None

                    if skip_text_extraction:
                        # Skip text and table extraction entirely
                        tables_with_position = []
                        table_bboxes = []
                        text_lines_for_ordering = []
                        full_text = ""

                        # Check for extractable text (to provide hint)
                        page_text = page.extract_text() or ''
                        char_count = len(page_text.strip())
                        if char_count > 0:
                            extractable_char_count = char_count

                            # Check corruption to determine hint
                            pdfminer_corrupted, warning_count = check_pdf_corruption_with_pdfminer(
                                str(pdf_path), page_num
                            )
                            if pdfminer_corrupted:
                                is_corrupted = True
                                ratio = warning_count / 10
                            else:
                                is_corrupted, ratio = is_text_corrupted(page_text)

                            if is_corrupted:
                                corruption_pct = int(ratio * 100)
                                text_hint = f"{char_count} chars ({corruption_pct}% corrupted). Text extraction not recommended."
                            else:
                                text_hint = f"{char_count} chars extractable. Use 'auto' to get text."
                    else:
                        # Extract tables first (to get bboxes)
                        tables_raw = page.extract_tables()
                        tables_with_position = []
                        table_bboxes = []

                        if tables_raw:
                            table_objects = page.find_tables()
                            for i, (table_data, table_obj) in enumerate(zip(tables_raw, table_objects)):
                                md = convert_table_to_markdown(table_data) if table_data else ""
                                if md:
                                    tables_with_position.append({
                                        'top': table_obj.bbox[1],
                                        'markdown': f"**Table {i+1}**\n\n{md}"
                                    })
                                    table_bboxes.append(table_obj.bbox)

                        # Extract text EXCLUDING table regions (prevent duplication!)
                        text_regions = extract_non_table_text_regions(page, table_bboxes)

                        # Use text_regions instead of text_lines
                        text_lines_for_ordering = []
                        for region in text_regions:
                            # Treat each region as a single "line"
                            text_lines_for_ordering.append({
                                'top': region['top'],
                                'text': region['text']
                            })

                        full_text = '\n\n'.join(r['text'] for r in text_regions)  # Full text (excluding tables)

                    # Auto-detect text corruption (only if extracting text)
                    text_corrupted = False
                    corruption_ratio = 0.0

                    if not skip_text_extraction:
                        pdfminer_corrupted, warning_count = check_pdf_corruption_with_pdfminer(
                            str(pdf_path), page_num
                        )

                        # Use pdfminer warnings first, fallback to character-based detection
                        if pdfminer_corrupted:
                            text_corrupted = True
                            corruption_ratio = warning_count / 10
                        else:
                            # Include table content in corruption check
                            all_text_for_check = full_text
                            if tables_with_position:
                                table_texts = '\n\n'.join(t['markdown'] for t in tables_with_position)
                                all_text_for_check = f"{full_text}\n\n{table_texts}" if full_text else table_texts

                            text_corrupted, corruption_ratio = is_text_corrupted(all_text_for_check)

                    # Provide full page as image based on extraction mode
                    page_image_base64 = None
                    page_img_width = None
                    page_img_height = None

                    # Determine if we should include page image
                    should_include_image = (
                        mode == 'image_only' or                  # Always in image_only mode
                        (mode == 'auto' and text_corrupted)      # Auto mode: only if corrupted
                    )
                    # mode == 'text_only' never includes page image

                    if should_include_image:
                        try:
                            logger.info(f"Page {page_num}: Attempting to render page image (mode={mode}, text_corrupted={text_corrupted})")
                            # Render page image with pypdfium2 (no external dependencies!)
                            pdfium_doc = pdfium.PdfDocument(str(pdf_path))
                            pdfium_page = pdfium_doc[page_num - 1]  # 0-indexed

                            # Calculate scale based on DPI (PDF base is 72 DPI)
                            scale = input_data.page_image_dpi / 72
                            bitmap = pdfium_page.render(scale=scale)
                            page_img = bitmap.to_pil()
                            pdfium_doc.close()

                            logger.info(f"Page {page_num}: pypdfium2 rendered page as {page_img.size}")

                            if page_img:

                                # White-out header/footer if filter enabled (for image_only mode)
                                if input_data.filter_header_footer:
                                    from PIL import ImageDraw
                                    draw = ImageDraw.Draw(page_img)
                                    width, height = page_img.size
                                    # Header: top 6% of page
                                    header_height = int(height * config.header_footer_ratio)
                                    draw.rectangle([0, 0, width, header_height], fill='white')
                                    # Footer: bottom 6% of page
                                    footer_start = int(height * config.footer_start_ratio)
                                    draw.rectangle([0, footer_start, width, height], fill='white')

                                # Resize page image to fit within max_image_dimension
                                width, height = page_img.size
                                max_dim = input_data.max_image_dimension
                                if width > max_dim or height > max_dim:
                                    scale = min(max_dim / width, max_dim / height)
                                    new_width = int(width * scale)
                                    new_height = int(height * scale)
                                    page_img = page_img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                                # Convert to RGB if necessary (JPEG doesn't support RGBA)
                                if page_img.mode in ('RGBA', 'LA', 'P'):
                                    page_img = page_img.convert('RGB')

                                buffered = io.BytesIO()
                                page_img.save(buffered, format="JPEG", quality=config.jpeg_quality)

                                # Add to extracted images with raw bytes (MCP SDK handles base64 encoding)
                                extracted_images.append({
                                    "data": buffered.getvalue(),  # raw bytes
                                    "format": "jpeg"              # format for Image wrapper
                                })
                                logger.info(f"Page {page_num}: Added page image to extracted_images, total={len(extracted_images)}")
                                page_image_base64 = f"[IMAGE_{image_index}]"
                                image_index += 1
                                total_images_count += 1  # Count page images too

                                page_img_width = page_img.width
                                page_img_height = page_img.height

                                # Note: text_hint not set here since text_corrupted
                                # already triggers corruption warning in UI
                            else:
                                logger.warning(f"Page {page_num}: pypdfium2 failed to render page")
                        except Exception as e:
                            import traceback
                            logger.error(f"Page {page_num}: Failed to render page image: {e}")
                            logger.error(f"Page {page_num}: Traceback: {traceback.format_exc()}")

                    # Extract images with pikepdf (skip if image_only or text_only mode)
                    images_with_position = []

                    # text_only mode: skip all image extraction
                    skip_image_extraction = (mode == 'image_only' or mode == 'text_only')

                    if not skip_image_extraction and pike_pdf:
                        # Get image position info from pdfplumber
                        pdfplumber_images = page.images if hasattr(page, 'images') else []

                        # Extract actual image data with pikepdf (use pre-opened pike_pdf)
                        try:
                            pike_page = pike_pdf.pages[page_num - 1]

                            for img_index, (img_name, raw_image) in enumerate(pike_page.images.items()):
                                try:
                                    # Extract image using pikepdf
                                    pdf_image = pikepdf.PdfImage(raw_image)
                                    pil_image = pdf_image.as_pil_image()

                                    # Get display size from pdfplumber (actual size in PDF page)
                                    display_width = pil_image.width
                                    display_height = pil_image.height

                                    if img_index < len(pdfplumber_images):
                                        pdf_img_info = pdfplumber_images[img_index]
                                        # Calculate display size from bbox (in PDF points)
                                        # pdfplumber provides width/height in PDF points
                                        if 'width' in pdf_img_info and 'height' in pdf_img_info:
                                            # PDF points to pixels (assuming 72 DPI base, scale to reasonable size)
                                            # Limit to actual display size in PDF
                                            display_width = int(pdf_img_info['width'])
                                            display_height = int(pdf_img_info['height'])

                                    # Resize image to fit within display size while maintaining aspect ratio
                                    if pil_image.width > display_width or pil_image.height > display_height:
                                        from PIL import Image as PILImage
                                        # Calculate scale to fit within display size while keeping aspect ratio
                                        scale = min(display_width / pil_image.width, display_height / pil_image.height)
                                        new_width = int(pil_image.width * scale)
                                        new_height = int(pil_image.height * scale)
                                        pil_image = pil_image.resize(
                                            (new_width, new_height),
                                            PILImage.Resampling.LANCZOS
                                        )

                                    # Convert PIL image to bytes
                                    img_buffer = io.BytesIO()
                                    pil_image.save(img_buffer, format='PNG')
                                    img_bytes = img_buffer.getvalue()

                                    # Create img_data dict for header/footer filter
                                    img_data = {
                                        "image": img_bytes,
                                        "width": pil_image.width,
                                        "height": pil_image.height
                                    }

                                    # Filter header/footer if enabled
                                    if input_data.filter_header_footer:
                                        if is_header_footer_image(img_data):
                                            continue

                                    # Crop image if enabled (additional max dimension limit)
                                    if input_data.crop_images:
                                        result = crop_image_to_max_dimension(
                                            img_bytes,
                                            input_data.max_image_dimension
                                        )

                                        # Skip if image is too small and discarded
                                        if result[0] is None:
                                            continue

                                        img_bytes = result[0]

                                    # Add to extracted images with raw bytes (MCP SDK handles base64 encoding)
                                    extracted_images.append({
                                        "data": img_bytes,   # raw bytes
                                        "format": "png"      # format for Image wrapper
                                    })
                                    img_placeholder = f"[IMAGE_{image_index}]"
                                    image_index += 1

                                    # Get position from pdfplumber if available
                                    top = pdfplumber_images[img_index].get('top', 0) if img_index < len(pdfplumber_images) else 0

                                    images_with_position.append({
                                        'top': top,
                                        'image_data': img_placeholder  # Use placeholder instead of base64
                                    })
                                    total_images_count += 1

                                except Exception as e:
                                    logger.debug(f"Failed to extract image {img_index} on page {page_num}: {e}")
                                    continue
                        except Exception as e:
                            logger.warning(f"Failed to extract images with pikepdf on page {page_num}: {e}")

                    # Reconstruct content order (using text excluding tables)
                    ordered_blocks_raw = order_content_blocks(
                        text_lines_for_ordering,
                        tables_with_position,
                        images_with_position
                    )

                    # Merge adjacent text blocks
                    ordered_blocks = merge_adjacent_text_blocks(ordered_blocks_raw)

                    # Convert to ContentBlock (simple conversion!)
                    content_blocks = []

                    # CRITICAL: Skip adding corrupted text/tables if text is corrupted
                    # This applies to both Auto mode (text_corrupted=True) and image_only mode
                    should_skip_text_blocks = (
                        (mode == 'auto' and text_corrupted) or  # Auto mode: skip if corrupted
                        mode == 'image_only'                     # image_only: always skip
                    )

                    if should_skip_text_blocks:
                        # Only add image blocks (if any), skip text and table blocks
                        for block in ordered_blocks:
                            if block['type'] == 'image':
                                content_blocks.append(ContentBlock(
                                    type=block['type'],
                                    content=block.get('content')
                                ))
                    else:
                        # Normal mode: add all blocks
                        for block in ordered_blocks:
                            content = block.get('content')
                            # Clean up text blocks
                            if block['type'] == 'text' and content:
                                content = content.strip()
                                # Skip page number separators like "- 2 -", "- 10 -"
                                if re.match(r'^-\s*\d+\s*-$', content):
                                    continue
                            content_blocks.append(ContentBlock(
                                type=block['type'],
                                content=content
                            ))

                    pages_data.append(PageData(
                        page_number=page_num,
                        content_blocks=content_blocks,
                        text_corrupted=text_corrupted if text_corrupted else None,
                        corruption_ratio=corruption_ratio if text_corrupted else None,
                        page_image=page_image_base64,
                        page_image_width=page_img_width,
                        page_image_height=page_img_height,
                        extractable_char_count=extractable_char_count,
                        text_hint=text_hint
                    ))
            finally:
                # Close pikepdf if it was opened
                if pike_pdf:
                    pike_pdf.close()

        # Create success response
        output = ReadPDFSuccess(
            file_path=str(pdf_path),
            pages=pages_data,
            total_pages_read=len(pages_data),
            total_images=total_images_count
        )

        logger.info(f"Returning {len(extracted_images)} images")
        # Remove null values for clean output
        return output.model_dump_json(indent=2, exclude_none=True), extracted_images

    except FileNotFoundError as e:
        error = ReadPDFError(
            error="FILE_NOT_FOUND",
            message=f"PDF file not found: {str(e)}"
        )
        return error.model_dump_json(indent=2), []
    except PermissionError as e:
        error = ReadPDFError(
            error="PERMISSION_DENIED",
            message=f"Permission denied accessing PDF: {str(e)}"
        )
        return error.model_dump_json(indent=2), []
    except (pikepdf.PdfError, pdfplumber.pdfminer.pdfparser.PDFSyntaxError) as e:
        error = ReadPDFError(
            error="INVALID_PDF",
            message=f"Invalid or corrupted PDF file: {str(e)}"
        )
        return error.model_dump_json(indent=2), []
    except Exception as e:
        # Return error with more specific context
        error = ReadPDFError(
            error="INVALID_PDF",
            message=f"Error processing PDF: {type(e).__name__}: {str(e)}"
        )
        return error.model_dump_json(indent=2), []


def check_pdfgrep_installed() -> bool:
    """Check if pdfgrep is available in PATH"""
    return shutil.which("pdfgrep") is not None


async def grep_pdf_handler(arguments: dict[str, Any]) -> tuple[str, list[dict]]:
    """
    Search PDF files using pdfgrep.

    Args:
        arguments: Dictionary matching GrepPDFInput schema

    Returns:
        Tuple of (JSON string, empty list) - no images for grep_pdf
    """
    try:
        # 1. Check pdfgrep installation FIRST - block execution if not installed
        if not check_pdfgrep_installed():
            error = GrepPDFError(
                error="PDFGREP_NOT_INSTALLED",
                message="pdfgrep is not installed. Please install it first.",
                install_hint="brew install pdfgrep (macOS) or apt install pdfgrep (Ubuntu)"
            )
            return error.model_dump_json(indent=2), []

        # 2. Validate input
        input_data = GrepPDFInput(**arguments)

        # 3. Resolve target path
        if input_data.file_path:
            target_path = Path(input_data.file_path)
            if not target_path.is_absolute():
                target_path = Path.cwd() / target_path
            target_path = target_path.resolve()

            if not target_path.exists():
                error = GrepPDFError(
                    error="FILE_NOT_FOUND",
                    message=f"PDF file not found: {target_path}"
                )
                return error.model_dump_json(indent=2), []

            if not target_path.suffix.lower() == '.pdf':
                error = GrepPDFError(
                    error="FILE_NOT_FOUND",
                    message=f"Not a PDF file: {target_path}"
                )
                return error.model_dump_json(indent=2), []
        else:
            target_path = Path(input_data.working_directory)
            if not target_path.is_absolute():
                target_path = Path.cwd() / target_path
            target_path = target_path.resolve()

            if not target_path.exists():
                error = GrepPDFError(
                    error="DIRECTORY_NOT_FOUND",
                    message=f"Directory not found: {target_path}"
                )
                return error.model_dump_json(indent=2), []

            if not target_path.is_dir():
                error = GrepPDFError(
                    error="DIRECTORY_NOT_FOUND",
                    message=f"Not a directory: {target_path}"
                )
                return error.model_dump_json(indent=2), []

        # 4. Build pdfgrep command
        cmd = ["pdfgrep", "-n", "-H"]  # Always include page number and filename

        if input_data.ignore_case:
            cmd.append("-i")
        if input_data.fixed_strings:
            cmd.append("-F")
        if input_data.context > 0:
            cmd.extend(["-C", str(input_data.context)])
        if input_data.max_count:
            cmd.extend(["-m", str(input_data.max_count)])
        if input_data.recursive and not input_data.file_path:
            cmd.append("-r")
        # Only add --page-range if not using defaults (start=1, end=all)
        if input_data.start_page != 1 or input_data.end_page is not None:
            end = input_data.end_page or 9999  # pdfgrep handles out-of-range gracefully
            cmd.extend(["--page-range", f"{input_data.start_page}-{end}"])

        cmd.append(input_data.pattern)
        cmd.append(str(target_path))

        logger.info(f"Running pdfgrep command: {' '.join(cmd)}")

        # 5. Execute with timeout
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(target_path.parent) if input_data.file_path else str(target_path)
            )
        except subprocess.TimeoutExpired:
            error = GrepPDFError(
                error="INTERNAL_ERROR",
                message="Search timed out after 60 seconds"
            )
            return error.model_dump_json(indent=2), []

        # 6. Check for errors
        if result.returncode == 2:
            # pdfgrep returns 2 for errors (invalid regex, etc.)
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            if "Invalid" in error_msg or "regex" in error_msg.lower():
                error = GrepPDFError(
                    error="INVALID_PATTERN",
                    message=f"Invalid search pattern: {error_msg}"
                )
            else:
                error = GrepPDFError(
                    error="INTERNAL_ERROR",
                    message=f"pdfgrep error: {error_msg}"
                )
            return error.model_dump_json(indent=2), []

        # 7. Parse output: "file.pdf:page:text" format
        matches = []
        files_found = set()

        if result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                if not line or line == '--':  # Skip empty lines and context separators
                    continue

                # Parse "file:page:text" format
                # Handle case where filename might contain ':'
                parts = line.split(':')
                if len(parts) >= 3:
                    # Find the page number (should be numeric)
                    file_parts = []
                    page_idx = -1

                    for i, part in enumerate(parts):
                        if part.isdigit() and i > 0:
                            page_idx = i
                            break
                        file_parts.append(part)

                    if page_idx > 0:
                        file_path_str = ':'.join(file_parts)
                        try:
                            page_num = int(parts[page_idx])
                            text = ':'.join(parts[page_idx + 1:])

                            matches.append(GrepMatch(
                                file=file_path_str,
                                page=page_num,
                                text=text
                            ))
                            files_found.add(file_path_str)
                        except ValueError:
                            # Skip malformed lines
                            continue

        # 8. Return output
        output = GrepPDFOutput(
            matches=matches,
            total=len(matches),
            truncated=len(matches) >= input_data.max_count,
            files_searched=len(files_found) if files_found else 0
        )
        return output.model_dump_json(indent=2), []

    except PermissionError as e:
        error = GrepPDFError(
            error="PERMISSION_DENIED",
            message=f"Permission denied: {str(e)}"
        )
        return error.model_dump_json(indent=2), []
    except Exception as e:
        error = GrepPDFError(
            error="INTERNAL_ERROR",
            message=f"Error during search: {type(e).__name__}: {str(e)}"
        )
        return error.model_dump_json(indent=2), []