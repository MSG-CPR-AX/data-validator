#!/usr/bin/env python3
"""
Bookmark YAML Validator

This script validates bookmark YAML files across multiple projects within the bookmark-data group
to ensure they meet the required format and constraints.

Validation rules:
1. Required fields: url, name, category, domain
2. No duplicate URLs across all files (even across different projects)
3. Domain field must match the URL's host
4. categories, tags, packages must be lists when present
5. category values must follow A/B or A/B/C format
"""

import os
import sys
import yaml

# Import custom modules
from token_manager import get_token_from_env
from fetch_projects import fetch_all_bookmarks
from yaml_validator import validate_bookmarks, load_current_project_bookmarks

# This function is now imported from yaml_validator.py
# def find_yaml_files(base_dir):
#     """Find all bookmark YAML files under the specified directory."""
#     ...

# This function is now replaced by fetch_all_bookmarks from fetch_projects.py
# def fetch_other_projects_yaml(gitlab_url, token, group_id, exclude_project_id=None):
#     """Fetch YAML files from other projects in the bookmark-data group using GitLab API."""
#     ...

def validate_bookmarks_data(current_dir, fetch_others=True):
    """
    Validate bookmark YAML files in the current project and optionally fetch
    and validate bookmarks from other projects in the group.
    """
    # Load bookmarks from the current project
    current_bookmarks, has_errors = load_current_project_bookmarks(current_dir)

    if not current_bookmarks and not fetch_others:
        return 1

    all_bookmarks = current_bookmarks

    # Fetch bookmarks from other projects if requested
    if fetch_others:
        gitlab_url = os.environ.get('CI_SERVER_URL')
        group_id = os.environ.get('BOOKMARK_DATA_GROUP_ID')
        current_project_id = os.environ.get('CI_PROJECT_ID')

        # Check if deploy token environment variables are set
        if all([
            os.environ.get('ENCRYPTED_DEPLOY_TOKEN'),
            os.environ.get('ENCRYPTION_KEY'),
            os.environ.get('DEPLOY_TOKEN_USERNAME'),
            gitlab_url,
            group_id
        ]):
            try:
                # Get authentication headers using deploy token
                _, _, headers = get_token_from_env()

                print(f"Fetching bookmarks from other projects in group {group_id}...", file=sys.stderr)
                other_bookmarks = fetch_all_bookmarks(gitlab_url, headers, group_id, current_project_id)
                print(f"Found {len(other_bookmarks)} bookmarks in other projects.", file=sys.stderr)

                all_bookmarks.extend(other_bookmarks)
            except Exception as e:
                print(f"Error fetching bookmarks from other projects: {str(e)}", file=sys.stderr)
                has_errors = True
        else:
            print("Warning: Cannot fetch bookmarks from other projects. Required environment variables are missing.", file=sys.stderr)
            print("Required variables: ENCRYPTED_DEPLOY_TOKEN, ENCRYPTION_KEY, DEPLOY_TOKEN_USERNAME, CI_SERVER_URL, BOOKMARK_DATA_GROUP_ID", file=sys.stderr)

    # Validate all collected bookmarks
    validation_errors = validate_bookmarks(all_bookmarks)
    has_errors = has_errors or validation_errors

    if has_errors:
        print("Validation failed. See errors above.", file=sys.stderr)
        return 1

    print(f"Validation successful. Found {len(all_bookmarks)} bookmarks in total.")
    return 0

def main():
    # Check if running in CI environment
    in_ci = 'CI' in os.environ

    # Determine whether to fetch data from other projects
    # Only do this in CI environment and when required environment variables are set
    fetch_others = in_ci and all([
        os.environ.get('CI_SERVER_URL'),
        os.environ.get('BOOKMARK_DATA_GROUP_ID'),
        os.environ.get('ENCRYPTED_DEPLOY_TOKEN'),
        os.environ.get('ENCRYPTION_KEY'),
        os.environ.get('DEPLOY_TOKEN_USERNAME')
    ])

    if fetch_others:
        print("Running in CI environment with GitLab API access. Will validate bookmarks across all projects.", file=sys.stderr)
    else:
        print("Running in standalone mode. Will only validate local YAML files.", file=sys.stderr)
        if in_ci:
            print("To enable cross-project validation, set CI_SERVER_URL, BOOKMARK_DATA_GROUP_ID, ENCRYPTED_DEPLOY_TOKEN, ENCRYPTION_KEY, and DEPLOY_TOKEN_USERNAME environment variables.", file=sys.stderr)

    # Get the current directory to search for YAML files
    current_dir = os.environ.get('CI_PROJECT_DIR', '.')

    # Run validation
    return validate_bookmarks_data(current_dir, fetch_others)

if __name__ == "__main__":
    sys.exit(main())
