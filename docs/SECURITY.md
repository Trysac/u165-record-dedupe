# Security notes

## Threat model

`record-dedupe` is a pure Python library without I/O operations, reducing the attack surface significantly. 

### Defended

- **Configurational Errors**: Explicit validation is performed in `DedupeConfig.__post_init__` to prevent invalid states, such as threshold overflows or excessive rule counts, raising `DedupeError`.
- **Resource Exhaustion**: The library limits resource usage via `max_records` (default 50,000) and `max_block_size` (default 1,000). Requests exceeding these bounds raise `DedupeError` with the appropriate machine-readable code.

### Not defended

- **Hostile Input**: Callers may pass arbitrary strings. The library assumes the caller validates data or handles potential `DedupeError` exceptions. 
- **Supply chain**: While we maintain zero runtime dependencies to minimize exposure, the library relies on standard supply chain practices (e.g., dependency updates, pinned actions).