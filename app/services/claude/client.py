"""Async Claude API client wrapper."""

import asyncio
from typing import Optional
import logging

from anthropic import AsyncAnthropic, APIError, RateLimitError

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ClaudeAPIError(Exception):
    """Custom exception for Claude API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        is_retryable: bool = False,
    ):
        self.message = message
        self.status_code = status_code
        self.is_retryable = is_retryable
        super().__init__(message)


class ClaudeClient:
    """Async client for Claude API.

    Features:
    - Async/await pattern
    - Automatic retries with exponential backoff
    - Token usage tracking
    - Error handling with custom exceptions
    """

    MAX_RETRIES = 3
    BASE_DELAY = 1.0  # seconds

    def __init__(self) -> None:
        """Initialize the Claude client."""
        if not settings.ANTHROPIC_API_KEY:
            raise ClaudeAPIError("ANTHROPIC_API_KEY not configured")

        self._client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
    ) -> str:
        """Generate text using Claude API.

        Args:
            prompt: The user message/prompt
            system_prompt: Optional system message for context
            max_tokens: Maximum tokens in response (default from settings)
            temperature: Sampling temperature (0-1)

        Returns:
            Generated text content

        Raises:
            ClaudeAPIError: If generation fails after retries
        """
        max_tokens = max_tokens or settings.CLAUDE_MAX_TOKENS
        last_error: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES):
            try:
                response = await self._client.messages.create(
                    model=settings.CLAUDE_MODEL,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt or "",
                    messages=[{"role": "user", "content": prompt}],
                )

                # Track token usage
                if response.usage:
                    self._total_input_tokens += response.usage.input_tokens
                    self._total_output_tokens += response.usage.output_tokens

                # Extract text content
                content = ""
                for block in response.content:
                    if block.type == "text":
                        content += block.text

                logger.info(
                    f"Claude generation successful. "
                    f"Tokens: {response.usage.input_tokens} in, "
                    f"{response.usage.output_tokens} out"
                )

                return content

            except RateLimitError as e:
                last_error = e
                delay = self.BASE_DELAY * (2**attempt)
                logger.warning(
                    f"Claude rate limit hit, retrying in {delay}s "
                    f"(attempt {attempt + 1}/{self.MAX_RETRIES})"
                )
                await asyncio.sleep(delay)

            except APIError as e:
                last_error = e
                # Only retry on 5xx errors
                if e.status_code and e.status_code >= 500:
                    delay = self.BASE_DELAY * (2**attempt)
                    logger.warning(
                        f"Claude API error {e.status_code}, retrying in {delay}s "
                        f"(attempt {attempt + 1}/{self.MAX_RETRIES})"
                    )
                    await asyncio.sleep(delay)
                else:
                    # Non-retryable error
                    logger.error(f"Claude API error: {e}")
                    raise ClaudeAPIError(
                        message=str(e),
                        status_code=e.status_code,
                        is_retryable=False,
                    )

            except Exception as e:
                logger.error(f"Unexpected error calling Claude: {e}")
                raise ClaudeAPIError(
                    message=f"Unexpected error: {str(e)}",
                    is_retryable=False,
                )

        # All retries exhausted
        error_msg = f"Claude API failed after {self.MAX_RETRIES} attempts"
        if last_error:
            error_msg += f": {str(last_error)}"
        logger.error(error_msg)
        raise ClaudeAPIError(message=error_msg, is_retryable=True)

    @property
    def total_input_tokens(self) -> int:
        """Get total input tokens used across all requests."""
        return self._total_input_tokens

    @property
    def total_output_tokens(self) -> int:
        """Get total output tokens used across all requests."""
        return self._total_output_tokens

    @property
    def total_tokens(self) -> int:
        """Get total tokens (input + output) used."""
        return self._total_input_tokens + self._total_output_tokens


# Singleton instance
_client: Optional[ClaudeClient] = None


def get_claude_client() -> ClaudeClient:
    """Get or create the Claude client singleton.

    Returns:
        ClaudeClient instance

    Raises:
        ClaudeAPIError: If API key not configured
    """
    global _client
    if _client is None:
        _client = ClaudeClient()
    return _client
