"""
PDF MCP for vLLM Test Server
Interactive web UI for testing PDF extraction with visual rendering
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import json
import base64
from src.pdf_tools import list_pdfs_handler, read_pdf_handler

app = FastAPI(title="PDF MCP for vLLM Test Server")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Main testing interface with inline image and markdown rendering"""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>PDF MCP for vLLM Test Server</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            max-width: 1400px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
        }
        .section {
            margin-bottom: 30px;
        }
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        input[type="text"], input[type="number"] {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        input[type="text"] {
            flex: 1;
            min-width: 200px;
        }
        input[type="number"] {
            width: 80px;
        }
        button {
            padding: 8px 16px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        button:hover {
            background: #0056b3;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .pdf-list {
            display: grid;
            gap: 10px;
            margin-top: 15px;
        }
        .pdf-item {
            display: grid;
            grid-template-columns: 1fr auto auto;
            gap: 10px;
            align-items: center;
            padding: 12px;
            background: #f8f9fa;
            border-radius: 4px;
            border: 1px solid #e9ecef;
        }
        .pdf-info {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .pdf-name {
            font-weight: 600;
            color: #333;
        }
        .pdf-meta {
            font-size: 12px;
            color: #666;
        }
        .action-buttons {
            display: flex;
            gap: 8px;
        }
        .btn-list {
            padding: 6px 12px;
            background: #28a745;
            font-size: 13px;
        }
        .btn-list:hover {
            background: #218838;
        }
        .btn-run {
            padding: 6px 12px;
            background: #dc3545;
            font-size: 13px;
        }
        .btn-run:hover {
            background: #c82333;
        }
        .output {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            border: 1px solid #ddd;
            margin-top: 15px;
            max-height: none;
        }
        .loading {
            color: #007bff;
            font-style: italic;
        }
        .error {
            color: #dc3545;
            background: #f8d7da;
            padding: 12px;
            border-radius: 4px;
            border: 1px solid #f5c6cb;
        }
        .checkbox-group {
            display: flex;
            gap: 15px;
            align-items: center;
        }
        label {
            display: flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
            font-size: 14px;
        }
        input[type="checkbox"] {
            cursor: pointer;
        }
        select {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            cursor: pointer;
            background: white;
        }
        .option-group {
            display: flex;
            gap: 20px;
            margin-top: 15px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 6px;
        }
        .option-item {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .option-label {
            font-weight: 600;
            color: #333;
            font-size: 13px;
        }
        .option-description {
            font-size: 11px;
            color: #666;
            line-height: 1.4;
        }
        .mode-info {
            background: #e7f3ff;
            padding: 15px;
            border-radius: 6px;
            margin-top: 15px;
            border-left: 4px solid #007bff;
        }
        .mode-info-title {
            font-weight: 600;
            color: #0056b3;
            margin-bottom: 8px;
        }
        .mode-info-content {
            font-size: 13px;
            color: #333;
            line-height: 1.6;
        }
        .mode-info-content code {
            background: #fff;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Monaco', monospace;
            color: #d63384;
        }

        /* Content rendering styles */
        .page-container {
            margin-bottom: 30px;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }
        .page-header {
            background: #007bff;
            color: white;
            padding: 12px 20px;
            font-weight: 600;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .page-content {
            padding: 20px;
        }
        .content-block {
            margin-bottom: 20px;
            padding: 15px;
            border-radius: 6px;
        }
        .block-text {
            background: #ffffff;
            border-left: 4px solid #007bff;
            white-space: pre-wrap;
            line-height: 1.6;
        }
        .block-table {
            background: #f8f9fa;
            border-left: 4px solid #28a745;
            overflow-x: auto;
        }
        .block-table table {
            width: 100%;
            border-collapse: collapse;
            margin: 0;
        }
        .block-table th {
            background: #e9ecef;
            padding: 10px;
            text-align: left;
            border: 1px solid #dee2e6;
            font-weight: 600;
        }
        .block-table td {
            padding: 10px;
            border: 1px solid #dee2e6;
        }
        .block-table tr:hover {
            background: #f1f3f5;
        }
        .block-image {
            background: #ffffff;
            border-left: 4px solid #ffc107;
            text-align: center;
        }
        .block-image img {
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .block-type-label {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        .label-text {
            background: #007bff;
            color: white;
        }
        .label-table {
            background: #28a745;
            color: white;
        }
        .label-image {
            background: #ffc107;
            color: #333;
        }
        .corruption-warning {
            background: #fff3cd;
            border: 1px solid #ffc107;
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 15px;
            color: #856404;
        }
        .page-image-container {
            margin-top: 15px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 6px;
            text-align: center;
        }
        .page-image-container img {
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .stats {
            background: #e7f3ff;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
        }
        .stats-item {
            display: inline-block;
            margin-right: 20px;
            color: #0056b3;
            font-weight: 600;
        }
        .text-hint-info {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 15px;
            color: #155724;
        }
        .option-disabled {
            opacity: 0.5;
            pointer-events: none;
        }
        .option-disabled select {
            background: #e9ecef;
            cursor: not-allowed;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>PDF MCP for vLLM Test Server</h1>
        <div class="subtitle">Interactive PDF extraction testing with visual rendering</div>

        <!-- List PDFs Section -->
        <div class="section">
            <h2>List PDFs</h2>
            <div class="controls">
                <input type="text" id="workdir" placeholder="Working directory (default: current)" value=".">
                <button onclick="listPDFs()">List PDFs</button>
            </div>
            <div id="pdf-list-output"></div>
        </div>

        <!-- Read PDF Section -->
        <div class="section">
            <h2>Read PDF</h2>
            <div class="controls">
                <input type="text" id="filepath" placeholder="PDF file path">
                <input type="number" id="startpage" placeholder="Start" value="1" min="1">
                <input type="number" id="endpage" placeholder="End">
                <button onclick="readPDF()">Read PDF</button>
            </div>
            <div class="option-group">
                <div class="option-item">
                    <label class="option-label" for="extractionmode">
                        Extraction Mode
                    </label>
                    <select id="extractionmode" onchange="updateModeInfo()">
                        <option value="auto" selected>Auto - Smart Detection (recommended)</option>
                        <option value="text_only">Text Only - No Page Images</option>
                        <option value="image_only">Image Only - Skip Text</option>
                    </select>
                    <span class="option-description">
                        Controls what content to extract and when to use vision
                    </span>
                </div>

                <div class="option-item">
                    <label class="option-label" for="filterheader">
                        Header/Footer Filter
                    </label>
                    <select id="filterheader">
                        <option value="enabled" selected>Enabled (remove decorative)</option>
                        <option value="disabled">Disabled (keep all)</option>
                    </select>
                    <span class="option-description">Filter small header/footer images</span>
                </div>

                <div class="option-item">
                    <label class="option-label" for="cropimages">
                        Image Cropping
                    </label>
                    <select id="cropimages">
                        <option value="enabled" selected>Enabled (max 842px)</option>
                        <option value="disabled">Disabled (original)</option>
                    </select>
                    <span class="option-description">Crop to A4 height for LLM context</span>
                </div>
            </div>

            <div class="mode-info" id="mode-info">
                <div class="mode-info-title">Auto Mode (Default)</div>
                <div class="mode-info-content">
                    Extracts text, tables, and images normally. If text corruption is detected,
                    automatically blocks corrupted text and provides page image for vision analysis.
                    Best for general use.
                </div>
            </div>
            <div id="read-output"></div>
        </div>
    </div>

    <script>
        async function listPDFs() {
            const output = document.getElementById('pdf-list-output');
            output.innerHTML = '<div class="loading">Loading PDFs...</div>';

            try {
                const response = await fetch('/api/list_pdfs', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        working_directory: document.getElementById('workdir').value || '.'
                    })
                });

                const result = await response.json();

                if (result.error) {
                    output.innerHTML = `<div class="error">${result.error}: ${result.message}</div>`;
                } else if (result.pdfs && result.pdfs.length > 0) {
                    const pdfItems = result.pdfs.map(pdf => `
                        <div class="pdf-item">
                            <div class="pdf-info">
                                <div class="pdf-name">${escapeHtml(pdf.name)}</div>
                                <div class="pdf-meta">
                                    ${pdf.pages} pages •
                                    ${(pdf.size_bytes / 1024).toFixed(1)} KB •
                                    ${escapeHtml(pdf.path)}
                                </div>
                            </div>
                            <div class="action-buttons">
                                <button class="btn-list" onclick="selectFile('${escapeHtml(pdf.path)}')">
                                    Select
                                </button>
                                <button class="btn-run" onclick="quickRead('${escapeHtml(pdf.path)}')">
                                    Read
                                </button>
                            </div>
                        </div>
                    `).join('');

                    output.innerHTML = `
                        <div style="margin-bottom: 10px; color: #666; font-size: 14px;">
                            Found ${result.total_count} PDF(s) in ${escapeHtml(result.working_directory)}
                        </div>
                        <div class="pdf-list">${pdfItems}</div>
                    `;
                } else {
                    output.innerHTML = '<div style="color: #666;">No PDFs found</div>';
                }
            } catch (error) {
                output.innerHTML = `<div class="error">Error: ${escapeHtml(error.message)}</div>`;
            }
        }

        function renderContentBlock(block) {
            if (block.type === 'text') {
                return `
                    <div class="content-block block-text">
                        <span class="block-type-label label-text">Text</span>
                        <div>${escapeHtml(block.content)}</div>
                    </div>
                `;
            } else if (block.type === 'table') {
                // Render markdown table using marked.js
                const tableHtml = marked.parse(block.content);
                return `
                    <div class="content-block block-table">
                        <span class="block-type-label label-table">Table</span>
                        ${tableHtml}
                    </div>
                `;
            } else if (block.type === 'image') {
                return `
                    <div class="content-block block-image">
                        <span class="block-type-label label-image">Image</span>
                        <img src="data:image/png;base64,${block.content}" alt="Extracted image">
                    </div>
                `;
            }
            return '';
        }

        function renderPage(page) {
            const blocksHtml = page.content_blocks.map(block => renderContentBlock(block)).join('');

            let corruptionWarning = '';
            if (page.text_corrupted) {
                corruptionWarning = `
                    <div class="corruption-warning">
                        <strong>Text Corruption Detected</strong>
                        (${(page.corruption_ratio * 100).toFixed(1)}% corruption ratio)
                        - Page image provided for vision analysis
                    </div>
                `;
            }

            let textHintHtml = '';
            if (page.text_hint) {
                textHintHtml = `
                    <div class="text-hint-info">
                        <strong>Text Available:</strong> ${page.text_hint}
                    </div>
                `;
            }

            let pageImageHtml = '';
            if (page.page_image) {
                pageImageHtml = `
                    <div class="page-image-container">
                        <div style="font-weight: 600; margin-bottom: 10px; color: #666;">
                            Full Page Image (${page.page_image_width}x${page.page_image_height}px)
                        </div>
                        <img src="data:image/png;base64,${page.page_image}" alt="Page ${page.page_number}">
                    </div>
                `;
            }

            // Empty page message if no content
            let emptyPageHtml = '';
            if (!blocksHtml && !pageImageHtml && !corruptionWarning) {
                emptyPageHtml = `
                    <div style="color: #888; font-style: italic; padding: 20px; text-align: center;">
                        This page has no extractable content (no text, tables, or images)
                    </div>
                `;
            }

            return `
                <div class="page-container">
                    <div class="page-header">
                        <span>Page ${page.page_number}</span>
                        <span>${page.content_blocks.length} block(s)</span>
                    </div>
                    <div class="page-content">
                        ${corruptionWarning}
                        ${textHintHtml}
                        ${blocksHtml}
                        ${pageImageHtml}
                        ${emptyPageHtml}
                    </div>
                </div>
            `;
        }

        async function readPDF() {
            const filepath = document.getElementById('filepath').value;
            if (!filepath) {
                alert('Please enter a PDF file path');
                return;
            }

            const output = document.getElementById('read-output');
            output.innerHTML = '<div class="loading">Reading PDF...</div>';

            try {
                const body = {
                    file_path: filepath,
                    start_page: parseInt(document.getElementById('startpage').value) || 1,
                    filter_header_footer: document.getElementById('filterheader').value === 'enabled',
                    crop_images: document.getElementById('cropimages').value === 'enabled',
                    extraction_mode: document.getElementById('extractionmode').value
                };

                const endPage = document.getElementById('endpage').value;
                if (endPage) {
                    body.end_page = parseInt(endPage);
                }

                const response = await fetch('/api/read_pdf', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(body)
                });

                const result = await response.json();

                if (result.error) {
                    output.innerHTML = `<div class="error">${escapeHtml(result.error)}: ${escapeHtml(result.message)}</div>`;
                } else if (result.pages) {
                    // Render pages with visual content
                    const statsHtml = `
                        <div class="stats">
                            <span class="stats-item">${result.total_pages_read} page(s)</span>
                            <span class="stats-item">${result.total_images} image(s)</span>
                            <span class="stats-item">${escapeHtml(result.file_path)}</span>
                        </div>
                    `;

                    const pagesHtml = result.pages.map(page => renderPage(page)).join('');
                    output.innerHTML = `<div class="output">${statsHtml}${pagesHtml}</div>`;
                } else {
                    output.innerHTML = `<div class="output"><pre>${JSON.stringify(result, null, 2)}</pre></div>`;
                }
            } catch (error) {
                output.innerHTML = `<div class="error">Error: ${escapeHtml(error.message)}</div>`;
            }
        }

        function selectFile(filepath) {
            document.getElementById('filepath').value = filepath;
        }

        function quickRead(filepath) {
            document.getElementById('filepath').value = filepath;
            readPDF();
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function updateModeInfo() {
            const mode = document.getElementById('extractionmode').value;
            const modeInfo = document.getElementById('mode-info');

            const modeDescriptions = {
                'auto': {
                    title: 'Auto Mode (Default)',
                    content: 'Extracts text, tables, and images normally. If text corruption is detected, automatically <strong>blocks corrupted text</strong> and provides page image for vision analysis. Best for general use.'
                },
                'text_only': {
                    title: 'Text Only Mode',
                    content: 'Extracts text, tables, and document images only. <strong>Never includes page images</strong>, even if text is corrupted. Fastest mode with minimal tokens. Best for known good PDFs.'
                },
                'image_only': {
                    title: 'Image Only Mode',
                    content: 'Skips all text extraction entirely. Provides <strong>only full page images</strong> for vision analysis. Best for scanned documents or known corrupted text.'
                }
            };

            const info = modeDescriptions[mode];
            modeInfo.innerHTML = `
                <div class="mode-info-title">${info.title}</div>
                <div class="mode-info-content">${info.content}</div>
            `;

            // Disable Cropping option in image_only mode (not applicable to page images)
            const cropImages = document.getElementById('cropimages');
            const isImageOnly = (mode === 'image_only');

            cropImages.disabled = isImageOnly;

            if (isImageOnly) {
                cropImages.parentElement.classList.add('option-disabled');
            } else {
                cropImages.parentElement.classList.remove('option-disabled');
            }
        }

        // Auto-load PDFs on page load
        window.onload = () => {
            listPDFs();
            updateModeInfo();
        };
    </script>
</body>
</html>
    """


@app.post("/api/list_pdfs")
async def api_list_pdfs(request: Request):
    """List PDFs API endpoint"""
    try:
        data = await request.json()
        result_json, _ = await list_pdfs_handler(data)
        return JSONResponse(content=json.loads(result_json))
    except Exception as e:
        return JSONResponse(
            content={"error": "INTERNAL_ERROR", "message": str(e)},
            status_code=500
        )


@app.post("/api/read_pdf")
async def api_read_pdf(request: Request):
    """Read PDF API endpoint"""
    try:
        data = await request.json()
        result_json, images = await read_pdf_handler(data)
        result = json.loads(result_json)

        # Replace placeholders with actual image data for web rendering
        # Note: images now contain raw bytes, need to convert to base64 for web
        if images and 'pages' in result:
            for page in result['pages']:
                # Replace in content_blocks
                for block in page.get('content_blocks', []):
                    if block.get('type') == 'image' and block.get('content', '').startswith('[IMAGE_'):
                        try:
                            idx = int(block['content'][7:-1])  # Extract index from [IMAGE_X]
                            if idx < len(images):
                                # Convert raw bytes to base64 for web display
                                img_data = images[idx]['data']
                                block['content'] = base64.b64encode(img_data).decode('utf-8')
                        except (ValueError, IndexError):
                            pass

                # Replace page_image placeholder
                if page.get('page_image', '').startswith('[IMAGE_'):
                    try:
                        idx = int(page['page_image'][7:-1])
                        if idx < len(images):
                            # Convert raw bytes to base64 for web display
                            img_data = images[idx]['data']
                            page['page_image'] = base64.b64encode(img_data).decode('utf-8')
                    except (ValueError, IndexError):
                        pass

        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            content={"error": "INTERNAL_ERROR", "message": str(e)},
            status_code=500
        )


def run():
    """Entry point for console script"""
    import uvicorn
    print("\n" + "="*60)
    print("PDF MCP for vLLM Test Server")
    print("="*60)
    print("Server starting at: http://localhost:8000")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    run()