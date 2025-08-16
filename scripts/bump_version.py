#!/usr/bin/env python3
"""
Version bumping script for AWSUP
"""
import re
import sys
import argparse
from pathlib import Path


def get_current_version():
    """Get current version from pyproject.toml"""
    pyproject_path = Path(__file__).parent.parent / 'pyproject.toml'
    
    with open(pyproject_path, 'r') as f:
        content = f.read()
    
    match = re.search(r'version = "([^"]+)"', content)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    
    return match.group(1)


def bump_version(current_version, bump_type):
    """Bump version based on type (patch, minor, major)"""
    major, minor, patch = map(int, current_version.split('.'))
    
    if bump_type == 'patch':
        patch += 1
    elif bump_type == 'minor':
        minor += 1
        patch = 0
    elif bump_type == 'major':
        major += 1
        minor = 0
        patch = 0
    else:
        raise ValueError("bump_type must be 'patch', 'minor', or 'major'")
    
    return f"{major}.{minor}.{patch}"


def update_version_files(new_version):
    """Update version in all relevant files"""
    files_to_update = [
        ('pyproject.toml', r'version = "[^"]+"', f'version = "{new_version}"'),
        ('src/awsup/__init__.py', r'__version__ = "[^"]+"', f'__version__ = "{new_version}"'),
    ]
    
    for file_path, pattern, replacement in files_to_update:
        full_path = Path(__file__).parent.parent / file_path
        
        if not full_path.exists():
            print(f"Warning: {file_path} not found")
            continue
        
        with open(full_path, 'r') as f:
            content = f.read()
        
        updated_content = re.sub(pattern, replacement, content)
        
        with open(full_path, 'w') as f:
            f.write(updated_content)
        
        print(f"✅ Updated {file_path}")


def main():
    parser = argparse.ArgumentParser(description='Bump AWSUP version')
    parser.add_argument(
        'bump_type', 
        choices=['patch', 'minor', 'major'],
        help='Type of version bump'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Show what would be changed without making changes'
    )
    
    args = parser.parse_args()
    
    try:
        current_version = get_current_version()
        new_version = bump_version(current_version, args.bump_type)
        
        print(f"Current version: {current_version}")
        print(f"New version: {new_version}")
        
        if args.dry_run:
            print("🔍 Dry run - no changes made")
            return
        
        update_version_files(new_version)
        
        print(f"\n🎉 Version bumped to {new_version}!")
        print("\n📋 Next steps:")
        print(f"1. git add -A")
        print(f"2. git commit -m 'Bump version to {new_version}'")
        print(f"3. git tag v{new_version}")
        print(f"4. git push origin main --tags")
        print(f"5. GitHub Actions will auto-publish to PyPI")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()