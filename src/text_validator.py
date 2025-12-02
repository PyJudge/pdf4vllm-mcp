"""
Text corruption detection utility
Detect PDF structure corruption with pdfminer.six → Provide corrupted pages as images
"""
import re
import io
import logging
from contextlib import redirect_stderr
from typing import Tuple
from pdfminer.high_level import extract_text

from src.config import config

logger = logging.getLogger(__name__)


def check_pdf_corruption_with_pdfminer(pdf_path: str, page_num: int) -> Tuple[bool, int]:
    """
    Check PDF structure corruption with pdfminer.six

    PDF is considered corrupted if pdfminer issues "Ignoring wrong pointing object" warnings

    Args:
        pdf_path: PDF file path
        page_num: Page number (1-indexed)

    Returns:
        (is_corrupted, warning_count)
    """
    # Capture stderr using thread-safe contextlib
    captured_stderr = io.StringIO()

    try:
        with redirect_stderr(captured_stderr):
            # Attempt text extraction with pdfminer
            extract_text(pdf_path, page_numbers=[page_num - 1])
    except Exception as e:
        logger.debug(f"PDF text extraction failed for {pdf_path} page {page_num}: {e}")

    warnings = captured_stderr.getvalue()

    # Count "Ignoring" warnings
    warning_count = warnings.count("Ignoring")

    # Consider corrupted if 3 or more warnings
    is_corrupted = warning_count >= 3

    return is_corrupted, warning_count


def is_text_corrupted(text: str, threshold: float = None) -> Tuple[bool, float]:
    """
    Auto-detect if text is corrupted

    Detection criteria:
    1. (cid:xxx) pattern exists
    2. Known corrupted character patterns (‹, Œ, Ù, Ú, ñ, û, Å, Æ, Ç, È, etc.)
    3. Special character ratio > threshold (from config.corruption_threshold)

    Args:
        text: Text to check
        threshold: Corruption detection threshold (0.0-1.0), defaults to config.corruption_threshold

    Returns:
        (is_corrupted, corruption_ratio)
    """
    # Use config value if threshold not explicitly provided
    if threshold is None:
        threshold = config.corruption_threshold
    if not text or len(text.strip()) == 0:
        return False, 0.0

    # Sample for inspection (first 500 characters)
    sample = text[:500]
    sample_len = len(sample)

    if sample_len == 0:
        return False, 0.0

    # 1. Check (cid:xxx) pattern (immediately consider corrupted)
    cid_pattern = re.findall(r'\(cid:\d+\)', sample)
    if len(cid_pattern) > 3:  # 3 or more cid patterns
        return True, 1.0

    # 2. Known corrupted character patterns
    known_corrupted_chars = set([
        '‹', 'Œ', 'Ù', 'Ú', 'Û', 'Ü', 'ñ', 'û', 'ý', 'Þ',
        'Å', 'Æ', 'Ç', 'È', 'É', 'Ê', 'Ë', 'Î', 'Ï',
        'Ñ', 'Ò', 'Ó', 'Ô', 'Õ', 'Ö', 'ß', 'à', 'á', 'â',
        'ã', 'ä', 'å', 'æ', 'ç', 'è', 'é', 'ê', 'ë', 'ì',
        'í', 'î', 'ï', 'ð', 'ò', 'ó', 'ô', 'õ', 'ö', 'ø',
        'ù', 'ú', 'Ý', 'þ', 'ÿ', '¡', '¢', '£', '¤', '¥',
        '¦', '§', '¨', '©', 'ª', '«', '¬', '®', '¯', '°',
        '±', '²', '³', '´', 'µ', '¶', '·', '¸', '¹', 'º',
        '»', '¼', '½', '¾', '¿', 'À', 'Á', 'Â', 'Ã', 'Ä'
    ])

    known_corrupted_count = sum(1 for c in sample if c in known_corrupted_chars)

    if known_corrupted_count > sample_len * 0.05:  # 5% or more
        return True, known_corrupted_count / sample_len

    # 2.5. Check consecutive special character patterns
    # Patterns like "#$%&#'()#*+" indicate corrupted text
    consecutive_special = re.findall(r'[#$%&*+/<=>@\\^`|~]{3,}', sample)
    if len(consecutive_special) >= 3:  # 3 or more occurrences of 3+ consecutive special chars
        return True, 0.8

    # Also check mixed special char sequences (e.g., "#'()#*+")
    mixed_special = re.findall(r'(?:[#$%&*+/<=>@\\^`|~\'\"()]+){5,}', sample)
    if len(mixed_special) >= 2:  # 2 or more occurrences of 5+ mixed special chars
        return True, 0.7

    # 3. Check general special character ratio
    corrupted_chars = 0
    valid_chars = set('.,!?()[]{}"\'\n\t -:;')  # Allowed punctuation
    # ASCII special characters that indicate corruption when frequent
    suspicious_ascii = set('#$%&*+/<=>@\\^`|~')

    for char in sample:
        char_code = ord(char)

        # ASCII range
        if char_code <= 127:
            # Count suspicious special characters
            if char in suspicious_ascii:
                corrupted_chars += 1
            continue

        # Korean ranges
        if '\uAC00' <= char <= '\uD7A3':  # Hangul syllables
            continue
        if '\u1100' <= char <= '\u11FF':  # Hangul jamo
            continue
        if '\u3131' <= char <= '\u318E':  # Hangul compatibility jamo
            continue

        # Chinese characters
        if '\u4E00' <= char <= '\u9FFF':
            continue

        # General European characters (normal range only)
        if '\u00C0' <= char <= '\u00FF':  # Latin-1 Supplement
            # But count if it's a known corrupted character
            if char in known_corrupted_chars:
                corrupted_chars += 1
            continue

        # Allowed special characters
        if char in valid_chars:
            continue

        # Rest are suspicious characters
        corrupted_chars += 1

    # Calculate corruption ratio
    corruption_ratio = corrupted_chars / sample_len

    # Corrupted if above threshold
    is_corrupted = corruption_ratio > threshold

    return is_corrupted, corruption_ratio



def get_corruption_message(corruption_ratio: float) -> str:
    """
    Generate message based on corruption ratio

    Args:
        corruption_ratio: Corruption ratio (0.0-1.0)

    Returns:
        User-friendly message
    """
    percentage = int(corruption_ratio * 100)

    if corruption_ratio > 0.5:
        return f"Text severely corrupted ({percentage}% corrupted). Provided as page image."
    elif corruption_ratio > 0.25:
        return f"Text partially corrupted ({percentage}% corrupted). Provided as page image."
    else:
        return f"Text quality is good ({percentage}% corrupted)."
