# PDF MCP for vLLM

> **vLLM reads PDF files automatically.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

**[English](./README.md)** | **[한국어](./README.ko.md)**

---

## The Problem

Feeding PDFs to vLLM is really not easy.
```
Read as text?
Corrupted text encoding    → garbage
Documents with mixed text and images → Text and images don't match up

Read as image?
Massive token usage     → Especially with many pages? Context explosion
```

---

## The Solution

**Other tools assume PDFs are clean.**
**PDF MCP for vLLM assumes PDFs are messy. PDF MCP for vLLM and vLLM handle it automatically.**


```
┌─────────────────────────────────────────────────┐
│  PDF Input                                       │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  Corruption Detection                            │
│  • pdfminer.six warnings                         │
│  • Character pattern analysis                    │
│  • Automatic fallback decision                   │
└──────────────────┬──────────────────────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
    Corrupted?           Clean?
    Image only?
         │                   │
         ▼                   ▼
  ┌──────────┐        ┌──────────┐
  │ Vision   │        │ Text     │
  │ Mode     │        │ Mode     │
  │          │        │          │
  │ Page     │        │ Text     │
  │ Image    │        │ Tables   │
  │ Only     │        │ Images   │
  └─────┬────┘        └────┬─────┘
        │                  │
        └────────┬─────────┘
                 │
                 ▼
        ┌────────────────┐
        │ Ordered Blocks │
        │ • Text         │
        │ • Tables (MD)  │
        │ • Images       │
        │ • Page Images  │
        └────────────────┘
                 │
                 ▼
        ┌────────────────┐
        │ JSON Output    │
        │ Clean          │
        │ Structured     │
        │ LLM-Ready      │
        └────────────────┘
```

### Structured Blocks = Better Understanding

PDF MCP for vLLM preserves **reading order** with typed blocks:

```
Page 1: Text → Table → Text → Image → Text
         ↓
[
  {type: "text", content: "Introduction..."},
  {type: "table", content: "| Item | Amount |"},
  {type: "text", content: "Analysis..."},
  {type: "image", content: "base64..."},
  {type: "text", content: "Conclusion..."}
]
```

**vLLM reads naturally**, not fighting scrambled content.

---

### vLLM and PDF MCP for vLLM handle it automatically.

```
100-page PDF requested
↓
PDF MCP for vLLM: "Too large! Try pages 1-10, 11-20, ..."
↓
LLM makes multiple smart requests
↓
All content processed without context overflow
+ Resolution adjustment included (100dpi default)
```

```
User: "What if I change the background color of scanned_contract.pdf to red?"

vLLM: Calls with extraction_mode="image_only"

PDF MCP for vLLM:
  - Skips useless text extraction attempt
  - Renders each page as image
  - Sends directly to vision

Result: Fast, accurate, no waste
```

---


### Smart Corruption Handling

```
Automatically detects PDFs that can't be read as text
↓
Automatically sends as image
vLLM reads perfectly with vision
```

**Before PDF MCP for vLLM:**
```json
{
  "text": "�㍻��㍺�������..."  // 5000 tokens of garbage
}
```

**With PDF MCP for vLLM (Auto Mode):**
```json
{
  "content_blocks": [],           // Garbage blocked
  "page_image": "base64...",      // Clean image for vision
  "text_corrupted": true          // LLM knows why
}
```

### Intelligent Image Processing

```
Extract all images from PDF
↓
Filter: Remove decorative junk (< 28px)
Filter: Remove extreme aspect ratios (> 15:1 ratio lines)
Filter: Remove headers/footers
↓
Crop: Scale down to A4 height (842px default)
DPI limit (100dpi default)
↓
Result: Only meaningful images, LLM-optimized sizes
```

**Before:** 50 images including logos, lines, borders
**After:** 5 meaningful content images

---

## See It In Action

```bash
python test_server.py
```

**Visual test interface shows:**
- Corrupted text detection in real-time
- How blocks are ordered
- Inline image rendering
- Markdown table rendering
- Mode switching effects

**Test with your own PDFs** before deploying to LLM.

---

## Quick Start

### Installation

**Method 1: PyPI (Easiest)**
```bash
pip install pdf4vllm-mcp
# With test server: pip install pdf4vllm-mcp[test]
```

**Method 2: Git Clone**
```bash
git clone https://github.com/PyJudge/pdf4vllm-mcp.git
cd pdf4vllm-mcp
pip install -e .
```

### Test Locally

```bash
python test_server.py
# → http://localhost:8000
```

**See it working:**
- Upload a corrupted PDF → Watch it auto-detect and switch to image
- Upload a clean PDF → See structured text blocks
- Try all 3 modes → Visual rendering shows the difference

### MCP Integration

#### Easy Install (Recommended)

```bash
git clone https://github.com/PyJudge/pdf4vllm-mcp.git
cd pdf4vllm-mcp
pip install -e .

# Cross-platform (Windows/macOS/Linux)
python scripts/install_mcp.py

# macOS/Linux only
./scripts/install_mcp.sh
```

The script automatically:
- Detects your OS (Windows/macOS/Linux)
- Finds Python path
- Creates Claude Desktop config with correct settings
- Backs up existing config

Then restart Claude Desktop.

