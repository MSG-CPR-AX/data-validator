#!/usr/bin/env python3
"""
Bookmark YAML Validator

This script validates bookmark YAML files in the repository to ensure they meet
the required format and constraints.

Validation rules:
1. Required fields: url, name, category, domain
2. No duplicate URLs across all files
3. Domain field must match the URL's host
4. categories, tags, packages must be lists when present
5. category values must follow A/B or A/B/C format
"""

import os
import re
import sys
import yaml
from urllib.parse import urlparse
from pathlib import Path

def find_yaml_files():
    """Find all bookmark YAML files in the repository."""
    yaml_files = []
    bookmark_dirs = [
        os.path.join('sidebar-data', 'bookmark-data', 'ops'),
        os.path.join('sidebar-data', 'bookmark-data', 'application')
    ]

    for base_dir in bookmark_dirs:
        if not os.path.exists(base_dir):
            continue
        for root, _, files in os.walk(base_dir):
            for file in files:
                if file.endswith('.yml'):
                    yaml_files.append(os.path.join(root, file))
    return yaml_files

def validate_bookmarks():
    """Validate all bookmark YAML files."""
    yaml_files = find_yaml_files()
    if not yaml_files:
        print("No YAML files found.", file=sys.stderr)
        return 1

    all_bookmarks = []
    all_urls = set()
    has_errors = False

    # Regular expression for category format (A/B or A/B/C)
    category_pattern = re.compile(r'^[^/]+/[^/]+(/[^/]+)?$')

    for yaml_file in yaml_files:
        try:
            with open(yaml_file, 'r') as f:
                try:
                    bookmarks = yaml.safe_load(f)
                    if not bookmarks:
                        continue

                    if not isinstance(bookmarks, list):
                        print(f"Error in {yaml_file}: Root element must be a list.", file=sys.stderr)
                        has_errors = True
                        continue

                    for i, bookmark in enumerate(bookmarks):
                        if not isinstance(bookmark, dict):
                            print(f"Error in {yaml_file}, item {i+1}: Bookmark must be a dictionary.", file=sys.stderr)
                            has_errors = True
                            continue

                        # Check required fields
                        required_fields = ['url', 'name', 'category', 'domain']
                        for field in required_fields:
                            if field not in bookmark:
                                print(f"Error in {yaml_file}, item {i+1}: Missing required field '{field}'.", file=sys.stderr)
                                has_errors = True

                        # Skip further validation if required fields are missing
                        if not all(field in bookmark for field in required_fields):
                            continue

                        # Check for duplicate URLs
                        url = bookmark['url']
                        if url in all_urls:
                            print(f"Error in {yaml_file}, item {i+1}: Duplicate URL '{url}'.", file=sys.stderr)
                            has_errors = True
                        else:
                            all_urls.add(url)

                        # Validate domain matches URL host
                        try:
                            parsed_url = urlparse(url)
                            if parsed_url.netloc != bookmark['domain']:
                                print(f"Error in {yaml_file}, item {i+1}: Domain '{bookmark['domain']}' does not match URL host '{parsed_url.netloc}'.", file=sys.stderr)
                                has_errors = True
                        except Exception as e:
                            print(f"Error in {yaml_file}, item {i+1}: Invalid URL '{url}': {str(e)}", file=sys.stderr)
                            has_errors = True

                        # Validate category format
                        if not category_pattern.match(bookmark['category']):
                            print(f"Error in {yaml_file}, item {i+1}: Category '{bookmark['category']}' does not match required format 'A/B' or 'A/B/C'.", file=sys.stderr)
                            has_errors = True

                        # Validate list fields
                        list_fields = ['tags', 'packages', 'categories']
                        for field in list_fields:
                            if field in bookmark and not isinstance(bookmark[field], list):
                                print(f"Error in {yaml_file}, item {i+1}: Field '{field}' must be a list.", file=sys.stderr)
                                has_errors = True

                        all_bookmarks.append(bookmark)

                except yaml.YAMLError as e:
                    print(f"Error parsing {yaml_file}: {str(e)}", file=sys.stderr)
                    has_errors = True
        except Exception as e:
            print(f"Error reading {yaml_file}: {str(e)}", file=sys.stderr)
            has_errors = True

    if has_errors:
        print("Validation failed. See errors above.", file=sys.stderr)
        return 1

    print(f"Validation successful. Found {len(all_bookmarks)} bookmarks in {len(yaml_files)} files.")
    return 0

if __name__ == "__main__":
    sys.exit(validate_bookmarks())