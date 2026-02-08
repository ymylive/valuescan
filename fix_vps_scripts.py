#!/usr/bin/env python3
"""
Batch fix hardcoded VPS passwords in deployment scripts.
Replaces hardcoded password with environment variable pattern.
"""
import os
import re
from pathlib import Path

def fix_vps_script(file_path):
    """Fix hardcoded password in a single script file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        original = content

        # Pattern 1: password='Qq159741'
        content = re.sub(
            r"password\s*=\s*['\"]Qq159741['\"]",
            "password=os.environ.get('VPS_PASSWORD', '')",
            content
        )

        # Pattern 2: password="Qq159741"
        content = re.sub(
            r'password\s*=\s*"Qq159741"',
            "password=os.environ.get('VPS_PASSWORD', '')",
            content
        )

        # Add os import if password was changed and os not imported
        if content != original and 'import os' not in content:
            # Add import after shebang or at the beginning
            lines = content.split('\n')
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.startswith('#!'):
                    insert_pos = i + 1
                    break
            lines.insert(insert_pos, 'import os')
            content = '\n'.join(lines)

        if content != original:
            file_path.write_text(content, encoding='utf-8')
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Fix all VPS scripts in .github_export/scripts/"""
    base_dir = Path(__file__).parent
    scripts_dir = base_dir / '.github_export' / 'scripts'

    if not scripts_dir.exists():
        print(f"Directory not found: {scripts_dir}")
        return

    fixed_count = 0
    total_count = 0

    for script_file in scripts_dir.glob('*.py'):
        total_count += 1
        if fix_vps_script(script_file):
            fixed_count += 1
            print(f"Fixed: {script_file.name}")

    print(f"\nSummary: Fixed {fixed_count} out of {total_count} scripts")

if __name__ == '__main__':
    main()
