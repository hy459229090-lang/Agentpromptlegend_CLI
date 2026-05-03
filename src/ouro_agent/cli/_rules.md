# cli Rules

1. CLI parses input and calls services; it does not resolve combat rules.
2. Do not write API keys to disk.
3. Keep command output ASCII-safe by default.
4. Long-running game flows should delegate to `sessions`, `engine`, and `tui`.

