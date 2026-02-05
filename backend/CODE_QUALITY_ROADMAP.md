# Code Quality Epic - Remaining Work Plan

**Status**: Phases 1-2 Complete ✅ | Phases 3-7 Planned 📋  
**Completed**: 217 violations (4% of total)  
**Remaining**: ~5,183 violations (96% of total)

---

## Phase 3: DTZ001/004/005/006/901 - Complete Timezone Migration 🟡

**Priority**: HIGH  
**Estimated Effort**: 3-4 days  
**Estimated Violations**: ~2,194

### Rules to Fix
| Rule | Description | Est. Count |
|------|-------------|------------|
| DTZ001 | `datetime()` without tzinfo | ~800 |
| DTZ004 | `datetime.utcfromtimestamp()` | ~200 |
| DTZ005 | `datetime.now()` without tzinfo | ~900 |
| DTZ006 | `datetime.fromtimestamp()` without tz | ~200 |
| DTZ901 | `datetime.min`/`max` without tz | ~94 |

### Fix Patterns

**DTZ001 - datetime() without tzinfo:**
```python
# OLD:
dt = datetime(2024, 1, 1, 12, 0, 0)

# NEW:
dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
```

**DTZ004 - utcfromtimestamp:**
```python
# OLD:
dt = datetime.utcfromtimestamp(timestamp)

# NEW:
dt = datetime.fromtimestamp(timestamp, tz=UTC)
```

**DTZ005 - datetime.now() without tzinfo:**
```python
# OLD:
now = datetime.now()

# NEW:
now = datetime.now(UTC)
```

**DTZ006 - fromtimestamp without tz:**
```python
# OLD:
dt = datetime.fromtimestamp(ts)

# NEW:
dt = datetime.fromtimestamp(ts, tz=UTC)
```

**DTZ901 - datetime.min/max:**
```python
# OLD:
min_date = datetime.min
max_date = datetime.max

# NEW:
min_date = datetime.min.replace(tzinfo=UTC)
max_date = datetime.max.replace(tzinfo=UTC)
```

### Implementation Strategy
1. **Batch 1**: Fix DTZ005 (most common, ~900 violations)
2. **Batch 2**: Fix DTZ001 (~800 violations)
3. **Batch 3**: Fix DTZ004/DTZ006 (~400 combined)
4. **Batch 4**: Fix DTZ901 (~94 violations)
5. **Run full test suite after each batch**
6. **Remove all DTZ rules from ignore list**

### Success Criteria
- ✅ All DTZ rules passing
- ✅ Full test suite passing
- ✅ No timezone-naive datetime operations in codebase

---

## Phase 4: ERA001 - Remove Commented Code 🟡

**Priority**: MEDIUM  
**Estimated Effort**: 1-2 days  
**Violations**: ~706

### What to Remove
- Dead code blocks commented out
- Debugging print statements
- Old implementations replaced by new code
- Experimental code that was never finalized

### What to Keep
- Intentional documentation comments explaining "why"
- Commented configuration examples
- License headers
- TODO/FIXME/NOTE comments

### Implementation Strategy
1. **Manual review**: Cannot be fully automated - requires context
2. **Batch by module**: Process one module at a time
3. **Use git blame**: Understand why code was commented out
4. **Document decisions**: Create issues for TODO items found

### Tools
```bash
# Find files with most commented code
ruff check . --select ERA001 --output-format=json | \
  jq -r '.[].filename' | sort | uniq -c | sort -rn | head -20
```

### Success Criteria
- ✅ ERA001 rule passing
- ✅ Important context preserved in issue tracker or docs
- ✅ Codebase easier to read and maintain

---

## Phase 5: ARG001/ARG002 - Unused Arguments 🟠

**Priority**: MEDIUM  
**Estimated Effort**: 3-4 days  
**Violations**: ~1,891

### Fix Patterns

**Truly unused - Remove:**
```python
# OLD:
def process_data(data, unused_param):
    return transform(data)

# NEW:
def process_data(data):
    return transform(data)
```

**Intentionally unused - Prefix with underscore:**
```python
# OLD:
def callback(event, context):  # context required by interface
    return handle(event)

# NEW:
def callback(event, _context):  # Explicit: unused but required
    return handle(event)
```

**Abstract methods - Document:**
```python
class BaseHandler:
    def handle(self, request: Request) -> Response:
        """Override in subclass. Request param required by interface."""
        raise NotImplementedError
```

### Implementation Strategy
1. **Categorize violations**: FastAPI deps, callbacks, abstract methods, truly unused
2. **Batch by category**: Fix similar patterns together
3. **Run tests after each batch**: Ensure no breakage
4. **Update type hints**: Remove from function signatures where appropriate

### Special Cases
- **FastAPI dependencies**: Keep unused Depends() - they enforce security/validation
- **Event handlers**: May need unused parameters to match callback signatures
- **Abstract base classes**: Document why parameters exist

### Success Criteria
- ✅ ARG001/ARG002 rules passing
- ✅ All tests passing
- ✅ Function signatures accurately reflect usage

---

## Phase 6: PTH*** - Pathlib Migration 🟢

**Priority**: LOW  
**Estimated Effort**: 2-3 days  
**Violations**: ~250

### Rules to Fix
| Rule | Description | Fix |
|------|-------------|-----|
| PTH103 | `os.makedirs()` | `Path.mkdir(parents=True)` |
| PTH108 | `os.unlink()` | `Path.unlink()` |
| PTH118 | `os.path.join()` | `Path() / "file"` |
| PTH123 | `open()` | `Path.open()` |

### Fix Patterns

