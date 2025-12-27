import base64
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
            base_url: Root URL of Freqtrade API (e.g., 'http://core:8080').
            username: API username from config.json.
            password: API password from config.json.
        """
        self.base_url = base_url.rstrip("/")
        self._auth_header = self._create_basic_auth_header(username, password)
        self._session: Optional[aiohttp.ClientSession] = None

    @staticmethod
    def _create_basic_auth_header(username: str, password: str) -> str:
        """
        Generates HTTP Basic Auth header value.

        Returns:
            Encoded 'Basic <base64>' string for Authorization header.
        """
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
        return f"Basic {encoded}"

    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Returns active aiohttp session, creating one if needed.
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def get_status(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves bot configuration from /api/v1/show_config endpoint.

        Returns:
            Dictionary with configuration data if successful, None otherwise.
        """
        session = await self._get_session()
        url = f"{self.base_url}/api/v1/show_config"
        headers = {"Authorization": self._auth_header}

        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                elif response.status == 401:
                    logger.error("Authentication failed: Invalid credentials")
                    return None
                else:
                    text = await response.text()
                    logger.warning(
                        f"API returned status {response.status}: {text[:200]}"
                    )
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Network error during API request: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error in get_status: {e}")
            return None

    async def close(self):
        """Closes the underlying aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
