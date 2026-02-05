#!/usr/bin/env python3
"""
Script to migrate timezone-naive datetime calls to timezone-aware equivalents.
"""
import re
import sys
from pathlib import Path


def migrate_file(filepath: Path) -> tuple[bool, int]:
    """
    Migrate a single file.
    Returns (changed, num_changes)
    """
    try:
        content = filepath.read_text()
        original_content = content
        changes = 0
        
        # Track if we need to add UTC import
        needs_utc_import = False
        
        # Replace datetime.utcnow() with datetime.now(tz=datetime.UTC)
        utcnow_pattern = r'datetime\.utcnow\(\)'
        if re.search(utcnow_pattern, content):
            content = re.sub(utcnow_pattern, 'datetime.now(tz=datetime.UTC)', content)
            needs_utc_import = True
            changes += len(re.findall(utcnow_pattern, original_content))
        
        # Replace datetime.now() with datetime.now(tz=datetime.UTC)
        # But only if it doesn't already have tz= parameter
        now_pattern = r'datetime\.now\(\)(?!\s*-)'  # Don't match if followed by subtraction yet
        if re.search(r'datetime\.now\(\)', content):
            # More careful replacement - only replace if not already timezone-aware
            content = re.sub(r'datetime\.now\(\)(?!\s*\()', 'datetime.now(tz=datetime.UTC)', content)
            needs_utc_import = True
            changes += len(re.findall(r'datetime\.now\(\)', original_content))
        
        # Replace datetime.utcfromtimestamp(...) with datetime.fromtimestamp(..., tz=datetime.UTC)
        # This is more complex due to the argument
        utcfromtimestamp_pattern = r'datetime\.utcfromtimestamp\(([^)]+)\)'
        if re.search(utcfromtimestamp_pattern, content):
            content = re.sub(
                utcfromtimestamp_pattern,
                r'datetime.fromtimestamp(\1, tz=datetime.UTC)',
                content
            )
            needs_utc_import = True
            changes += len(re.findall(utcfromtimestamp_pattern, original_content))
        
        # Update imports if needed
        if needs_utc_import and changes > 0:
            # Check if datetime is imported
            has_datetime_import = 'from datetime import' in content or 'import datetime' in content
            
            if has_datetime_import:
                # Pattern 1: from datetime import datetime (but not UTC yet)
                # Need to check if UTC is already imported
                if 'from datetime import' in content and 'UTC' not in content.split('from datetime import')[1].split('\n')[0]:
                    # Find the import line and add UTC
                    import_pattern = r'from datetime import (datetime(?:,\s*\w+)*)'
                    match = re.search(import_pattern, content)
                    if match:
                        # Check if datetime is in the imports
                        if 'datetime' in match.group(1):
                            # Add UTC before datetime
                            content = re.sub(
                                r'from datetime import datetime\b',
                                'from datetime import UTC, datetime',
                                content,
                                count=1
                            )
        
        if content != original_content:
            filepath.write_text(content)
            return True, changes
        return False, 0
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False, 0


def main():
    backend_dir = Path(__file__).parent
    
    # Find all Python files
    python_files = list(backend_dir.rglob("*.py"))
    
    # Exclude this migration script and migrations folder
    python_files = [
        f for f in python_files 
        if f.name != "migrate_timezones.py" 
        and "/alembic/versions/" not in str(f)
        and "/migrations/" not in str(f)
    ]
    
    total_files = 0
    total_changes = 0
    
    print(f"Processing {len(python_files)} Python files...")
    
    for filepath in python_files:
        changed, num_changes = migrate_file(filepath)
        if changed:
            total_files += 1
            total_changes += num_changes
            print(f"✓ {filepath.relative_to(backend_dir)}: {num_changes} changes")
    
    print(f"\nMigration complete!")
    print(f"Files modified: {total_files}")
    print(f"Total changes: {total_changes}")


if __name__ == "__main__":
    main()
