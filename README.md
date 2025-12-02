# pdf4vllm

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/pdf4vllm-mcp.svg)](https://pypi.org/project/pdf4vllm-mcp/)
[![Open in Gitpod](https://img.shields.io/badge/Gitpod-Open-orange?logo=gitpod)](https://gitpod.io/#https://github.com/PyJudge/pdf4vllm-mcp)

PDF reading MCP server optimized for vision LLMs.

<!-- mcp-name: io.github.PyJudge/pdf4vllm -->

<details>
<summary><b>한국어</b></summary>

## 문제

| 방식 | 문제점 |
|------|--------|
| 텍스트 추출 | 인코딩 깨짐 → 쓰레기 출력, 이미지-텍스트 순서 뒤섞임 |
| 이미지 변환 | 토큰 폭발 (특히 페이지 많을 때) |

## 해결

pdf4vllm은 **PDF가 지저분하다고 가정**합니다.

- 텍스트 손상 자동 감지 → 이미지로 자동 전환
- 읽기 순서 보존 (텍스트 → 표 → 이미지 블록 순서대로)
- 페이지 제한으로 컨텍스트 오버플로우 방지
- 불필요한 이미지 자동 필터링 (로고, 선, 헤더/푸터)

## 설치

```bash
pip install pdf4vllm-mcp
# 또는
uvx pdf4vllm-mcp
```

## Claude Desktop 설정

```bash
git clone https://github.com/PyJudge/pdf4vllm-mcp.git
cd pdf4vllm-mcp
python scripts/install_mcp.py
```

또는 직접 설정 (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "pdf4vllm": {
      "command": "/python/경로",
      "args": ["/pdf4vllm-mcp/경로/src/server.py"]
    }
  }
}
```

## 추출 모드

| 모드 | 설명 |
|------|------|
| `auto` (기본) | 텍스트 추출 시도 → 손상 감지 시 이미지로 전환 |
| `text_only` | 텍스트/표만 추출, 이미지 없음 |
| `image_only` | 페이지를 이미지로만 렌더링 |

</details>

---

## Problem

| Approach | Issue |
|----------|-------|
| Text extraction | Encoding corruption → garbage output, mixed text-image ordering |
| Image conversion | Token explosion (especially with many pages) |

## Solution

pdf4vllm **assumes PDFs are messy**.

- Auto-detects text corruption → switches to image automatically
- Preserves reading order (text → table → image blocks in sequence)
- Page limits prevent context overflow
- Filters unnecessary images (logos, lines, headers/footers)

```
PDF Input
    ↓
Corruption Detection (pdfminer.six + pattern analysis)
    ↓
┌─────────────┬─────────────┐
│  Corrupted  │    Clean    │
│  → Image    │  → Text +   │
│    only     │    Tables + │
│             │    Images   │
└─────────────┴─────────────┘
    ↓
Ordered Blocks (JSON)
```

## Install

```bash
pip install pdf4vllm-mcp
# or run without installing
uvx pdf4vllm-mcp
```

## Claude Desktop Setup

```bash
git clone https://github.com/PyJudge/pdf4vllm-mcp.git
cd pdf4vllm-mcp
python scripts/install_mcp.py
```

Or manually edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pdf4vllm": {
      "command": "/path/to/python",
      "args": ["/path/to/pdf4vllm-mcp/src/server.py"]
    }
  }
}
```

## Claude Code Setup

Create `.mcp.json` in your project:

```json
{
  "mcpServers": {
    "pdf4vllm": {
      "command": "uvx",
      "args": ["pdf4vllm-mcp"]
    }
  }
}
```

## Extraction Modes

| Mode | Description |
|------|-------------|
| `auto` (default) | Try text extraction → switch to image if corrupted |
| `text_only` | Text/tables only, no images |
| `image_only` | Render pages as images only |

## Output Format

```json
{
  "pages": [
    {
      "page_number": 1,
      "content_blocks": [
        {"type": "text", "content": "..."},
        {"type": "table", "content": "| A | B |"},
        {"type": "image", "content": "[IMAGE_0]"}
      ]
    }
  ]
}
```

When text is corrupted:
```json
{
  "page_number": 2,
  "content_blocks": [],
  "text_corrupted": true,
  "page_image": "[IMAGE_1]"
}
```

## Configuration

`config.json` or environment variables:

```json
{
  "max_pages_per_request": 10,
  "max_image_dimension": 842,
  "page_image_dpi": 100
}
```

```bash
export PDF_MAX_PAGES=20
export PDF_PAGE_IMAGE_DPI=150
```

## Test Server

```bash
pip install pdf4vllm-mcp[test]
python test_server.py
# → http://localhost:8000
```

## License

MIT

---

[GitHub](https://github.com/PyJudge/pdf4vllm-mcp) · [PyPI](https://pypi.org/project/pdf4vllm-mcp/)
