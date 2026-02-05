# Example Changes - Timezone Migration

## Example 1: Simple datetime.utcnow() replacement

### Before:
```python
from datetime import datetime

def soft_delete(self) -> None:
    """Mark the record as deleted."""
    self.deleted_at = datetime.utcnow()
```

### After:
```python
from datetime import UTC, datetime

def soft_delete(self) -> None:
    """Mark the record as deleted."""
    self.deleted_at = datetime.now(tz=datetime.UTC)
```

**File:** `app/models/base.py`

---

## Example 2: datetime.utcfromtimestamp() replacement

### Before:
```python
from datetime import datetime, timedelta

def verify_token(token: str, expected_type: str | None = None) -> dict | None:
    # ...
    exp = payload.get("exp")
    if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
        return None
```

### After:
```python
from datetime import UTC, datetime, timedelta

def verify_token(token: str, expected_type: str | None = None) -> dict | None:
    # ...
    exp = payload.get("exp")
    if exp and datetime.fromtimestamp(exp, tz=datetime.UTC) < datetime.now(tz=datetime.UTC):
        return None
```

**File:** `app/core/security.py`

---

## Example 3: SQLAlchemy column defaults

### Before:
```python
from datetime import datetime

joined_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
    default=datetime.utcnow,
)
```

### After:
```python
from datetime import UTC, datetime

joined_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
    default=lambda: datetime.now(tz=datetime.UTC),
)
```

**File:** `app/models/organization.py`

---

## Example 4: SQLAlchemy onupdate

### Before:
```python
from datetime import datetime

updated_at = Column(
    DateTime(timezone=True),
    default=datetime.utcnow,
    onupdate=datetime.utcnow,
    nullable=False,
)
```

### After:
```python
from datetime import UTC, datetime

updated_at = Column(
    DateTime(timezone=True),
    default=lambda: datetime.now(tz=datetime.UTC),
    onupdate=lambda: datetime.now(tz=datetime.UTC),
    nullable=False,
)
```

**File:** `app/models/reference_component.py`

---

## Example 5: Dataclass field defaults

### Before:
```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ModerationResult:
    timestamp: datetime = field(default_factory=datetime.utcnow)
    is_prohibited: bool = False
```

### After:
```python
from dataclasses import dataclass, field
from datetime import UTC, datetime

@dataclass
class ModerationResult:
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=datetime.UTC))
    is_prohibited: bool = False
```

**File:** `app/services/content_moderation.py`

---

## Example 6: Multiple occurrences in one file

### Before:
```python
from datetime import datetime

def mark_read(self) -> None:
    """Mark notification as read."""
    self.is_read = True
    self.read_at = datetime.now()

@property
def is_expired(self) -> bool:
    """Check if notification has expired."""
    if not self.expires_at:
        return False
    return datetime.now() > self.expires_at
```

### After:
```python
from datetime import UTC, datetime

def mark_read(self) -> None:
    """Mark notification as read."""
    self.is_read = True
    self.read_at = datetime.now(tz=datetime.UTC)

@property
def is_expired(self) -> bool:
    """Check if notification has expired."""
    if not self.expires_at:
        return False
    return datetime.now(tz=datetime.UTC) > self.expires_at
```

**File:** `app/models/notification.py`

---

## Key Patterns

### Pattern 1: Direct function call
```python
# Before: datetime.utcnow()
# After:  datetime.now(tz=datetime.UTC)
```

### Pattern 2: Timestamp conversion
```python
# Before: datetime.utcfromtimestamp(ts)
# After:  datetime.fromtimestamp(ts, tz=datetime.UTC)
```

### Pattern 3: As callable (no parentheses)
```python
# Before: default=datetime.utcnow
# After:  default=lambda: datetime.now(tz=datetime.UTC)
```

### Pattern 4: As factory
```python
# Before: field(default_factory=datetime.utcnow)
# After:  field(default_factory=lambda: datetime.now(tz=datetime.UTC))
```

---

## Import Changes

All files using the new syntax had their imports updated:

```python
# Before
from datetime import datetime

# After
from datetime import UTC, datetime
```

Or if timedelta was already imported:

```python
# Before
from datetime import datetime, timedelta

# After
from datetime import UTC, datetime, timedelta
```

---

## What Was NOT Changed

1. **Server-side defaults**: `server_default=func.now()` - These use PostgreSQL's timezone-aware now() function
2. **Comments**: Comments mentioning datetime.utcnow() were left unchanged
3. **String literals**: Any strings containing "utcnow" were not modified
4. **Already timezone-aware calls**: `datetime.now(UTC)` or `datetime.now(timezone.utc)` were left as-is

