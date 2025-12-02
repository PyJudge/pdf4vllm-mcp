# PDF MCP for vLLM

> **vLLM이 알아서 PDF 파일을 읽습니다.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

**[English](./README.md)** | **[한국어](./README.ko.md)**

---

## 문제점

PDF를 vLLM에 넣는 건 정말 쉽지 않습니다.
```
글자로 읽으면? 
깨진 텍스트 인코딩    → 쓰레기
그림과 글이 섞여 있는 문서       → 글과 그림이 따로 노는 결과물

이미지로 읽으면? 
엄청난 토큰 사용     → 특히 페이지 많으면? 컨텍스트 폭발
```

---

## 해결책

**다른 도구는 PDF가 깨끗하다고 가정합니다.**
**PDF MCP for vLLM은 PDF가 지저분하다고 가정합니다. PDF MCP for vLLM과 vLLM이 알아서 합니다.**


```
┌─────────────────────────────────────────────────┐
│  PDF 입력                                        │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  손상 감지                                       │
│  • pdfminer.six 경고                            │
│  • 문자 패턴 분석                                │
│  • 자동 대체 결정                                │
└──────────────────┬──────────────────────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
    손상됨? 그림만?           깨끗함?
         │                   │
         ▼                   ▼
  ┌──────────┐        ┌──────────┐
  │ 비전     │        │ 텍스트   │
  │ 모드     │        │ 모드     │
  │          │        │          │
  │ 페이지   │        │ 텍스트   │
  │ 이미지   │        │ 표       │
  │ 만       │        │ 이미지   │
  └─────┬────┘        └────┬─────┘
        │                  │
        └────────┬─────────┘
                 │
                 ▼
        ┌────────────────┐
        │ 순서 있는 블록  │
        │ • 텍스트        │
        │ • 표 (MD)      │
        │ • 이미지        │
        │ • 페이지 이미지 │
        └────────────────┘
                 │
                 ▼
        ┌────────────────┐
        │ JSON 출력      │
        │ 깨끗함         │
        │ 구조화됨       │
        │ LLM 준비 완료  │
        └────────────────┘
```

### 구조화된 블록 = 더 나은 이해

PDF MCP for vLLM은 타입이 지정된 블록으로 **읽기 순서를 보존**합니다:

```
1페이지: 텍스트 → 표 → 텍스트 → 이미지 → 텍스트
         ↓
[
  {type: "text", content: "서론..."},
  {type: "table", content: "| 항목 | 금액 |"},
  {type: "text", content: "분석..."},
  {type: "image", content: "base64..."},
  {type: "text", content: "결론..."}
]
```

**vLLM이 자연스럽게 읽습니다**, 뒤죽박죽 콘텐츠와 싸우지 않습니다.

---

### vLLM과 PDF MCP for vLLM이 알아서 합니다.

```
100페이지 PDF 요청
↓
PDF MCP for vLLM: "너무 큽니다! 1-10페이지, 11-20페이지, ... 시도하세요"
↓
LLM이 여러 번 스마트하게 요청
↓
컨텍스트 오버플로우 없이 모든 콘텐츠 처리
+ 해상도 조절도 합니다(100dpi 기본)
```

```
사용자: "scanned_contract.pdf의 배경색을 빨간색으로 바꾸면 어떨까?"

vLLM: extraction_mode="image_only"로 호출

PDF MCP for vLLM:
  - 쓸모없는 텍스트 추출 시도 스킵
  - 각 페이지를 이미지로 렌더링
  - 비전으로 직접 보냄

결과: 빠르고, 정확하고, 낭비 없음
```

---


### 스마트 손상 처리

```
텍스트로 못 읽는 PDF를 자동으로 감지
↓
자동으로 이미지로 전송
vLLM이 비전으로 완벽하게 읽음
```

**PDF MCP for vLLM 이전:**
```json
{
  "text": "�㍻��㍺�������..."  // 5000 토큰의 쓰레기
}
```

