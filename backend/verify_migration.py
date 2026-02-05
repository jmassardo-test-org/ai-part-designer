#!/usr/bin/env python3
"""
Verification script for timezone migration.
"""
import re
from pathlib import Path


def verify_migration():
    """Verify all timezone-naive datetime calls have been migrated."""
    backend_dir = Path(__file__).parent
    python_files = [
        f for f in backend_dir.rglob("*.py") 
        if "/alembic/versions/" not in str(f) 
        and f.name not in ["migrate_timezones.py", "verify_migration.py"]
    ]
    
    issues = []
    
    for filepath in python_files:
        content = filepath.read_text()
        
        # Check for timezone-naive calls
        if re.search(r'\bdatetime\.utcnow\(\)', content):
            issues.append(f"{filepath}: Found datetime.utcnow()")
        
        if re.search(r'\bdatetime\.utcfromtimestamp\(', content):
            issues.append(f"{filepath}: Found datetime.utcfromtimestamp()")
        
        # Check for datetime.now() without tz parameter (excluding comments)
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if '#' in line:
                line = line[:line.index('#')]
            if re.search(r'\bdatetime\.now\(\)(?!\s*\()', line):
                issues.append(f"{filepath}:{i}: Found datetime.now() without tz parameter")
        
        # If file uses datetime.now(tz=datetime.UTC), ensure UTC is imported
        if 'datetime.now(tz=datetime.UTC)' in content or 'datetime.fromtimestamp(' in content:
            if 'from datetime import' in content:
                import_lines = [line for line in lines if 'from datetime import' in line]
                has_utc = any('UTC' in line for line in import_lines)
                if not has_utc:
                    issues.append(f"{filepath}: Uses datetime.UTC but UTC not imported")
    
    if issues:
        print("❌ Migration verification FAILED\n")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("✅ Migration verification PASSED")
        print(f"   Checked {len(python_files)} Python files")
        print("   No timezone-naive datetime calls found")
        print("   All imports correctly updated")
        return True


if __name__ == "__main__":
    success = verify_migration()
    exit(0 if success else 1)
