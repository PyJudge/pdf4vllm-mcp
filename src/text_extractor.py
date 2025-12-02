"""
Text extraction utility
Extract only text excluding table regions to prevent duplication
"""
from typing import List, Dict


def extract_non_table_text_regions(page, table_bboxes: List[tuple]) -> List[Dict]:
    """
    Extract text regions excluding table areas

    Split page by table bboxes and extract text from each region

    Args:
        page: pdfplumber page object
        table_bboxes: List of table bboxes [(x0, top, x1, bottom), ...]

    Returns:
        [{'top': float, 'text': str}, ...] Text by region
    """
    if not table_bboxes:
        # If no tables, extract full text
        text = page.extract_text()
        return [{'top': 0, 'text': text}] if text else []

    # Sort bboxes by top coordinate
    sorted_tables = sorted(table_bboxes, key=lambda b: b[1])

    text_regions = []
    page_height = page.height
    page_width = page.width

    # Region before first table
    first_table = sorted_tables[0]
    if first_table[1] > 0:  # If top is greater than 0
        above_bbox = (0, 0, page_width, first_table[1])
        above_region = page.within_bbox(above_bbox)
        text = above_region.extract_text()
        if text and text.strip():
            text_regions.append({'top': 0, 'text': text})

    # Regions between tables
    for i in range(len(sorted_tables) - 1):
        current_table = sorted_tables[i]
        next_table = sorted_tables[i + 1]

        # Between current table end and next table start
        between_bbox = (0, current_table[3], page_width, next_table[1])

        if next_table[1] > current_table[3]:  # If there's space
            between_region = page.within_bbox(between_bbox)
            text = between_region.extract_text()
            if text and text.strip():
                text_regions.append({'top': current_table[3], 'text': text})

    # Region after last table
    last_table = sorted_tables[-1]
    if last_table[3] < page_height:
        below_bbox = (0, last_table[3], page_width, page_height)
        below_region = page.within_bbox(below_bbox)
        text = below_region.extract_text()
        if text and text.strip():
            text_regions.append({'top': last_table[3], 'text': text})

    return text_regions
