import json
import os
import aiofiles
from aiogram.fsm.storage.base import BaseStorage, StorageKey, StateType
from typing import Any, Dict, Optional

class JSONStorage(BaseStorage):
    """
    A simple JSON-based persistent storage for Aiogram FSM.
    """
    def __init__(self, file_path: str = "fsm_data.json"):
        self.file_path = file_path
        self._data: Dict[str, Dict[str, Any]] = {"states": {}, "data": {}}
        self._load_sync()

    def _load_sync(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content:
                        self._data = json.loads(content)
            except Exception as e:
                print(f"Error loading JSONStorage: {e}")
        
        if "states" not in self._data:
            self._data["states"] = {}
        if "data" not in self._data:
            self._data["data"] = {}

    async def _save(self):
        try:
            async with aiofiles.open(self.file_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(self._data, ensure_ascii=False))
        except Exception as e:
            print(f"Error saving JSONStorage: {e}")

    def _get_key(self, key: StorageKey) -> str:
        return f"{key.bot_id}:{key.chat_id}:{key.user_id}"

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        k = self._get_key(key)
        if state is None:
            self._data["states"].pop(k, None)
        else:
            self._data["states"][k] = state.state if hasattr(state, "state") else state
        
        await self._save()

    async def get_state(self, key: StorageKey) -> Optional[str]:
        k = self._get_key(key)
        return self._data["states"].get(k)

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        k = self._get_key(key)
        if not data:
            self._data["data"].pop(k, None)
        else:
            self._data["data"][k] = data
            
        await self._save()

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        k = self._get_key(key)
        return self._data["data"].get(k, {})

    async def close(self) -> None:
        await self._save()
