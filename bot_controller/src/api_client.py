import logging
from typing import Any, Dict, Optional, cast  # добавили cast

import aiohttp

logger = logging.getLogger(__name__)


class APIClient:

    def __init__(self, base_url: str):
        self.base_url = base_url

    async def get_status(self) -> Optional[Dict[str, Any]]:

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}/status") as response:
                    if response.status == 200:
                        data = cast(Dict[str, Any], await response.json())
                        return data
                    else:
                        logger.warning(f"API returned status {response.status}")
                        return None
            except Exception as e:
                logger.error(f"Failed to connect to API: {e}")
                return None
