"""
Filename similarity matching utility
Suggest similar files when a non-existent file is requested
"""
from pathlib import Path
from typing import List
import difflib
import re


def extract_keywords(filename: str) -> List[str]:
    """
    Extract keywords from filename

    Separates Korean, English, and numbers as search keywords

    Args:
        filename: Filename (without extension)

    Returns:
        List of keywords
    """
    keywords = []

    # Extract Korean words (consecutive Korean characters)
    korean = re.findall(r'[가-힣]+', filename)
    keywords.extend(korean)

    # Extract English words (consecutive English characters)
    english = re.findall(r'[a-z]+', filename.lower())
    keywords.extend(english)

    # Extract numbers (consecutive digits)
    numbers = re.findall(r'\d+', filename)
    keywords.extend(numbers)

    return keywords


def find_similar_pdfs(
    requested_path: str,
    max_suggestions: int = 3,
    cutoff: float = 0.3
) -> List[str]:
    """
    Find PDF files similar to the requested file

    Algorithm:
    1. Extract keywords from request path
    2. Search PDFs in directories
    3. First filter by keyword inclusion
    4. Second sort by filename similarity (difflib)
    5. Return top N matches

    Args:
        requested_path: Requested file path
        max_suggestions: Maximum number of suggestions
        cutoff: Minimum similarity (0.0-1.0)

    Returns:
        List of similar PDF file paths (relative to current directory)
    """
    requested = Path(requested_path)
    requested_name = requested.stem.lower()  # Filename without extension (lowercase)

    # Extract keywords (separate Korean, English, numbers)
    keywords = extract_keywords(requested_name)

    # Directories to search
    search_dirs = []

    # 1. Directory of the requested path
    if requested.parent != Path('.'):
        parent_dir = Path.cwd() / requested.parent
        if parent_dir.exists() and parent_dir.is_dir():
            search_dirs.append(parent_dir)

    # 2. Current directory
    search_dirs.append(Path.cwd())

    # 3. sample_pdfs directory (default search)
    sample_dir = Path.cwd() / "sample_pdfs"
    if sample_dir.exists() and sample_dir.is_dir():
        search_dirs.append(sample_dir)

    # Collect PDF files
    all_pdfs = []
    seen_paths = set()

    for search_dir in search_dirs:
        try:
            # Search directory and 1 level down only
            for pdf_path in search_dir.glob("*.pdf"):
                if pdf_path.is_file() and str(pdf_path) not in seen_paths:
                    all_pdfs.append(pdf_path)
                    seen_paths.add(str(pdf_path))

            # 1 level subdirectories
            for pdf_path in search_dir.glob("*/*.pdf"):
                if pdf_path.is_file() and str(pdf_path) not in seen_paths:
                    all_pdfs.append(pdf_path)
                    seen_paths.add(str(pdf_path))
        except Exception:
            continue

    if not all_pdfs:
        return []

    # First filter: keyword inclusion
    keyword_matches = []
    for pdf_path in all_pdfs:
        pdf_name_lower = pdf_path.stem.lower()
        # If any keyword is included
        if any(kw in pdf_name_lower for kw in keywords if len(kw) >= 2):
            keyword_matches.append(pdf_path)

    # Use keyword matches if available, otherwise search all
    candidates = keyword_matches if keyword_matches else all_pdfs

    # Second sort: similarity
    pdf_names = [pdf.name.lower() for pdf in candidates]

    matches = difflib.get_close_matches(
        requested.name.lower(),  # Match with full filename
        pdf_names,
        n=max_suggestions * 2,  # Find more than needed
        cutoff=cutoff
    )

    if not matches:
        return []

    # Find actual paths of matched files
    similar_files = []
    seen_paths = set()  # Remove duplicates

    for match in matches:
        for pdf_path in all_pdfs:
            if pdf_path.name.lower() == match:
                # Relative path from current directory
                try:
                    relative = pdf_path.relative_to(Path.cwd())
                    path_str = str(relative)
                except ValueError:
                    path_str = str(pdf_path)

                # Remove duplicates
                if path_str not in seen_paths:
                    similar_files.append(path_str)
                    seen_paths.add(path_str)
                break

    return similar_files[:max_suggestions]


def get_file_not_found_message(
    requested_path: str,
    similar_files: List[str]
) -> str:
    """
    Generate FILE_NOT_FOUND error message

    Args:
        requested_path: Requested file path
        similar_files: List of similar files

    Returns:
        User-friendly error message
    """
    base_msg = f"PDF file not found: {requested_path}"

    if not similar_files:
        return base_msg + "\n\nCould not find similar PDF files in the current directory."

    suggestions = "\n".join([f"  - {f}" for f in similar_files])
    return (
        f"{base_msg}\n\n"
        f"Did you mean one of these?\n{suggestions}\n\n"
        f"Please verify the exact file path or use the list_pdfs tool to see available PDF files."
    )
