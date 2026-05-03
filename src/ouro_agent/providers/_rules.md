# providers Rules

1. Adapters return internal model-turn results, not raw SDK objects.
2. Do not import combat engine internals.
3. Real network calls must be replaceable by mock tests.
4. Provider failures must not corrupt run state.

