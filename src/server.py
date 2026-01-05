"""
PDF MCP for vLLM - Block-based PDF extraction for LLM consumption

Exports PDFs as structured content blocks (text, tables, images) that LLMs can easily process.
Preserves document reading order and handles corrupted text automatically.

Provides two tools:
1. list_pdfs: List all PDF files recursively from working directory
2. read_pdf: Extract PDF content as ordered blocks with intelligent limits
"""
import asyncio
import sys
import logging
from pathlib import Path

# Configure logging to file for MCP server debugging
log_file = Path.home() / '.pdf4vllm_mcp_debug.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(log_file), mode='a'),
        logging.StreamHandler(sys.stderr)
    ]
)

# Add project directory to sys.path (executable from anywhere)
SCRIPT_DIR = Path(__file__).parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Imports after sys.path modification (intentional)
from mcp.server import Server  # noqa: E402
from mcp.server.stdio import stdio_server  # noqa: E402
from mcp.server.fastmcp.utilities.types import Image  # noqa: E402
from mcp.types import Tool, TextContent, CallToolResult  # noqa: E402

from src.pdf_tools import list_pdfs_handler, read_pdf_handler, grep_pdf_handler  # noqa: E402
from src.config import config  # noqa: E402


# Create MCP server instance
server = Server("pdf4vllm")


def _get_read_pdf_description() -> str:
    """Generate read_pdf description based on config extraction mode"""
    mode = config.default_extraction_mode
    base = f"Read PDF content. Always prefer this over cat or file read for PDF files. Limits: {config.max_pages_per_request} pages per request."

    if mode == "auto":
        return (
            f"{base} "
            f"Works with both text and scanned documents. "
            f"Use 'image_only' to see actual page layout, or 'text_only' for pure text."
        )
    elif mode == "text_only":
        return (
            f"{base} "
            f"Extracts text and tables only. "
            f"Use 'image_only' to see actual page layout, or 'auto' for smart detection."
        )
    elif mode == "image_only":
        return (
            f"{base} "
            f"Returns page images for visual analysis. "
            f"Use 'text_only' for pure text extraction, or 'auto' for smart detection."
        )
    else:
        return base


@server.list_tools()
async def list_tools() -> list[Tool]:
    """
    List available tools for PDF MCP for vLLM
    """
    return [
        Tool(
            name="list_pdfs",
            description=(
                "Find PDF files in a directory. Use name_pattern for glob filtering (e.g., '*report*'). "
                "Returns name, path, pages for each PDF. Use the returned 'path' directly with read_pdf."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "working_directory": {
                        "type": "string",
                        "description": "Working directory to search (relative or absolute path, default: current directory)",
                        "default": "."
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Whether to include subdirectories",
                        "default": True
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": f"Maximum recursion depth (default: {config.max_recursion_depth})",
                        "default": config.max_recursion_depth,
                        "minimum": 1
                    },
                    "name_pattern": {
                        "type": "string",
                        "description": "Glob pattern for filename filtering (e.g., '*report*', 'doc_202?.pdf')"
                    }
                }
            }
        ),
        Tool(
            name="read_pdf",
            description=_get_read_pdf_description(),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "PDF file path (relative or absolute path)"
                    },
                    "start_page": {
                        "type": "integer",
                        "description": "Start page (1-indexed, inclusive)",
                        "default": 1,
                        "minimum": 1
                    },
                    "end_page": {
                        "type": "integer",
                        "description": "End page (1-indexed, inclusive). None = last page",
                        "default": None,
                        "minimum": 1
                    },
                    "extraction_mode": {
                        "type": "string",
                        "description": (
                            "Content extraction mode:\n"
                            "- 'auto' (default): Smart detection - extract text/tables, add page image only if corrupted\n"
                            "- 'text_only': Extract text/tables only, no images\n"
                            "- 'image_only': Skip text extraction, provide only full page images"
                        ),
                        "enum": ["auto", "text_only", "image_only"],
                        "default": config.default_extraction_mode
                    },
                    "filter_header_footer": {
                        "type": "boolean",
                        "description": "Whether to filter out header/footer images (top/bottom 6% of page)",
                        "default": True
                    },
                    "crop_images": {
                        "type": "boolean",
                        "description": "Whether to crop images to max_image_dimension",
                        "default": True
                    },
                    "max_image_dimension": {
                        "type": "integer",
                        "description": f"Maximum image dimension in pixels (default: {config.max_image_dimension}, A4 height)",
                        "default": config.max_image_dimension,
                        "minimum": 100,
                        "maximum": 4096
                    },
                    "page_image_dpi": {
                        "type": "integer",
                        "description": f"DPI for page image rendering (default: {config.page_image_dpi})",
                        "default": config.page_image_dpi,
                        "minimum": 50,
                        "maximum": 300
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="grep_pdf",
            description=(
                "Search text in PDFs. Use instead of read_pdf to find specific text. "
                "Returns matching lines with page numbers. "
                "NOTE: No page limit (unlike read_pdf's 10-page limit)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Search pattern (regex by default)"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Specific PDF file. If not provided, searches ALL PDFs in working_directory"
                    },
                    "working_directory": {
                        "type": "string",
                        "description": "Base directory for search (only used when file_path is not provided)",
                        "default": "."
                    },
                    "ignore_case": {
                        "type": "boolean",
                        "description": "Case-insensitive search",
                        "default": False
                    },
                    "fixed_strings": {
                        "type": "boolean",
                        "description": "Treat pattern as literal string, not regex",
                        "default": False
                    },
                    "context": {
                        "type": "integer",
                        "description": "Lines of context before/after match (0-5, default: 2)",
                        "default": 2,
                        "minimum": 0,
                        "maximum": 5
                    },
                    "max_count": {
                        "type": "integer",
                        "description": "Maximum matches to return (1-100)",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Include subdirectories when searching directory",
                        "default": True
                    },
                    "start_page": {
                        "type": "integer",
                        "description": "Start page (1-indexed, inclusive)",
                        "default": 1,
                        "minimum": 1
                    },
                    "end_page": {
                        "type": "integer",
                        "description": "End page (1-indexed, inclusive). None = last page",
                        "minimum": 1
                    }
                },
                "required": ["pattern"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    """
    Execute a tool by name with given arguments

    Args:
        name: Tool name ("list_pdfs" or "read_pdf")
        arguments: Tool arguments

    Returns:
        CallToolResult with content list
        - TextContent: JSON response with image placeholders
        - ImageContent: Actual image data (sent as proper MCP ImageContent)
    """
    if name == "list_pdfs":
        result_json, images = await list_pdfs_handler(arguments)
        return CallToolResult(
            content=[TextContent(type="text", text=result_json)],
            isError=False
        )

    elif name == "read_pdf":
        result_json, images = await read_pdf_handler(arguments)

        # Build response: TextContent first, then ImageContent for each image
        # Using Image wrapper for proper MCP-compliant image serialization
        content = [TextContent(type="text", text=result_json)]

        for img in images:
            # Create Image wrapper with raw bytes and format
            # Image.to_image_content() handles base64 encoding automatically
            image_wrapper = Image(data=img["data"], format=img["format"])
            content.append(image_wrapper.to_image_content())

        return CallToolResult(
            content=content,
            isError=False
        )

    elif name == "grep_pdf":
        result_json, images = await grep_pdf_handler(arguments)
        return CallToolResult(
            content=[TextContent(type="text", text=result_json)],
            isError=False
        )

    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    """
    Main entry point for the PDF for vLLM MCP server

    Runs the server with stdio transport for inter-process communication
    """
    # Run stdio server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def run():
    """Synchronous entry point"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    run()