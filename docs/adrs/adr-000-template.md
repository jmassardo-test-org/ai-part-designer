# ADR-000: ADR Template

## Status
Accepted

## Context
We need a consistent format for documenting architecture decisions to ensure:
- Decisions are captured with their rationale
- Future team members can understand why decisions were made
- We can revisit decisions when context changes

## Decision
We will use Architecture Decision Records (ADRs) in Markdown format, stored in the `docs/adrs/` directory.

Each ADR will follow this template structure:
- **Status**: Proposed | Accepted | Deprecated | Superseded
- **Context**: The issue motivating the decision
- **Decision**: What we're doing
- **Consequences**: What becomes easier/harder
- **Options Considered**: Alternatives evaluated
- **References**: Supporting documentation

## Consequences
### Positive
- Consistent documentation format
- Easy to review in pull requests
- Version controlled with code

### Negative
- Requires discipline to maintain
- Another document to keep updated

## References
- [Michael Nygard's original ADR article](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- [ADR GitHub organization](https://adr.github.io/)
