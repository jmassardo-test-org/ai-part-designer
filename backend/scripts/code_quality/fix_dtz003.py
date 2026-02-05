#!/usr/bin/env python3
"""
Script to fix DTZ003 violations: Replace datetime.utcnow() with datetime.now(UTC)
"""
import re
from pathlib import Path
from typing import Set


def has_datetime_import(content: str) -> bool:
    """Check if file already imports datetime."""
    return bool(re.search(r'from datetime import.*datetime', content))


def has_utc_import(content: str) -> bool:
    """Check if file already imports UTC."""
    return bool(re.search(r'from datetime import.*UTC', content))


def add_utc_to_import(content: str) -> str:
    """Add UTC to existing datetime import."""
    # Pattern: from datetime import [items]
    pattern = r'from datetime import ([^\n]+)'
    
    def replace_import(match):
        imports = match.group(1).strip()
        # Skip if UTC already in imports
        if 'UTC' in imports:
            return match.group(0)
        
        # Add UTC to the import list
        # Handle both single-line and potential multi-line imports
        if '(' in imports:
            # Multi-line import
            return match.group(0).replace('(', '(UTC, ', 1)
        else:
            # Single-line import - add UTC at the beginning for consistency
            return f'from datetime import UTC, {imports}'
    
    return re.sub(pattern, replace_import, content)


def replace_utcnow(content: str) -> str:
    """Replace datetime.utcnow() with datetime.now(UTC)."""
    # Replace datetime.utcnow() with datetime.now(UTC)
    return re.sub(r'datetime\.utcnow\(\)', 'datetime.now(UTC)', content)


def fix_file(filepath: Path) -> tuple[bool, str]:
    """
    Fix DTZ003 violations in a file.
    Returns (modified, message)
    """
    try:
        content = filepath.read_text()
        original_content = content
        
        # Check if file has datetime.utcnow()
        if 'datetime.utcnow()' not in content:
            return False, "No datetime.utcnow() found"
        
        # Ensure UTC is imported
        if has_datetime_import(content) and not has_utc_import(content):
            content = add_utc_to_import(content)
        
        # Replace datetime.utcnow() with datetime.now(UTC)
        content = replace_utcnow(content)
        
        # Only write if content changed
        if content != original_content:
            filepath.write_text(content)
            occurrences = original_content.count('datetime.utcnow()')
            return True, f"Fixed {occurrences} occurrence(s)"
        
        return False, "No changes needed"
    
    except Exception as e:
        return False, f"Error: {e}"


def get_files_to_fix() -> list[Path]:
    """Get list of files with DTZ003 violations from ruff."""
    import subprocess
    
    result = subprocess.run(
        ['ruff', 'check', '.', '--select', 'DTZ003', '--output-format=concise'],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )
    
    files: Set[Path] = set()
    for line in result.stdout.splitlines():
        if ':' in line:
            filepath = line.split(':')[0]
            files.add(Path(__file__).parent / filepath)
    
    return sorted(files)


def main():
    """Main execution."""
    print("🔍 Finding files with DTZ003 violations...")
    files = get_files_to_fix()
    
    print(f"📝 Found {len(files)} files to fix\n")
    
    fixed_count = 0
    failed_files = []
    
    for filepath in files:
        modified, message = fix_file(filepath)
        status = "✅" if modified else "⏭️"
        print(f"{status} {filepath.relative_to(Path.cwd())}: {message}")
        
        if modified:
            fixed_count += 1
        elif "Error" in message:
            failed_files.append((filepath, message))
    
    print(f"\n{'='*60}")
    print(f"✨ Summary: Fixed {fixed_count}/{len(files)} files")
    
    if failed_files:
        print(f"\n❌ Failed files ({len(failed_files)}):")
        for filepath, message in failed_files:
            print(f"  - {filepath.relative_to(Path.cwd())}: {message}")
    
    return 0 if not failed_files else 1


if __name__ == '__main__':
    exit(main())