**PDF MCP for vLLM 사용 (Auto 모드):**
```json
{
  "content_blocks": [],           // 쓰레기 차단
  "page_image": "base64...",      // 비전용 깨끗한 이미지
  "text_corrupted": true          // LLM이 이유를 알 수 있음
}
```

### 지능형 이미지 처리

```
PDF에서 모든 이미지 추출
↓
필터: 장식용 쓰레기 제거 (< 28px)
필터: 극단적 비율 제거 (> 15:1 비율 선)
필터: 헤더/푸터 제거
↓
자르기: A4 높이로 축소 (기본 842px)
DPI 제한(기본 100dpi)
↓
결과: 의미있는 이미지만, LLM 최적화 크기
```

**이전:** 로고, 선, 테두리 포함 50개 이미지
**이후:** 의미있는 콘텐츠 이미지 5개

---

## 실제 작동 확인

```bash
python test_server.py
```

**시각적 테스트 인터페이스 표시:**
- 실시간 손상된 텍스트 감지
- 블록 순서 확인
- 인라인 이미지 렌더링
- 마크다운 테이블 렌더링
- 모드 전환 효과

**LLM에 붙이기 전** 자신의 PDF로 테스트하세요.

---

## 빠른 시작

### 설치

**방법 1: PyPI (가장 쉬움)**
```bash
pip install pdf4vllm-mcp
# 테스트 서버 포함: pip install pdf4vllm-mcp[test]
```

**방법 2: Git 클론**
```bash
git clone https://github.com/PyJudge/pdf4vllm-mcp.git
cd pdf4vllm-mcp
pip install -e .
```

### 로컬 테스트

```bash
python test_server.py
# → http://localhost:8000
```

**작동 확인:**
- 손상된 PDF 업로드 → 자동 감지 및 이미지 전환 확인
- 깨끗한 PDF 업로드 → 구조화된 텍스트 블록 확인
- 3가지 모드 시도 → 시각적 렌더링으로 차이 확인

### MCP 연동

#### 쉬운 설치 (권장)

```bash
git clone https://github.com/PyJudge/pdf4vllm-mcp.git
cd pdf4vllm-mcp
pip install -e .

# 크로스 플랫폼 (Windows/macOS/Linux)
python scripts/install_mcp.py

# macOS/Linux 전용
./scripts/install_mcp.sh
```

스크립트가 자동으로:
- OS 감지 (Windows/macOS/Linux)
- Python과 Poppler 경로 찾기
- 올바른 설정으로 Claude Desktop 설정 파일 생성
- 기존 설정 백업

그 다음 Claude Desktop을 재시작하세요.

#### Claude Code (CLI)

프로젝트 디렉토리에서 `.mcp.json` 생성:

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

---

#### 수동 설치 (Claude Desktop)

**설정 파일:** `~/Library/Application Support/Claude/claude_desktop_config.json`

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

#### 전체 예시 (Conda)

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

#### 전체 예시 (Homebrew)

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

> **중요:**
> - `command`와 `args` 모두 **절대 경로** 사용

#### Claude Desktop 재시작

Claude Desktop을 완전히 종료 후 다시 실행하세요.

#### 문제 해결

**"server disconnected"**
- Python 경로 또는 server.py 경로 오류. 둘 다 존재하는지 확인

**로그 확인:** `~/Library/Logs/Claude/mcp-server-pdf4vllm.log`

---

## 실제 사례

### 사례 1: 손상된 법률 문서

```
사용자: "court_document.pdf 읽어줘"

PDF MCP for vLLM Auto 모드:
  1. 감지: 87% 텍스트 손상
  2. 차단: 쓰레기 텍스트가 LLM에 도달하지 못하게
  3. 제공: 깨끗한 페이지 이미지
  4. 결과: LLM이 비전으로 읽고 완벽하게 이해

절약된 토큰: ~15,000 (차단된 손상 텍스트)
정확도: 100% (비전) vs 0% (쓰레기 텍스트)
```

### 사례 2: 200페이지 보고서

