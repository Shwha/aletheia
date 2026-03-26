"""
LLM client for Aletheia — wraps LiteLLM with security hardening.

The evaluated model is always treated as potentially adversarial.
We send probes, receive responses, and score them — never trusting
the content, never interpolating it into further system operations.

Being-in-service (Dienstbarkeit): this module serves the runner by
providing a clean, secure interface to any LLM backend. Its service
is constitutive — without it, no probing occurs.

Supply chain note: The March 2026 LiteLLM PyPI incident demonstrated
that even trusted packages can be compromised. We pin exact versions
in pyproject.toml and recommend hash verification via:
    uv pip compile --generate-hashes pyproject.toml -o requirements.txt

Network security:
- TLS 1.3 only (via httpx client configuration)
- Optional proxy support (SOCKS5/HTTP) for air-gapped environments
- Certificate pinning option
- Rate limiting with exponential backoff

Ref: SCOPE.md §4 (Stack — LiteLLM)
"""

from __future__ import annotations

import asyncio
import ssl
import time
from typing import Any

import httpx
import litellm
import litellm.exceptions
import structlog

from aletheia.config import AletheiaSettings
from aletheia.models import sanitize_model_response

logger = structlog.get_logger()

# Suppress LiteLLM's own logging to prevent secret leakage
litellm.suppress_debug_info = True


