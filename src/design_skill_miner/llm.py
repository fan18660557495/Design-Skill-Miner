from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from json import JSONDecodeError
import json
import os
import ssl
from typing import Any
from urllib import error, request

from .models import Insight


DEFAULT_BASE_URL = "https://api.openai.com/v1"

SYSTEM_PROMPT = """你是设计规则审校助手。
你会收到一个 design-skill-miner 生成的 insight JSON。
只允许在不引入新事实的前提下做 3 件事：
1. 改写 summary，使其更清晰。
2. 改写 why_it_repeats，使其更聚焦。
3. 改写 normalized_rules，使其更具体可执行。

要求：
- 不要发明新证据。
- normalized_rules 保持 2 到 5 条。
- 每条规则必须是可执行约束，不要写口号。
- 只输出 JSON 对象。
"""

BATCH_SYSTEM_PROMPT = """你是设计规则审校助手。
你会收到一个 insights JSON 数组。请逐项在不引入新事实的前提下优化每个 insight：
1. 改写 summary，使其更清晰。
2. 改写 why_it_repeats，使其更聚焦。
3. 改写 normalized_rules，使其更具体可执行。

要求：
- 不要发明新证据。
- 保留每个 insight 的 title，作为匹配键。
- normalized_rules 保持 2 到 5 条。
- 每条规则必须是可执行约束，不要写口号。
- 只输出 JSON 对象，格式为 {"insights":[...]}。
"""


@dataclass
class LLMConfig:
    enabled: bool = False
    provider: str = "openai-compatible"
    base_url: str = DEFAULT_BASE_URL
    model: str | None = None
    api_key_env: str = "OPENAI_API_KEY"
    api_key_value: str | None = None
    json_mode: bool = True
    allow_insecure_tls: bool = False
    timeout_seconds: int = 120

    @property
    def api_key(self) -> str | None:
        if self.api_key_value:
            return self.api_key_value.strip()
        value = os.getenv(self.api_key_env)
        return value.strip() if value else None

    def is_ready(self) -> bool:
        return self.enabled and bool(self.model) and bool(self.api_key)


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config

    def enhance_insight(self, insight: Insight) -> Insight:
        if not self.config.is_ready():
            return insight

        payload = self._chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(insight.to_dict(), ensure_ascii=False, indent=2),
                },
            ]
        )
        return merge_llm_payload(insight, payload)

    def enhance_insights(self, insights: list[Insight]) -> tuple[list[Insight], int]:
        if not self.config.is_ready() or not insights:
            return insights, 0

        payload = self._chat_completion(
            messages=[
                {"role": "system", "content": BATCH_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {"insights": [insight.to_dict() for insight in insights]},
                        ensure_ascii=False,
                        indent=2,
                    ),
                },
            ]
        )
        merged, failures = merge_batch_payload(insights, payload)
        return merged, failures

    def _chat_completion(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        payload = self._send_chat_completion(
            messages,
            response_format={"type": "json_object"} if self.should_use_json_mode() else None,
        )
        try:
            content = payload["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise LLMError("LLM response did not contain text content")
            return parse_json_payload(content)
        except (KeyError, IndexError, TypeError, JSONDecodeError) as exc:
            raise LLMError("Failed to parse LLM JSON response") from exc

    def probe(self) -> dict[str, Any]:
        if not self.config.is_ready():
            raise LLMError("LLM config is not ready")

        started_at = datetime.now()
        payload = self._send_chat_completion(
            [{"role": "user", "content": "你好"}],
            response_format=None,
        )
        elapsed_ms = int((datetime.now() - started_at).total_seconds() * 1000)

        try:
            choice = payload["choices"][0]["message"]
            content = choice.get("content", "")
            reasoning_content = choice.get("reasoning_content", "")
            model = payload.get("model") or self.config.model
            return {
                "ok": True,
                "model": model,
                "content_preview": content[:120] if isinstance(content, str) else "",
                "reasoning_preview": reasoning_content[:120] if isinstance(reasoning_content, str) else "",
                "elapsed_ms": elapsed_ms,
            }
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Failed to parse LLM probe response") from exc

    def _send_chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        response_format: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if self.config.provider != "openai-compatible":
            raise LLMError(f"Unsupported LLM provider: {self.config.provider}")
        if not self.config.model:
            raise LLMError("Missing LLM model")
        if not self.config.api_key:
            raise LLMError(f"Missing API key in env var: {self.config.api_key_env}")

        endpoint = self.config.base_url.rstrip("/") + "/chat/completions"
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": 0.2,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            endpoint,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
            method="POST",
        )

        try:
            with request.urlopen(
                http_request,
                timeout=self.config.timeout_seconds,
                context=build_ssl_context(self.config.allow_insecure_tls),
            ) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise LLMError(f"LLM request failed with HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise LLMError(f"LLM request failed: {exc.reason}") from exc

        try:
            return json.loads(raw)
        except JSONDecodeError as exc:
            raise LLMError("Failed to parse LLM raw response") from exc

    def should_use_json_mode(self) -> bool:
        if not self.config.json_mode:
            return False
        model = (self.config.model or "").lower()
        if "thinking" in model:
            return False
        return True


def merge_llm_payload(insight: Insight, payload: dict[str, Any]) -> Insight:
    summary = payload.get("summary")
    why_it_repeats = payload.get("why_it_repeats")
    normalized_rules = payload.get("normalized_rules")

    if isinstance(summary, str) and summary.strip():
        insight.summary = summary.strip()
    if isinstance(why_it_repeats, list):
        cleaned_repeats = [item.strip() for item in why_it_repeats if isinstance(item, str) and item.strip()]
        if cleaned_repeats:
            insight.why_it_repeats = cleaned_repeats[:3]
    if isinstance(normalized_rules, list):
        cleaned_rules = [item.strip() for item in normalized_rules if isinstance(item, str) and item.strip()]
        if cleaned_rules:
            insight.normalized_rules = cleaned_rules[:5]
    return insight


def parse_json_payload(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except JSONDecodeError:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        return json.loads(cleaned)


def merge_batch_payload(insights: list[Insight], payload: dict[str, Any]) -> tuple[list[Insight], int]:
    items = payload.get("insights")
    if not isinstance(items, list):
        raise LLMError("LLM batch response did not contain insights array")

    by_title: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        if isinstance(title, str) and title.strip():
            by_title[title.strip()] = item

    merged: list[Insight] = []
    failures = 0
    for insight in insights:
        candidate = by_title.get(insight.title)
        if candidate is None:
            failures += 1
            merged.append(insight)
            continue
        merged.append(merge_llm_payload(insight, candidate))

    return merged, failures


def build_ssl_context(allow_insecure_tls: bool) -> ssl.SSLContext:
    if allow_insecure_tls:
        return ssl._create_unverified_context()  # noqa: SLF001

    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()
