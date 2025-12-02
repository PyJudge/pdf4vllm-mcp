"""
Image processing utilities for PDF MCP server
Simplified algorithm: configurable filtering + maximum size limit
"""
from PIL import Image
import io
from typing import Tuple, Optional
from .config import config


def crop_image_to_max_dimension(
    image_bytes: bytes,
    max_dimension: int = None
) -> Tuple[Optional[bytes], int, int]:
    """
    Simplified image scaling

    Algorithm:
    1. If either dimension < config.min_image_dimension → discard (return None)
    2. Scale down large images only (maintain aspect ratio)
    3. Keep small images as is
    4. LANCZOS resampling (high quality)

    Args:
        image_bytes: Original image as bytes
        max_dimension: Maximum width or height (default: config.max_image_dimension)

    Returns:
        Tuple of (scaled_image_bytes, new_width, new_height)
        or None if image is too small
    """
    # Use config values as defaults
    if max_dimension is None:
        max_dimension = config.max_image_dimension
    min_dim = config.min_image_dimension

    try:
        # Load image
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size

        # Discard if either dimension is below minimum
        if width < min_dim or height < min_dim:
            return None, width, height

        # Return as is if already small enough
        if width <= max_dimension and height <= max_dimension:
            return image_bytes, width, height

        # Scale down large images only (maintain aspect ratio)
        scale = min(max_dimension / width, max_dimension / height)
        new_width = int(width * scale)
        new_height = int(height * scale)

        # LANCZOS resampling (high quality downscaling)
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Convert back to bytes
        output = io.BytesIO()
        img_format = img.format or 'PNG'

        # Save with quality from config
        if img_format.upper() in ['JPEG', 'JPG']:
            img_resized.save(output, format='JPEG', quality=config.jpeg_quality)
        else:
            img_resized.save(output, format=img_format)

        # Close images to free resources
        img.close()
        img_resized.close()

        return output.getvalue(), new_width, new_height

    except Exception:
        # Return original if processing fails
        min_dim = config.min_image_dimension
        try:
            img = Image.open(io.BytesIO(image_bytes))
            width, height = img.size
            # Check size
            if width < min_dim or height < min_dim:
                return None, width, height
            return image_bytes, width, height
        except Exception:
            return None, 0, 0


def is_header_footer_image(img_data: dict) -> bool:
    """
    Image filtering

    Filtering conditions:
    1. If either dimension < config.min_image_dimension → discard
    2. Extreme aspect ratio (> config.max_aspect_ratio) → discard (dividing lines, etc.)

    Args:
        img_data: Dictionary with 'width', 'height', 'image' keys

    Returns:
        True if image should be filtered out
    """
    try:
        width = img_data.get("width", 0)
        height = img_data.get("height", 0)
        min_dim = config.min_image_dimension

        # 1. Discard if either dimension is below minimum size
        if width < min_dim or height < min_dim:
            return True

        # 2. Extreme aspect ratio filter (configurable, 0=disabled)
        if config.max_aspect_ratio > 0 and width > 0 and height > 0:
            aspect_ratio = max(width / height, height / width)
            if aspect_ratio > config.max_aspect_ratio:
                return True  # Consider as dividing line if > 15:1

        return False

    except Exception:
        return False
