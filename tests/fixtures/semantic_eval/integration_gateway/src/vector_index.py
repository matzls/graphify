class VectorIndex:
    def __init__(self):
        self._items = {}

    def upsert(self, namespace: str, vector: list[float]) -> str:
        lookup_id = f"{namespace}:{len(self._items)}"
        self._items[lookup_id] = vector
        return lookup_id
