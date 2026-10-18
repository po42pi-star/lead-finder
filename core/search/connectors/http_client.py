import asyncio
import logging

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from core.config.settings import Settings

logger = logging.getLogger(__name__)


class PoliteHttpClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = asyncio.Lock()
        self._client = httpx.AsyncClient(
            timeout=settings.search_http_timeout_sec,
            headers={
                "User-Agent": "NevatomLeadSearch/0.1 (+https://nevatom.local; legal-open-sources)",
                "Accept": "application/json, text/html, application/xml, */*",
            },
            follow_redirects=True,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _throttle(self) -> None:
        async with self._lock:
            await asyncio.sleep(self._settings.search_request_delay_sec)

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    async def get(self, url: str, **kwargs) -> httpx.Response:
        await self._throttle()
        response = await self._client.get(url, **kwargs)
        response.raise_for_status()
        return response

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    async def post(self, url: str, **kwargs) -> httpx.Response:
        await self._throttle()
        response = await self._client.post(url, **kwargs)
        response.raise_for_status()
        return response
