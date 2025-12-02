#!/usr/bin/env python3
"""Test image extraction directly without MCP"""
import asyncio
import json
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from src.pdf_tools import read_pdf_handler

async def main():
    print("Testing page 10 image extraction...")
    result_json, images = await read_pdf_handler({
        'file_path': 'sample_pdfs/기록.pdf',
        'start_page': 10,
        'end_page': 10,
        'extraction_mode': 'auto'
    })

    result = json.loads(result_json)

    print("\n=== JSON Response ===")
    print(f"Total images in JSON: {result.get('total_images', 0)}")
    if 'pages' in result and len(result['pages']) > 0:
        page = result['pages'][0]
        print(f"Text corrupted: {page.get('text_corrupted', False)}")
        print(f"Text hint: {page.get('text_hint', 'None')}")
        page_img = page.get('page_image', 'None')
        if page_img and page_img != 'None':
            print(f"Page image placeholder: {page_img}")
        else:
            print("Page image: None")

    print("\n=== Actual Images List ===")
    print(f"Images returned: {len(images)}")
    for i, img in enumerate(images):
        # New API uses 'format' and raw bytes instead of 'mimeType' and base64
        print(f"  Image {i}: format={img['format']}, data length: {len(img['data'])} bytes")

    if len(images) == 0:
        print("\nERROR: No images were extracted!")
    else:
        print(f"\nSUCCESS: {len(images)} images extracted")

if __name__ == '__main__':
    asyncio.run(main())