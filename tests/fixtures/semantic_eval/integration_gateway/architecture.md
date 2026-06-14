# Architecture Notes

ProviderClient owns outbound model calls. GatewayService builds the retry
envelope, applies the token budget, and submits an EmbeddingJob. VectorIndex
stores embeddings by namespace and returns lookup ids.

TraceEvent connects GatewayService, ProviderClient, EmbeddingJob, and
VectorIndex so operators can diagnose slow provider responses without logging
raw document text.
