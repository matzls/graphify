# Integration Gateway Fixture

The integration gateway sends documents to the provider client with a token
budget and a retry envelope. Successful responses create an embedding job that
writes vectors into the vector index. Every request produces a trace event with
the provider name, retry count, and index namespace.

The gateway must not confuse retry envelopes with token budgets: retries govern
transport attempts, while token budgets bound prompt size.
