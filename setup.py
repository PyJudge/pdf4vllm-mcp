"""
Setup script for PDF MCP for vLLM MCP Server
For PyPI distribution
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="pdf4vllm-mcp",
    version="1.0.1",
    description="Block-based PDF extraction MCP server optimized for LLM consumption",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="PDF MCP for vLLM Contributors",
    url="https://github.com/PyJudge/pdf4vllm-mcp",
    project_urls={
        "Documentation": "https://github.com/PyJudge/pdf4vllm-mcp#readme",
        "Source": "https://github.com/PyJudge/pdf4vllm-mcp",
        "Issues": "https://github.com/PyJudge/pdf4vllm-mcp/issues",
    },
    packages=find_packages(exclude=["tests", "sample_pdfs"]),
    python_requires=">=3.10",
    install_requires=[
        "mcp>=0.9.0",
        "pypdfium2>=4.0.0",
        "pikepdf>=8.0.0",
        "pdfplumber>=0.10.0",
        "Pillow>=10.0.0",
        "pydantic>=2.0.0",
        "pdfminer.six>=20221105",
    ],
    extras_require={
        "test": [
            "fastapi>=0.100.0",
            "uvicorn>=0.23.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "pdf4vllm-test=test_server:run",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: Filters",
    ],
    keywords="mcp pdf llm extraction claude vision ocr vllm",
    license="MIT",
)
