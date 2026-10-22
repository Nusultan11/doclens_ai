"""Parser budgets shared with API-side route pinning without parser imports."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExtractionLimits:
    """Hard resource ceilings applied before and during parsing."""

    max_files: int = 10_000
    max_file_bytes: int = 50 * 1024 * 1024
    max_office_entries: int = 20_000
    max_office_entry_bytes: int = 100 * 1024 * 1024
    max_office_uncompressed_bytes: int = 500 * 1024 * 1024
    max_office_compression_ratio: float = 200.0
    max_pdf_pages: int = 2_000
    min_pdf_non_whitespace_chars_per_page: int = 20
    max_extracted_characters: int = 5_000_000
    max_document_blocks: int = 100_000
    max_table_cells: int = 1_000_000
    max_xlsx_sheets: int = 256
    max_xlsx_stored_cells: int = 1_000_000
    max_xlsx_merged_ranges: int = 100_000
    max_xlsx_tables: int = 10_000
