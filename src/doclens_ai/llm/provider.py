"""Bounded local OpenAI-compatible HTTP adapter. Never execute model tools."""

from __future__ import annotations

import asyncio
import json
from typing import Protocol

import httpx

from doclens_ai.core.rag_config import RagSettings


class GeneratorUnavailable(RuntimeError):
    def __init__(self):
        super().__init__("answer service is unavailable")


class Generator(Protocol):
    async def generate(self, messages: list[dict[str, str]]) -> str: ...

    async def aclose(self) -> None: ...


def strict_json(value: str | bytes):
    """Reject duplicate keys, nonfinite numbers, trailing data and JSON repair."""

    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError("duplicate JSON field")
            result[key] = item
        return result

    def invalid_constant(_):
        raise ValueError("invalid JSON number")

    return json.loads(value, object_pairs_hook=pairs, parse_constant=invalid_constant)


class LocalGenerator:
    def __init__(self, settings: RagSettings, *, transport=None):
        if settings.endpoint is None or settings.model_id is None:
            raise GeneratorUnavailable()
        self.settings = settings
        self._semaphore = asyncio.Semaphore(settings.concurrency)
        self._client = httpx.AsyncClient(
            timeout=settings.timeout_seconds,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
            limits=httpx.Limits(
                max_connections=settings.concurrency,
                max_keepalive_connections=settings.concurrency,
            ),
        )

    def metadata(self):
        return {
            "protocol": "local-chat-completions-v1",
            "model_id": self.settings.model_id,
            "declared_revision": self.settings.model_revision,
            "declared_artifact_sha256": self.settings.artifact_sha256,
            "artifact_verification": "operator_declaration_only_not_verified_by_adapter",
            "temperature": self.settings.temperature,
            "max_output_tokens": self.settings.max_output_tokens,
            "timeout_seconds": self.settings.timeout_seconds,
            "concurrency": self.settings.concurrency,
            "max_response_bytes": self.settings.max_response_bytes,
        }

    async def generate(self, messages):
        try:
            async with asyncio.timeout(self.settings.queue_timeout_seconds):
                await self._semaphore.acquire()
        except TimeoutError:
            raise GeneratorUnavailable() from None
        try:
            headers = {"Accept": "application/json", "Accept-Encoding": "identity"}
            if self.settings.api_key is not None:
                headers["Authorization"] = "Bearer " + self.settings.api_key.get_secret_value()
            async with asyncio.timeout(self.settings.timeout_seconds):
                async with self._client.stream(
                    "POST",
                    self.settings.endpoint,
                    headers=headers,
                    json={
                        "model": self.settings.model_id,
                        "messages": messages,
                        "temperature": self.settings.temperature,
                        "max_tokens": self.settings.max_output_tokens,
                        "n": 1,
                        "stream": False,
                        "response_format": {"type": "json_object"},
                    },
                ) as response:
                    if (
                        response.status_code != 200
                        or response.headers.get("content-encoding", "identity") != "identity"
                        or response.headers.get("content-type", "").split(";")[0].strip()
                        != "application/json"
                    ):
                        raise GeneratorUnavailable()
                    body = bytearray()
                    async for part in response.aiter_raw():
                        if len(body) + len(part) > self.settings.max_response_bytes:
                            raise GeneratorUnavailable()
                        body.extend(part)
            payload = strict_json(bytes(body).decode("utf-8"))
            if not isinstance(payload, dict) or payload.get("model") != self.settings.model_id:
                raise GeneratorUnavailable()
            choices = payload.get("choices")
            if not isinstance(choices, list) or len(choices) != 1:
                raise GeneratorUnavailable()
            choice = choices[0]
            if not isinstance(choice, dict) or choice.get("finish_reason") != "stop":
                raise GeneratorUnavailable()
            message = choice.get("message")
            if (
                not isinstance(message, dict)
                or message.get("role") != "assistant"
                or set(message) - {"role", "content", "refusal"}
                or message.get("refusal") is not None
                or type(message.get("content")) is not str
                or not message["content"]
            ):
                raise GeneratorUnavailable()
            return message["content"]
        except Exception:
            # Never log provider body, exception text, request or model paths.
            raise GeneratorUnavailable() from None
        finally:
            # HTTP cancellation closes the stream; remote computation may still continue.
            self._semaphore.release()

    async def aclose(self):
        await self._client.aclose()
