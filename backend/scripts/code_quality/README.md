# Code Quality Scripts

Automation scripts for fixing linting violations in the ai-part-designer backend.

## Scripts

### `fix_dtz003.py`
**Status**: ✅ Used in Phase 1 - Complete

Automatically fixes DTZ003 violations by replacing `datetime.utcnow()` with `datetime.now(UTC)`.

**Usage:**
```bash
python scripts/code_quality/fix_dtz003.py
```

**What it does:**
1. Finds all files with `datetime.utcnow()` usage
2. Adds `UTC` to datetime imports if needed
3. Replaces all `datetime.utcnow()` calls with `datetime.now(UTC)`
4. Reports number of fixes per file

**Results**: Fixed 207 violations across 55 files

---

### `fix_ruf012.py`
**Status**: ✅ Used in Phase 2 - Partial Success

Automatically adds `ClassVar` annotations to mutable class attributes.

**Usage:**
```bash
python scripts/code_quality/fix_ruf012.py
```

**What it does:**
1. Finds all files with RUF012 violations
2. Adds `ClassVar` to typing imports if needed
3. Adds type annotations to mutable class attributes
4. Reports number of fixes per file

**Limitations:**
- Works for simple single-line attribute definitions
- Multi-line dict/list definitions require manual fixing
- Complex class hierarchies may need review

**Results**: Fixed 1/10 violations automatically; 9 required manual edits

---

## Future Scripts (Not Yet Implemented)

### `fix_dtz_all.py`
Fix all remaining DTZ rules (DTZ001, DTZ004, DTZ005, DTZ006, DTZ901).

### `analyze_era.py`
Analyze and categorize commented-out code (ERA001).

### `analyze_args.py`
Categorize unused arguments by type (FastAPI deps, callbacks, etc.).

### `migrate_pathlib.py`
Automate migration from os.path to pathlib (PTH***).

---

## Pattern Template

All scripts follow this pattern:

```python
#!/usr/bin/env python3
"""
Script to fix RULE_NAME violations.
"""
import re
from pathlib import Path

def get_files_to_fix() -> list[Path]:
    """Get files with violations from ruff."""
    # Use ruff to find violations
    pass

def fix_file(filepath: Path) -> tuple[bool, str]:
    """Fix violations in a file. Returns (modified, message)."""
    # Read, modify, write file
    pass

def main():
    """Main execution."""
    files = get_files_to_fix()
    # Process each file
    # Report results
    pass

if __name__ == '__main__':
    exit(main())
```

---

## Testing Scripts

Always test scripts on a sample file first:

```bash
# 1. Create backup
git stash

# 2. Run script on single file
python fix_script.py --file app/models/base.py

# 3. Review changes
git diff app/models/base.py

# 4. If good, run on all files
python fix_script.py

# 5. Verify no breakage
ruff check .
pytest tests/
```

---

## Best Practices

1. **Always use git**: Changes are bulk, need easy rollback
2. **Run ruff first**: Let it find violations, don't search manually
3. **Small batches**: Process files in logical groups
4. **Test frequently**: Run tests after each batch
5. **Manual review**: Spot-check automated changes
6. **Document patterns**: Update this README with lessons learned

---

## Lessons Learned

### What Worked Well
- **Ruff integration**: Using ruff to find violations is fast and accurate
- **Regex for simple cases**: Pattern matching works for straightforward replacements
- **Incremental approach**: Fixing small batches with frequent testing catches issues early

### Challenges
- **Multi-line definitions**: Hard to parse with regex alone
- **Context awareness**: Some fixes need understanding of business logic
- **Import management**: Adding imports requires careful placement (after `__future__`, before other imports)

### Improvements for Future Scripts
1. Use AST parsing instead of regex for complex cases
2. Add dry-run mode to preview changes
3. Support undo/rollback functionality
4. Add parallel processing for large codebases
5. Generate detailed change reports

---

**Created**: January 2025  
**Last Updated**: January 2025
