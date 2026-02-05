#!/usr/bin/env python3
"""
Script to fix RUF012 violations: Add ClassVar annotations to mutable class attributes.
"""
import re
from pathlib import Path
from typing import Set


def has_typing_import(content: str) -> bool:
    """Check if file has typing import."""
    return bool(re.search(r'from typing import', content) or re.search(r'import typing', content))


def has_classvar_import(content: str) -> bool:
    """Check if ClassVar is already imported."""
    return bool(re.search(r'from typing import.*ClassVar', content))


def add_classvar_to_import(content: str) -> str:
    """Add ClassVar to existing typing import."""
    # Pattern: from typing import [items]
    pattern = r'from typing import ([^\n]+?)(?=\n|$)'
    
    def replace_import(match):
        imports = match.group(1).strip()
        # Skip if ClassVar already in imports
        if 'ClassVar' in imports:
            return match.group(0)
        
        # Add ClassVar to the import list
        if '(' in imports:
            # Multi-line import - add after opening paren
            return match.group(0).replace('(', '(\n    ClassVar,', 1)
        else:
            # Single-line import - add ClassVar
            # Parse existing imports
            import_items = [item.strip() for item in imports.split(',')]
            import_items.insert(0, 'ClassVar')
            return f'from typing import {", ".join(import_items)}'
    
    modified = re.sub(pattern, replace_import, content, count=1)
    return modified


def add_typing_import(content: str) -> str:
    """Add typing import if not present."""
    # Find a good place to add the import (after __future__, before other imports)
    lines = content.split('\n')
    
    # Find insertion point
    insert_idx = 0
    in_docstring = False
    docstring_char = None
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Track docstrings
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                docstring_char = stripped[:3]
                if not stripped.endswith(docstring_char) or len(stripped) == 3:
                    in_docstring = True
                continue
        else:
            if docstring_char in line:
                in_docstring = False
            continue
        
        # Skip empty lines and comments at the top
        if not stripped or stripped.startswith('#'):
            continue
        
        # After __future__ imports
        if '__future__' in stripped:
            insert_idx = i + 1
            continue
        
        # Before any other import
        if stripped.startswith('import ') or stripped.startswith('from '):
            insert_idx = i
            break
        
        # Before any other code
        if stripped:
            insert_idx = i
            break
    
    # Insert the import
    lines.insert(insert_idx, 'from typing import ClassVar')
    return '\n'.join(lines)


def fix_mutable_attribute(content: str, line_num: int) -> str:
    """Fix a specific mutable class attribute by adding ClassVar annotation."""
    lines = content.split('\n')
    
    if line_num < 1 or line_num > len(lines):
        return content
    
    # Line numbers are 1-indexed
    line_idx = line_num - 1
    line = lines[line_idx]
    
    # Match patterns like:
    # attr_name = []
    # attr_name = {}
    # attr_name: dict = {}
    
    # Get indentation
    indent_match = re.match(r'^(\s*)', line)
    indent = indent_match.group(1) if indent_match else ''
    
    stripped = line.strip()
    
    # Check if already has ClassVar
    if 'ClassVar' in line:
        return content
    
    # Pattern 1: name = {} or name = []
    match1 = re.match(r'^(\w+)\s*=\s*(\{|\[)', stripped)
    if match1:
        name = match1.group(1)
        value = line[line.find('='):].strip()
        
        # Determine type
        if value.startswith('{'):
            type_hint = 'dict'
        elif value.startswith('['):
            type_hint = 'list'
        else:
            type_hint = ''
        
        if type_hint:
            lines[line_idx] = f'{indent}{name}: ClassVar[{type_hint}] = {value[2:]}'
        return '\n'.join(lines)
    
    # Pattern 2: name: type = value
    match2 = re.match(r'^(\w+):\s*([^=]+?)\s*=\s*(.+)$', stripped)
    if match2:
        name = match2.group(1)
        type_hint = match2.group(2).strip()
        value = match2.group(3).strip()
        
        # Add ClassVar wrapper
        lines[line_idx] = f'{indent}{name}: ClassVar[{type_hint}] = {value}'
        return '\n'.join(lines)
    
    return content


def get_violations() -> dict[Path, list[int]]:
    """Get RUF012 violations from ruff."""
    import subprocess
    
    result = subprocess.run(
        ['ruff', 'check', '.', '--select', 'RUF012', '--output-format=concise'],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )
    
    violations: dict[Path, list[int]] = {}
    for line in result.stdout.splitlines():
        if ':' in line:
            parts = line.split(':')
            if len(parts) >= 3:
                filepath = Path(__file__).parent / parts[0]
                line_num = int(parts[1])
                
                if filepath not in violations:
                    violations[filepath] = []
                violations[filepath].append(line_num)
    
    return violations


def fix_file(filepath: Path, line_nums: list[int]) -> tuple[bool, str]:
    """Fix RUF012 violations in a file."""
    try:
        content = filepath.read_text()
        original_content = content
        
        # Ensure ClassVar is imported
        if not has_classvar_import(content):
            if has_typing_import(content):
                content = add_classvar_to_import(content)
            else:
                content = add_typing_import(content)
        
        # Fix each violation (process in reverse order to maintain line numbers)
        for line_num in sorted(line_nums, reverse=True):
            content = fix_mutable_attribute(content, line_num)
        
        # Only write if content changed
        if content != original_content:
            filepath.write_text(content)
            return True, f"Fixed {len(line_nums)} violation(s)"
        
        return False, "No changes needed"
    
    except Exception as e:
        return False, f"Error: {e}"


def main():
    """Main execution."""
    print("🔍 Finding files with RUF012 violations...")
    violations = get_violations()
    
    print(f"📝 Found {len(violations)} files to fix\n")
    
    fixed_count = 0
    failed_files = []
    
    for filepath, line_nums in sorted(violations.items()):
        modified, message = fix_file(filepath, line_nums)
        status = "✅" if modified else "⏭️"
        print(f"{status} {filepath.relative_to(Path.cwd())}: {message}")
        
        if modified:
            fixed_count += 1
        elif "Error" in message:
            failed_files.append((filepath, message))
    
    print(f"\n{'='*60}")
    print(f"✨ Summary: Fixed {fixed_count}/{len(violations)} files")
    
    if failed_files:
        print(f"\n❌ Failed files ({len(failed_files)}):")
        for filepath, message in failed_files:
            print(f"  - {filepath.relative_to(Path.cwd())}: {message}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
