from .vector_index import VectorIndex


class ProviderClient:
    def embed(self, text: str, token_budget: int) -> list[float]:
        return [float(min(len(text), token_budget))]


class GatewayService:
    def __init__(self, provider: ProviderClient, index: VectorIndex):
        self.provider = provider
        self.index = index

    def run_embedding_job(self, document: str, namespace: str, token_budget: int) -> str:
        vector = self.provider.embed(document, token_budget)
        return self.index.upsert(namespace, vector)
