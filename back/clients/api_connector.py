import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class ApiConnector:

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=headers or {},
            timeout=timeout,
        )
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    async def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        last_exception: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self._client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                last_exception = exc
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500:
                    raise

                if attempt < self._max_retries:
                    delay = self._retry_delay * (2 ** (attempt - 1))
                    logger.warning("Request %s %s failed (attempt %d/%d), retrying in %.1fs: %s",
                                   method, url, attempt, self._max_retries, delay, exc)
                    await asyncio.sleep(delay)

        raise last_exception  # type: ignore[misc]

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self._request_with_retry("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self._request_with_retry("POST", url, **kwargs)

    async def close(self) -> None:
        await self._client.aclose()