#### Claude Code (CLI)

Create `.mcp.json` in your project directory:

```json
{
  "mcpServers": {
    "pdf4vllm": {
      "command": "python",
      "args": ["-m", "src.server"]
    }
  }
}
```

---

#### Manual Install (Claude Desktop)

**Configuration:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "pdf4vllm": {
      "command": "/path/to/your/python",
      "args": ["/full/path/to/pdf4vllm-mcp/src/server.py"]
    }
  }
}
```

#### Complete Example (Conda)

```json
{
  "mcpServers": {
    "pdf4vllm": {
      "command": "/opt/anaconda3/envs/pdfmcp/bin/python",
      "args": ["/Users/username/pdf4vllm-mcp/src/server.py"]
    }
  }
}
```

#### Complete Example (Homebrew)

```json
{
  "mcpServers": {
    "pdf4vllm": {
      "command": "/usr/local/bin/python3",
      "args": ["/Users/username/pdf4vllm-mcp/src/server.py"]
    }
  }
}
```

> **Important:**
> - Use **absolute paths** for both `command` and `args`

#### Restart Claude Desktop

Completely quit and restart Claude Desktop to load the MCP server.

#### Troubleshooting

**"server disconnected"**
- Wrong Python path or server.py path. Verify both exist

**Check logs:** `~/Library/Logs/Claude/mcp-server-pdf4vllm.log`

---

## Real-World Examples

### Example 1: Corrupted Legal Document

```
User: "Read court_document.pdf"

PDF MCP for vLLM Auto Mode:
  1. Detects: 87% text corruption
  2. Blocks: Garbage text from reaching LLM
  3. Provides: Clean page image
  4. Result: LLM reads with vision, perfect understanding

Tokens saved: ~15,000 (blocked corrupted text)
Accuracy: 100% (vision) vs 0% (garbage text)
```

### Example 2: 200-Page Report

```
User: "Read annual_report.pdf"

PDF MCP for vLLM:
  "PAGE_LIMIT_EXCEEDED: Requested 200 pages exceeds limit (10).

   Suggested ranges:
   - Pages 1-10 (10 pages, ~5 images)
   - Pages 11-20 (10 pages, ~8 images)
   - Pages 21-30 (10 pages, ~12 images)
   - Pages 31-40 (10 pages, ~6 images)
   - Pages 41-50 (10 pages, ~15 images)"

User: "Read pages 1-10"
PDF MCP for vLLM: Extracts first section

User: "Read pages 11-20"
PDF MCP for vLLM: Extracts next section

Result: No context explosion, systematic reading
```

---

## Configuration

Create `config.json`:

```json
{
  "max_pages_per_request": 20,        // Your context size
  "max_images_per_request": 100,      // Your needs
  "max_image_dimension": 1024,        // Higher quality
  "min_image_dimension": 50,          // More aggressive filtering
  "max_aspect_ratio": 10,             // Stricter line filtering
  "page_image_dpi": 150               // Higher DPI for vision
}
```

**Or use environment variables:**
```bash
export PDF_MAX_PAGES=20
export PDF_PAGE_IMAGE_DPI=150
```

---
## 3 Extraction Modes

Choose based on your PDF:

### Auto (Default) - PDF MCP for vLLM Decides

```python
extraction_mode: "auto"  # Smart detection
```

**What it does:**
1. Tries text extraction first
2. **Detects corruption automatically**
3. If corrupted → **Blocks garbage text** + **Adds page image**
4. If clean → Returns text normally

**Use when:** You don't know PDF quality (most cases)

---

### Text Only - Fast & Lightweight

```python
extraction_mode: "text_only"
```

**What it does:**
- Extract text + tables only
- Never add page images
- Minimal tokens

**Use when:** You KNOW the PDF is clean

---

### Image Only - Vision First

```python
extraction_mode: "image_only"
```

**What it does:**
- Skip text extraction entirely
- Render pages as images only
- Direct to LLM vision

**Use when:** Scanned PDFs, known corrupted text

---



---

## API

### `read_pdf`

**One parameter that matters:**

```json
{
  "file_path": "document.pdf",
  "extraction_mode": "auto"  // That's it. Everything else has smart defaults.
}
```

**Advanced options (when you need them):**

```json
{
  "file_path": "document.pdf",
  "start_page": 1,               // Default: 1
  "end_page": 10,                // Default: last page
  "extraction_mode": "auto",     // Default: "auto"
  "filter_header_footer": true,  // Default: true
  "crop_images": true,           // Default: true
  "max_image_dimension": 842,    // Default: 842 (A4 height)
  "page_image_dpi": 100          // Default: 100
}
```

---

## License

**MIT**

**Dependencies:**
- pypdfium2: Apache 2.0 / BSD
- pikepdf: MPL 2.0
- pdfplumber: MIT
- Pillow: HPND
- pydantic: MIT

---

<div align="center">

**PDF MCP for vLLM v1.0**

Don't fight PDFs. Let PDF MCP for vLLM handle it.

[GitHub](https://github.com/PyJudge/pdf4vllm-mcp) · [Issues](https://github.com/PyJudge/pdf4vllm-mcp/issues) · [Discussions](https://github.com/PyJudge/pdf4vllm-mcp/discussions)

</div>