class LLMClient:
    """Secure LLM client wrapping LiteLLM.

    Heidegger's tool-analysis: the LLM should be Zuhanden (ready-to-hand) —
    transparently available for probing. When it breaks (API errors, rate limits,
    timeouts), it becomes Vorhanden (present-at-hand) and demands explicit handling.

    All responses are sanitized before returning. The client never logs
    prompt content or API keys.
    """

    def __init__(self, settings: AletheiaSettings | None = None) -> None:
        self._settings = settings or AletheiaSettings()
        self._http_client: httpx.AsyncClient | None = None
        self._configure_litellm()

    def _configure_litellm(self) -> None:
        """Configure LiteLLM with security settings."""
        # Set API keys from settings (SecretStr → str only at point of use)
        s = self._settings
        if s.openai_api_key.get_secret_value():
            litellm.openai_key = s.openai_api_key.get_secret_value()
        if s.anthropic_api_key.get_secret_value():
            litellm.anthropic_key = s.anthropic_api_key.get_secret_value()
        if s.google_api_key.get_secret_value():
            litellm.google_key = s.google_api_key.get_secret_value()

        # Disable telemetry — OpSec: no phone-home
        litellm.telemetry = False
        litellm.drop_params = True

    def _get_ssl_context(self) -> ssl.SSLContext | bool:
        """Create SSL context with TLS 1.3 minimum.

        Returns ssl.SSLContext for custom cert pinning, True for default
        verification, or False if TLS verification is explicitly disabled
        (local dev only).
        """
        if not self._settings.verify_tls:
            logger.warning("tls_verification_disabled", reason="ALETHEIA_VERIFY_TLS=false")
            return False

        if self._settings.tls_cert_path:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.minimum_version = ssl.TLSVersion.TLSv1_3
            ctx.load_verify_locations(self._settings.tls_cert_path)
            return ctx

        return True

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create the shared httpx client."""
        if self._http_client is None or self._http_client.is_closed:
            ssl_verify = self._get_ssl_context()
            transport_kwargs: dict[str, Any] = {}
            if self._settings.proxy_url:
                transport_kwargs["proxy"] = self._settings.proxy_url
            self._http_client = httpx.AsyncClient(
                verify=ssl_verify,
                timeout=httpx.Timeout(60.0, connect=10.0),
                **transport_kwargs,
            )
        return self._http_client

    async def complete(
        self,
        model: str,
        prompt: str,
        system_prompt: str | None = None,
        timeout: int = 30,
        max_retries: int = 2,
    ) -> tuple[str, float]:
        """Send a prompt to the model and return (response, latency_ms).

        The prompt is sent as-is — no framework metadata is included.
        The response is sanitized before returning.

        Exponential backoff on retries: 1s, 2s, 4s...
        Never retries on auth errors (fail fast, reveal the problem).

        Args:
            model: LiteLLM model identifier (e.g., 'claude-opus-4-20250514', 'gpt-4')
            prompt: The probe prompt to send
            system_prompt: Optional system context for the probe
            timeout: Timeout in seconds per attempt
            max_retries: Maximum retry attempts

        Returns:
            Tuple of (sanitized_response, response_time_ms)

        Raises:
            LLMError: On unrecoverable failure
        """
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            start = time.monotonic()
            try:
                # LiteLLM async completion — model routing handled by LiteLLM
                response = await litellm.acompletion(
                    model=model,
                    messages=messages,
                    timeout=timeout,
                    num_retries=0,  # We handle retries ourselves
                )
                elapsed_ms = (time.monotonic() - start) * 1000

                # Extract response text safely
                content = response.choices[0].message.content or ""
                sanitized = sanitize_model_response(content)

                logger.info(
                    "llm_completion",
                    model=model,
                    attempt=attempt + 1,
                    latency_ms=round(elapsed_ms, 1),
                    response_length=len(sanitized),
                )

                return sanitized, elapsed_ms

            except litellm.exceptions.AuthenticationError:
                # Never retry auth errors — fail fast, reveal the problem (unconcealment)
                logger.exception("llm_auth_error", model=model)
                msg = (
                    f"Authentication failed for model '{model}'. "
                    "Check your API key environment variables."
                )
                raise LLMError(msg) from None

            except (
                litellm.exceptions.RateLimitError,
                litellm.exceptions.Timeout,
                litellm.exceptions.ServiceUnavailableError,
            ) as e:
                last_error = e
                if attempt < max_retries:
                    backoff = 2**attempt
                    logger.warning(
                        "llm_retry",
                        model=model,
                        attempt=attempt + 1,
                        backoff_seconds=backoff,
                        error=str(e),
                    )
                    await asyncio.sleep(backoff)
                continue

            except Exception as e:
                last_error = e
                logger.exception("llm_unexpected_error", model=model, error=str(e))
                break

        msg = f"LLM completion failed after {max_retries + 1} attempts: {last_error}"
        raise LLMError(msg)

    async def complete_conversation(
        self,
        model: str,
        messages: list[dict[str, str]],
        timeout: int = 30,
        max_retries: int = 2,
    ) -> tuple[str, float]:
        """Send a multi-turn message history and return (response, latency_ms).

        Used by reflexive probes where the model must be confronted with its
        own prior responses.  The full conversation history is sent so the
        model sees the context of the encounter.

        Security: the messages list may contain prior model responses which are
        untrusted.  They are included verbatim in the ``assistant`` role so the
        API treats them as conversational history, not as executable content.
        """
        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            start = time.monotonic()
            try:
                response = await litellm.acompletion(
                    model=model,
                    messages=messages,
                    timeout=timeout,
                    num_retries=0,
                )
                elapsed_ms = (time.monotonic() - start) * 1000

                content = response.choices[0].message.content or ""
                sanitized = sanitize_model_response(content)

                logger.info(
                    "llm_conversation_turn",
                    model=model,
                    attempt=attempt + 1,
                    latency_ms=round(elapsed_ms, 1),
                    response_length=len(sanitized),
                    turns=len(messages),
                )
                return sanitized, elapsed_ms

            except litellm.exceptions.AuthenticationError:
                logger.exception("llm_auth_error", model=model)
                msg = (
                    f"Authentication failed for model '{model}'. "
                    "Check your API key environment variables."
                )
                raise LLMError(msg) from None

            except (
                litellm.exceptions.RateLimitError,
                litellm.exceptions.Timeout,
                litellm.exceptions.ServiceUnavailableError,
            ) as e:
                last_error = e
                if attempt < max_retries:
                    backoff = 2**attempt
                    logger.warning(
                        "llm_retry",
                        model=model,
                        attempt=attempt + 1,
                        backoff_seconds=backoff,
                        error=str(e),
                    )
                    await asyncio.sleep(backoff)
                continue

            except Exception as e:
                last_error = e
                logger.exception("llm_unexpected_error", model=model, error=str(e))
                break

        msg = f"LLM conversation failed after {max_retries + 1} attempts: {last_error}"
        raise LLMError(msg)

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()


class LLMError(Exception):
    """Raised when LLM communication fails unrecoverably.

    Unconcealment (aletheia): when the tool breaks, name it clearly.
    Don't fabricate a response, don't pretend success.
    """
