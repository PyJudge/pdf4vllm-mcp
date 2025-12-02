"""
Content ordering utility
Sort text, tables, and images in original document order
"""
from typing import List, Dict


def order_content_blocks(
    text_regions: List[Dict],
    tables: List[Dict],
    images: List[Dict]
) -> List[Dict]:
    """
    Sort text regions, tables, and images by top coordinate in reading order

    Args:
        text_regions: Text regions excluding tables [{'top': float, 'text': str}, ...]
        tables: Table info [{'top': float, 'markdown': str}, ...]
        images: Image info [{'top': float, 'image_data': str}, ...]

    Returns:
        Sorted content blocks
    """
    all_blocks = []

    # Add text regions
    for region in text_regions:
        all_blocks.append({
            'type': 'text',
            'top': region['top'],
            'content': region['text'],
            'image': None
        })

    # Add tables
    for table_info in tables:
        all_blocks.append({
            'type': 'table',
            'top': table_info['top'],
            'content': table_info['markdown'],
            'image': None
        })

    # Add images (image_data is base64 string)
    for img_info in images:
        all_blocks.append({
            'type': 'image',
            'top': img_info['top'],
            'content': img_info['image_data'],  # base64 string
            'image': None
        })

    # Sort by top coordinate (top to bottom)
    all_blocks.sort(key=lambda x: x['top'])

    # Add position
    for block in all_blocks:
        block['position'] = block['top']
        del block['top']  # Replace top with position

    return all_blocks


def merge_adjacent_text_blocks(blocks: List[Dict]) -> List[Dict]:
    """
    Merge adjacent text blocks into one
    (Simplified since text excluding tables is already merged by region)

    Args:
        blocks: content blocks

    Returns:
        Merged blocks
    """
    if not blocks:
        return []

    # Text excluding tables is already extracted by region
    # No additional merging needed, return as is
    return blocks
