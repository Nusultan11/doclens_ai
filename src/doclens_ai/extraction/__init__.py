"""Standalone structured document extraction baseline."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

from doclens_ai.extraction.models import (
    DocumentFormat,
    ErrorCategory,
    ExtractionResult,
    ExtractionStatus,
    ExtractionWarning,
    SourceLocation,
    SpreadsheetCell,
    SpreadsheetSheet,
    SpreadsheetTable,
    TableBlock,
    TableCell,
    TableRow,
    TextBlock,
    WarningCode,
    WarningSeverity,
)

if TYPE_CHECKING:
    from doclens_ai.extraction.parsers import (
        ExtractionConfigurationError,
        ExtractionLimits,
        extract_corpus,
        extract_file,
    )


def __getattr__(name: str) -> Any:
    # Metadata contracts must remain importable without optional parser dependencies.
    if name in {
        "ExtractionConfigurationError",
        "ExtractionLimits",
        "extract_corpus",
        "extract_file",
    }:
        return getattr(import_module("doclens_ai.extraction.parsers"), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "DocumentFormat",
    "ErrorCategory",
    "ExtractionConfigurationError",
    "ExtractionLimits",
    "ExtractionResult",
    "ExtractionStatus",
    "ExtractionWarning",
    "SourceLocation",
    "SpreadsheetCell",
    "SpreadsheetSheet",
    "SpreadsheetTable",
    "TableBlock",
    "TableCell",
    "TableRow",
    "TextBlock",
    "WarningCode",
    "WarningSeverity",
    "extract_corpus",
    "extract_file",
]
