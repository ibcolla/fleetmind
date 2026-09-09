"""
FleetMind — In-Memory Supabase Client Mock
-------------------------------------------
Provides a lightweight, fully functional mock for Supabase's Python client v2
including database tables, updates, and Supabase Storage bucket operations.
Used during pytest runs so unit and integration tests run fast, isolated, and offline.
"""

import uuid
from typing import Any, Dict, List, Optional


class MockSupabaseResponse:
    def __init__(self, data: List[Dict[str, Any]]):
        self.data = data


class MockQueryBuilder:
    def __init__(self, table_name: str, store: Dict[str, List[Dict[str, Any]]]):
        self.table_name = table_name
        self.store = store
        self._filters: List[tuple] = []
        self._order: Optional[tuple] = None
        self._limit: Optional[int] = None
        self._insert_data: Optional[Any] = None
        self._update_data: Optional[Dict[str, Any]] = None

    def select(self, *args, **kwargs) -> "MockQueryBuilder":
        return self

    def insert(self, data: Any, *args, **kwargs) -> "MockQueryBuilder":
        self._insert_data = data
        return self

    def update(self, data: Dict[str, Any], *args, **kwargs) -> "MockQueryBuilder":
        self._update_data = data
        return self

    def eq(self, column: str, value: Any) -> "MockQueryBuilder":
        self._filters.append((column, value))
        return self

    def order(self, column: str, desc: bool = False) -> "MockQueryBuilder":
        self._order = (column, desc)
        return self

    def limit(self, count: int) -> "MockQueryBuilder":
        self._limit = count
        return self

    async def execute(self) -> MockSupabaseResponse:
        table_rows = self.store.setdefault(self.table_name, [])

        if self._insert_data is not None:
            items = self._insert_data if isinstance(self._insert_data, list) else [self._insert_data]
            inserted = []
            for item in items:
                row = dict(item)
                if "id" not in row and self.table_name != "workspace_users":
                    row["id"] = str(uuid.uuid4())
                if self.table_name == "workspaces":
                    row.setdefault("subscription_status", "free")
                    row.setdefault("agent_runs_count", 0)
                table_rows.append(row)
                inserted.append(row)
            return MockSupabaseResponse(inserted)

        if self._update_data is not None:
            updated = []
            for row in table_rows:
                match = True
                for col, val in self._filters:
                    if row.get(col) != val:
                        match = False
                        break
                if match:
                    row.update(self._update_data)
                    updated.append(row)
            return MockSupabaseResponse(updated)

        # SELECT path
        result = list(table_rows)
        for col, val in self._filters:
            result = [r for r in result if r.get(col) == val]

        if self._order:
            col, desc = self._order
            result.sort(key=lambda r: r.get(col, ""), reverse=desc)

        if self._limit is not None:
            result = result[: self._limit]

        return MockSupabaseResponse(result)


class MockSignedUrlResponse:
    def __init__(self, signed_url: str):
        self.signed_url = signed_url
        self.signedUrl = signed_url
        self.signedURL = signed_url

    def get(self, key, default=None):
        return getattr(self, key, default)


class MockStorageBucket:
    def __init__(self, bucket_name: str, storage_store: Dict[str, Dict[str, bytes]]):
        self.bucket_name = bucket_name
        self.storage_store = storage_store.setdefault(bucket_name, {})

    async def upload(self, path: str, file: bytes, file_options: Optional[Dict] = None) -> Dict[str, str]:
        self.storage_store[path] = file
        return {"path": path, "id": str(uuid.uuid4())}

    async def create_signed_url(self, path: str, expires_in: int = 3600) -> MockSignedUrlResponse:
        url = f"https://test-project.supabase.co/storage/v1/object/sign/{self.bucket_name}/{path}?token=mock_token_123"
        return MockSignedUrlResponse(url)

    def get_public_url(self, path: str) -> str:
        return f"https://test-project.supabase.co/storage/v1/object/public/{self.bucket_name}/{path}"


class MockStorageClient:
    def __init__(self):
        self.buckets: Dict[str, Dict[str, bytes]] = {}

    def from_(self, bucket_name: str) -> MockStorageBucket:
        return MockStorageBucket(bucket_name, self.buckets)


class MockSupabaseClient:
    def __init__(self):
        self.store: Dict[str, List[Dict[str, Any]]] = {
            "workspaces": [],
            "workspace_users": [],
            "signals": [],
            "actions": [],
        }
        self.storage = MockStorageClient()

    def table(self, name: str) -> MockQueryBuilder:
        return MockQueryBuilder(name, self.store)

    def from_(self, name: str) -> MockQueryBuilder:
        return self.table(name)

    def clear(self) -> None:
        for k in self.store:
            self.store[k].clear()
        self.storage.buckets.clear()
