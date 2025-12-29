import asyncio
from typing import Any, Dict, Optional

import aiohttp
from loguru import logger


class APIClient:
    """
    Asynchronous client for Freqtrade REST API using HTTP Basic Authentication.
    """

    def __init__(self, base_url: str, username: str, password: str):
        """
        Args:
            base_url: Root URL of Freqtrade API  'http://core:8080'.
            username: API username from config.json.
            password: API password from config.json.
        """
        self.base_url = base_url.rstrip("/")
        self._auth = aiohttp.BasicAuth(login=username, password=password)
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Returns active aiohttp session, creating one if needed.
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(auth=self._auth)
        return self._session

    async def _get_request(self, endpoint: str) -> Optional[Any]:
        """
        Generic helper for GET requests.
        """
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"

        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 401:
                    logger.error(f"Auth failed for {endpoint}: Invalid credentials")
                    return None
                else:
                    text = await response.text()
                    logger.warning(
                        f"API {endpoint} returned {response.status}: {text[:200]}"
                    )
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Network error calling {endpoint}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error calling {endpoint}: {e}")
            return None

    async def get_status(self) -> Optional[Dict[str, Any]]:
        """Retrieves bot configuration from /api/v1/show_config."""
        return await self._get_request("/api/v1/show_config")

    async def get_balance(self) -> Optional[Dict[str, Any]]:
        """Retrieves wallet balance from /api/v1/balance."""
        return await self._get_request("/api/v1/balance")

    async def get_daily_profit(self) -> Optional[Dict[str, Any]]:
        """Retrieves daily profit stats from /api/v1/daily."""
        return await self._get_request("/api/v1/daily")

    async def get_trades(self) -> Optional[Any]:
        """Retrieves open trades from /api/v1/status."""
        return await self._get_request("/api/v1/status")

    async def _post_request(self, endpoint: str) -> bool:
        """
        General helper for POST requests to the API.

        Args:
            endpoint: API endpoint (e.g., '/api/v1/start').

        Returns:
            True if status code is 200, False otherwise.
        """
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"

        try:
            async with session.post(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(
                        f"API Command Success: {endpoint} -> {data.get('status')}"
                    )
                    return True
                else:
                    text = await response.text()
                    logger.error(
                        f"API Command Failed: "
                        f"{endpoint} (Status: {response.status}) - {text[:200]}"
                    )
                    return False
        except Exception as e:
            logger.exception(f"Exception during POST {endpoint}: {e}")
            return False

    async def start(self) -> bool:
        """Starts the trading bot."""
        return await self._post_request("/api/v1/start")

    async def stop(self) -> bool:
        """Stops the trading bot."""
        return await self._post_request("/api/v1/stop")

    async def reload_config(self, retries: int = 3) -> bool:
        """Reloads the configuration (useful for hot-swapping params)."""
        for i in range(retries):
            if await self._post_request("/api/v1/reload_config"):
                return True
            if i < retries - 1:
                logger.info(f"Reload failed, retrying in 1s... ({i+1}/{retries})")
                await asyncio.sleep(1)
        return False

    async def close(self):
        """Closes the underlying aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
