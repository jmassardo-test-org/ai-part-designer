# Code Quality Quick Reference Guide

Quick reference for developers working on the ai-part-designer backend.

## ✅ Fixed Rules (Now Enforced)

### DTZ003: Timezone-Aware Datetimes

**❌ Don't:**
```python
from datetime import datetime
timestamp = datetime.utcnow()  # Creates naive datetime!
```

**✅ Do:**
```python
from datetime import UTC, datetime
timestamp = datetime.now(UTC)  # Creates timezone-aware datetime
```

**Why?** Naive datetimes can cause comparison errors and timezone bugs in production.

---

### RUF012: ClassVar for Mutable Class Attributes

**❌ Don't:**
```python
class MyClass:
    shared_list = []  # Mutable default!
    config = {"key": "value"}  # Can be mutated!
```

**✅ Do:**
```python
from typing import ClassVar

class MyClass:
    shared_list: ClassVar[list[str]] = []
    config: ClassVar[dict[str, str]] = {"key": "value"}
```

**Why?** Without `ClassVar`, all instances share the same mutable object, leading to unexpected behavior.

---

## ⏳ Temporarily Ignored Rules

### DTZ001, DTZ004, DTZ005, DTZ006, DTZ901
**Timezone-aware datetime usage** - Will be fixed in future phases.

### ARG001, ARG002  
**Unused arguments** - Prefix intentionally unused args with `_`:
```python
def callback(event, _context):  # _context is intentionally unused
    process(event)
```

### ERA001
**Commented-out code** - Use git history instead of commented code.

### PTH103, PTH108, PTH118, PTH123
**Pathlib usage** - Prefer `pathlib.Path` over `os.path`:
```python
# Prefer:
from pathlib import Path
path = Path("/data") / "file.txt"

# Over:
import os
path = os.path.join("/data", "file.txt")
```

---

## Pre-Commit Checklist

Before committing:
```bash
# 1. Format code
ruff format .

# 2. Check linting
ruff check .

# 3. Type check
mypy app

# 4. Run relevant tests
pytest tests/relevant_module/ -v
```

---

## Common Patterns

### Creating Timestamps
```python
from datetime import UTC, datetime

# Current time (timezone-aware)
now = datetime.now(UTC)

# Future/past times
from datetime import timedelta
expires_at = datetime.now(UTC) + timedelta(days=7)
```

### Class-Level Constants
```python
from typing import ClassVar

class APIHandler:
    # Immutable constants (no ClassVar needed)
    MAX_RETRIES = 3
    TIMEOUT_SECONDS = 30
    
    # Mutable constants (ClassVar required)
    ALLOWED_METHODS: ClassVar[list[str]] = ["GET", "POST"]
    DEFAULT_HEADERS: ClassVar[dict[str, str]] = {"User-Agent": "MyApp"}
    EXCLUDED_PATHS: ClassVar[set[str]] = {"/health", "/metrics"}
```

### Intentionally Unused Parameters
```python
# FastAPI dependency injection
from fastapi import Depends

def endpoint(
    user: User = Depends(get_current_user),  # Used
    _: None = Depends(require_admin),  # Unused but required for auth check
):
    return {"user": user.id}
```

---

## Need Help?

- **DTZ errors**: Ensure all datetime operations use `UTC` timezone
- **RUF012 errors**: Add `ClassVar` type annotation to mutable class attributes
- **Type errors**: Check that datetime objects are consistently timezone-aware

See `CODE_QUALITY_SUMMARY.md` for detailed information on recent changes.
