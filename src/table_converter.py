"""
Table conversion utility
Convert pdfplumber tables to Markdown format
Includes merged cell handling
"""
from typing import List


def fill_merged_cells(table: List[List]) -> List[List]:
    """
    Handle merged cells: fill empty cells (None) with value from above

    Args:
        table: pdfplumber extract_tables() result (list of lists)

    Returns:
        Table with merged cells filled
    """
    if not table or len(table) == 0:
        return table

    # Process each column
    filled_table = [row[:] for row in table]  # Copy

    for col_idx in range(len(filled_table[0])):
        last_value = None

        for row in filled_table:
            if col_idx >= len(row):
                continue

            cell = row[col_idx]

            # Copy value from above if cell is empty
            if cell is None or (isinstance(cell, str) and cell.strip() == ''):
                row[col_idx] = last_value or ''
            else:
                # Store value if present
                last_value = cell

    return filled_table


def convert_table_to_markdown(table: List[List]) -> str:
    """
    Convert pdfplumber table to Markdown table

    Args:
        table: pdfplumber extract_tables() result (list of lists)

    Returns:
        Markdown format string
    """
    if not table or len(table) == 0:
        return ""

    # Handle merged cells
    filled_table = fill_merged_cells(table)

    # Convert None to empty string
    cleaned_table = []
    for row in filled_table:
        cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
        cleaned_table.append(cleaned_row)

    # Column count
    max_cols = max(len(row) for row in cleaned_table)

    # Normalize all rows to same column count
    normalized_table = []
    for row in cleaned_table:
        while len(row) < max_cols:
            row.append("")
        normalized_table.append(row[:max_cols])

    if len(normalized_table) == 0:
        return ""

    # Generate Markdown
    lines = []

    # First row as header
    header = normalized_table[0]
    lines.append("| " + " | ".join(header) + " |")

    # Separator line
    lines.append("| " + " | ".join(["---"] * max_cols) + " |")

    # Data rows
    for row in normalized_table[1:]:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def convert_tables_to_markdown(tables: List[List[List[str]]]) -> List[str]:
    """
    Convert multiple tables to Markdown

    Args:
        tables: pdfplumber extract_tables() result (list of tables)

    Returns:
        List of Markdown strings
    """
    markdown_tables = []

    for i, table in enumerate(tables):
        md = convert_table_to_markdown(table)
        if md:
            # Add table number
            markdown_tables.append(f"**Table {i+1}**\n\n{md}")

    return markdown_tables
