#!/usr/bin/env python3
"""
YAML Bookmark Validator

This module provides functions for validating bookmark YAML data according to
the required format and constraints.

Validation rules:
1. Required fields: url, name, category, domain
2. No duplicate URLs across all files (even across different projects)
3. Domain field must match the URL's host
4. categories, tags, packages must be lists when present
5. category values must follow A/B or A/B/C format

Usage:
    from yaml_validator import validate_bookmarks
    
    # Validate a list of bookmarks
    has_errors = validate_bookmarks(bookmarks)
"""

import re
import sys
from urllib.parse import urlparse

def validate_bookmarks(bookmarks):
    """
    Validate a list of bookmark dictionaries against the required format and constraints.
    
    Args:
        bookmarks (list): List of bookmark dictionaries to validate
        
    Returns:
        bool: True if validation errors were found, False otherwise
    """
    has_errors = False
    all_urls = set()
    
    # Regular expression for category format (A/B or A/B/C)
    category_pattern = re.compile(r'^[^/]+/[^/]+(/[^/]+)?$')
    
    for bookmark in bookmarks:
        source_file = bookmark.get('_source_file', 'unknown')
        source_project = bookmark.get('_source_project', 'unknown')
        index = bookmark.get('_index', 0)
        
        # Format the location string for error messages
        if source_project == 'current':
            location = f"{source_file}, item {index}"
        else:
            location = f"{source_project}/{source_file}"
        
        # Remove metadata fields before validation
        bookmark_copy = bookmark.copy()
        for meta_field in ['_source_file', '_source_project', '_index']:
            if meta_field in bookmark_copy:
                del bookmark_copy[meta_field]
        
        # Check required fields
        required_fields = ['url', 'name', 'category', 'domain']
        for field in required_fields:
            if field not in bookmark_copy:
                print(f"Error in {location}: Missing required field '{field}'.", file=sys.stderr)
                has_errors = True
        
        # Skip further validation if required fields are missing
        if not all(field in bookmark_copy for field in required_fields):
            continue
        
        # Check for duplicate URLs
        url = bookmark_copy['url']
        if url in all_urls:
            print(f"Error in {location}: Duplicate URL '{url}'.", file=sys.stderr)
            has_errors = True
        else:
            all_urls.add(url)
        
        # Validate domain matches URL host
        try:
            parsed_url = urlparse(url)
            if parsed_url.netloc != bookmark_copy['domain']:
                print(f"Error in {location}: Domain '{bookmark_copy['domain']}' does not match URL host '{parsed_url.netloc}'.", file=sys.stderr)
                has_errors = True
        except Exception as e:
            print(f"Error in {location}: Invalid URL '{url}': {str(e)}", file=sys.stderr)
            has_errors = True
        
        # Validate category format
        if not category_pattern.match(bookmark_copy['category']):
            print(f"Error in {location}: Category '{bookmark_copy['category']}' does not match required format 'A/B' or 'A/B/C'.", file=sys.stderr)
            has_errors = True
        
        # Validate list fields
        list_fields = ['tags', 'packages']
        for field in list_fields:
            if field in bookmark_copy and not isinstance(bookmark_copy[field], list):
                print(f"Error in {location}: Field '{field}' must be a list.", file=sys.stderr)
                has_errors = True
    
    return has_errors

def find_yaml_files(base_dir):
    """
    Find all bookmark YAML files under the specified directory.
    
    Args:
        base_dir (str): The base directory to search for YAML files
        
    Returns:
        list: List of paths to YAML files
    """
    import os
    yaml_files = []
    
    if not os.path.exists(base_dir):
        print(f"Warning: Search directory {base_dir} does not exist.", file=sys.stderr)
        return yaml_files
    
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith(('.yml', '.yaml')):
                if '.git' in root:
                    continue
                yaml_files.append(os.path.join(root, file))
    
    return yaml_files

def load_yaml_file(yaml_file):
    """
    Load and parse a YAML file.
    
    Args:
        yaml_file (str): Path to the YAML file
        
    Returns:
        tuple: (bookmarks, has_errors) - List of bookmarks and error flag
    """
    import yaml
    bookmarks = []
    has_errors = False
    
    try:
        with open(yaml_file, 'r') as f:
            try:
                yaml_content = yaml.safe_load(f)
                if not yaml_content:
                    print(f"Info: Skipping empty or non-bookmark YAML file: {yaml_file}", file=sys.stderr)
                    return bookmarks, has_errors
                
                if not isinstance(yaml_content, list):
                    print(f"Error in {yaml_file}: Root element must be a list.", file=sys.stderr)
                    has_errors = True
                    return bookmarks, has_errors
                
                for i, bookmark in enumerate(yaml_content):
                    if not isinstance(bookmark, dict):
                        print(f"Error in {yaml_file}, item {i+1}: Bookmark must be a dictionary.", file=sys.stderr)
                        has_errors = True
                        continue
                    
                    # Add source info for error reporting
                    bookmark['_source_project'] = 'current'
                    bookmark['_source_file'] = yaml_file
                    bookmark['_index'] = i+1
                    
                    bookmarks.append(bookmark)
            
            except yaml.YAMLError as e:
                print(f"Error parsing {yaml_file}: {str(e)}", file=sys.stderr)
                has_errors = True
    except Exception as e:
        print(f"Error reading {yaml_file}: {str(e)}", file=sys.stderr)
        has_errors = True
    
    return bookmarks, has_errors

def load_current_project_bookmarks(current_dir):
    """
    Load all bookmarks from the current project.
    
    Args:
        current_dir (str): The current project directory
        
    Returns:
        tuple: (bookmarks, has_errors) - List of bookmarks and error flag
    """
    yaml_files = find_yaml_files(current_dir)
    if not yaml_files:
        print(f"No YAML files found in {current_dir}.", file=sys.stderr)
        return [], False
    
    print(f"Found {len(yaml_files)} YAML files to validate in current project.", file=sys.stderr)
    
    all_bookmarks = []
    has_errors = False
    
    for yaml_file in yaml_files:
        bookmarks, file_has_errors = load_yaml_file(yaml_file)
        all_bookmarks.extend(bookmarks)
        has_errors = has_errors or file_has_errors
    
    return all_bookmarks, has_errors