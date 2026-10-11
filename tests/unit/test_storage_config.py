from __future__ import annotations

import pytest
from pydantic import ValidationError

from doclens_ai.storage.config import StorageSettings


def _settings(**overrides: object) -> StorageSettings:
    values = {
        "endpoint_url": "http://localhost:9000/",
        "access_key": "local-access",
        "secret_key": "local-secret",
        "bucket_name": "private-documents",
        "secure": False,
    }
    values.update(overrides)
    return StorageSettings(**values)


def test_storage_settings_are_typed_and_normalized() -> None:
    settings = _settings(max_upload_size_bytes="1024")

    assert settings.endpoint_url == "http://localhost:9000"
    assert settings.max_upload_size_bytes == 1024
    assert settings.secret_key.get_secret_value() == "local-secret"
    assert "local-secret" not in repr(settings)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("endpoint_url", "localhost:9000"),
        ("bucket_name", " "),
        ("max_upload_size_bytes", 0),
    ],
)
def test_storage_settings_reject_invalid_values(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        _settings(**{field: value})


def test_storage_settings_require_transport_to_match_endpoint() -> None:
    with pytest.raises(ValidationError, match="HTTPS"):
        _settings(secure=True)