```
사용자: "annual_report.pdf 읽어줘"

PDF MCP for vLLM:
  "PAGE_LIMIT_EXCEEDED: 요청한 200페이지가 제한(10)을 초과합니다.

   제안 범위:
   - 1-10페이지 (10페이지, ~5개 이미지)
   - 11-20페이지 (10페이지, ~8개 이미지)
   - 21-30페이지 (10페이지, ~12개 이미지)
   - 31-40페이지 (10페이지, ~6개 이미지)
   - 41-50페이지 (10페이지, ~15개 이미지)"

사용자: "1-10페이지 읽어줘"
PDF MCP for vLLM: 첫 번째 섹션 추출

사용자: "11-20페이지 읽어줘"
PDF MCP for vLLM: 다음 섹션 추출

결과: 컨텍스트 폭발 없음, 체계적 읽기
```

---

## 설정

`config.json` 생성:

```json
{
  "max_pages_per_request": 20,        // 당신의 컨텍스트 크기
  "max_images_per_request": 100,      // 당신의 필요
  "max_image_dimension": 1024,        // 더 높은 품질
  "min_image_dimension": 50,          // 더 공격적인 필터링
  "max_aspect_ratio": 10,             // 더 엄격한 선 필터링
  "page_image_dpi": 150               // 비전용 더 높은 DPI
}
```

**또는 환경 변수 사용:**
```bash
export PDF_MAX_PAGES=20
export PDF_PAGE_IMAGE_DPI=150
```

---
## 3가지 추출 모드

PDF에 따라 선택:

### Auto (기본값) - PDF MCP for vLLM이 결정

```python
extraction_mode: "auto"  # 스마트 감지
```

**동작:**
1. 먼저 텍스트 추출 시도
2. **자동으로 손상 감지**
3. 손상됨 → **쓰레기 텍스트 차단** + **페이지 이미지 추가**
4. 깨끗함 → 텍스트 정상 반환

**사용 시기:** PDF 품질을 모를 때 (대부분의 경우)

---

### Text Only - 빠르고 가벼움

```python
extraction_mode: "text_only"
```

**동작:**
- 텍스트 + 표만 추출
- 페이지 이미지 절대 추가 안 함
- 최소 토큰

**사용 시기:** PDF가 깨끗한 것을 확실히 알 때

---

### Image Only - 비전 우선

```python
extraction_mode: "image_only"
```

**동작:**
- 텍스트 추출 완전 스킵
- 페이지를 이미지로만 렌더링
- LLM 비전으로 직접

**사용 시기:** 스캔 PDF, 확실히 손상된 텍스트

---



---

## API

### `read_pdf`

**중요한 파라미터 하나:**

```json
{
  "file_path": "document.pdf",
  "extraction_mode": "auto"  // 이게 전부. 나머지는 스마트 기본값.
}
```

**고급 옵션 (필요할 때):**

```json
{
  "file_path": "document.pdf",
  "start_page": 1,               // 기본값: 1
  "end_page": 10,                // 기본값: 마지막 페이지
  "extraction_mode": "auto",     // 기본값: "auto"
  "filter_header_footer": true,  // 기본값: true
  "crop_images": true,           // 기본값: true
  "max_image_dimension": 842,    // 기본값: 842 (A4 높이)
  "page_image_dpi": 100          // 기본값: 100
}
```

---

## 라이선스

**MIT**

**종속성:**
- pypdfium2: Apache 2.0 / BSD
- pikepdf: MPL 2.0
- pdfplumber: MIT
- Pillow: HPND
- pydantic: MIT

---

<div align="center">

**PDF MCP for vLLM v1.0**

PDF와 싸우지 마세요. PDF MCP for vLLM이 처리하게 하세요.

[GitHub](https://github.com/PyJudge/pdf4vllm-mcp) · [이슈](https://github.com/PyJudge/pdf4vllm-mcp/issues) · [토론](https://github.com/PyJudge/pdf4vllm-mcp/discussions)

</div>