**PTH118 - Path joining:**
```python
# OLD:
import os
path = os.path.join(base_dir, "uploads", filename)

# NEW:
from pathlib import Path
path = Path(base_dir) / "uploads" / filename
```

**PTH103 - Directory creation:**
```python
# OLD:
import os
os.makedirs(directory, exist_ok=True)

# NEW:
from pathlib import Path
Path(directory).mkdir(parents=True, exist_ok=True)
```

**PTH123 - File operations:**
```python
# OLD:
with open(filepath, "r") as f:
    content = f.read()

# NEW:
from pathlib import Path
content = Path(filepath).read_text()
```

### Implementation Strategy
1. **Batch by module**: One module at a time
2. **Start with utilities**: Low-risk, high-impact files first
3. **Test file operations**: Ensure paths work cross-platform
4. **Update type hints**: Use `Path` type in signatures

### Benefits
- Modern Python 3.12+ patterns
- Better cross-platform compatibility
- More readable path operations
- Type-safe path handling

### Success Criteria
- ✅ PTH*** rules passing
- ✅ All file operations tested
- ✅ Cross-platform path handling verified

---

## Phase 7: Mypy Strict Mode 🔵

**Priority**: FUTURE  
**Estimated Effort**: 5-7 days  
**Current Status**: Passing with lenient config

### Goals
1. Enable stricter type checking flags
2. Add missing type hints to untyped functions
3. Fix `Any` types with specific types
4. Ensure no `type: ignore` comments added without justification

### Current Config
```toml
[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # TODO: Enable
```

### Proposed Strict Config
```toml
[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true  # ✅ Enable
disallow_any_unimported = true  # ✅ Enable
disallow_any_generics = true  # ✅ Enable
no_implicit_optional = true  # ✅ Enable
strict_equality = true  # ✅ Enable
```

### Implementation Strategy
1. **Enable flags incrementally**: One flag at a time
2. **Fix by module**: Start with core modules
3. **Document complex types**: Add docstrings for complex type signatures
4. **Regular reviews**: Ensure type hints are accurate, not just silencing errors

### Success Criteria
- ✅ Strict mypy config passing
- ✅ All public APIs fully typed
- ✅ Type hints improve IDE autocomplete
- ✅ Type errors caught before runtime

---

## Effort Summary

| Phase | Priority | Days | Violations | % of Total |
|-------|----------|------|------------|------------|
| ✅ 1-2 (Complete) | HIGH | 1 | 217 | 4% |
| 3 (DTZ) | HIGH | 3-4 | ~2,194 | 40% |
| 4 (ERA) | MEDIUM | 1-2 | ~706 | 13% |
| 5 (ARG) | MEDIUM | 3-4 | ~1,891 | 35% |
| 6 (PTH) | LOW | 2-3 | ~250 | 5% |
| 7 (Mypy) | FUTURE | 5-7 | N/A | N/A |
| **TOTAL** | | **15-21 days** | **~5,258** | **100%** |

---

## Recommended Sprint Breakdown

### Sprint 1 (Week 1-2): High Priority Timezone Work
- **Phase 3**: Complete DTZ migration
- **Deliverable**: All datetime operations timezone-aware

### Sprint 2 (Week 3): Medium Priority Cleanup
- **Phase 4**: Remove commented code (ERA001)
- **Deliverable**: Cleaner, more readable codebase

### Sprint 3 (Week 4-5): Unused Arguments
- **Phase 5**: Fix ARG001/ARG002
- **Deliverable**: All function signatures accurate

### Sprint 4 (Week 6): Pathlib Migration
- **Phase 6**: PTH*** rules
- **Deliverable**: Modern Python path handling

### Sprint 5 (Future): Type Safety
- **Phase 7**: Strict mypy
- **Deliverable**: Production-grade type safety

---

## Automation Opportunities

### Scripts to Build
1. **`fix_dtz_all.py`** - Automate all remaining DTZ rules
2. **`analyze_era.py`** - Identify commented code by category
3. **`analyze_args.py`** - Categorize unused arguments by type
4. **`migrate_pathlib.py`** - Automate PTH migrations

### Reusable Patterns
The scripts built in Phases 1-2 can be extended:
- Pattern detection and replacement
- Import management (adding/updating)
- Batch processing with rollback
- Verification and testing

---

## Risk Mitigation

### High-Risk Areas
1. **Datetime operations in critical paths**: Auth, payments, scheduling
2. **File operations**: Ensure no data loss during pathlib migration
3. **Callback signatures**: Unused args may be required by interfaces

### Mitigation Strategies
1. **Incremental approach**: Small batches with frequent testing
2. **Feature flags**: Enable fixes gradually in production
3. **Comprehensive testing**: Integration tests for critical paths
4. **Rollback plan**: Git branches for each phase
5. **Monitoring**: Watch for runtime errors after deployment

---

## Success Metrics

### Code Quality
- **Linting violations**: 5,400 → 0 (100% reduction)
- **Type coverage**: Current → 90%+ (with strict mypy)
- **Test coverage**: Maintain 80%+ throughout

### Team Productivity
- **CI build time**: Monitor for regression
- **Developer velocity**: Should improve with cleaner codebase
- **Bug rate**: Should decrease with better type safety

### Production Stability
- **Runtime errors**: Should not increase
- **Performance**: Should not regress
- **User-facing bugs**: Zero tolerance for issues from refactoring

---

## Next Steps

1. **Review this plan** with tech lead
2. **Prioritize sprints** based on team capacity
3. **Set up monitoring** for production deployments
4. **Create tracking issues** for each phase
5. **Begin Phase 3** (DTZ migration)

---

**Document Version**: 1.0  
**Last Updated**: January 2025  
**Owner**: Development Team
