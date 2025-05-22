#!/usr/bin/env python3
"""
GitLab Projects and Files Fetcher

This module provides functions for fetching projects and files from GitLab repositories
using the GitLab API with deploy token authentication.

Usage:
    from fetch_projects import fetch_group_projects, fetch_project_yaml_files
    
    # Get authentication headers
    from token_manager import get_token_from_env
    _, _, headers = get_token_from_env()
    
    # Fetch projects in a group
    projects = fetch_group_projects(gitlab_url, headers, group_id)
    
    # Fetch YAML files from a project
    yaml_files = fetch_project_yaml_files(gitlab_url, headers, project_id)
"""

import sys
import yaml
import requests
from urllib.parse import quote

def fetch_group_projects(gitlab_url, headers, group_id, exclude_project_id=None):
    """
    Fetch all projects in a GitLab group using the GitLab API.
    
    Args:
        gitlab_url (str): GitLab instance URL
        headers (dict): Authentication headers
        group_id (str): The ID of the group to fetch projects from
        exclude_project_id (str, optional): Project ID to exclude from results
        
    Returns:
        list: List of project dictionaries
    """
    api_url = f"{gitlab_url}/api/v4"
    
    # Get all projects in the group
    projects_response = requests.get(
        f"{api_url}/groups/{group_id}/projects?include_subgroups=true&per_page=100",
        headers=headers
    )
    
    if projects_response.status_code != 200:
        print(f"Error fetching projects: {projects_response.status_code}", file=sys.stderr)
        return []
    
    projects = projects_response.json()
    
    # Filter out the current project and data-validator project
    other_projects = [
        project for project in projects
        if (exclude_project_id is None or str(project['id']) != exclude_project_id) and
           not project['path_with_namespace'].endswith('data-validator')
    ]
    
    return other_projects

def fetch_project_yaml_files(gitlab_url, headers, project_id, project_path=None):
    """
    Fetch all YAML files from a GitLab project repository.
    
    Args:
        gitlab_url (str): GitLab instance URL
        headers (dict): Authentication headers
        project_id (int): The ID of the project
        project_path (str, optional): The path with namespace of the project (for error reporting)
        
    Returns:
        list: List of bookmark dictionaries extracted from YAML files
    """
    api_url = f"{gitlab_url}/api/v4"
    project_path = project_path or f"Project ID: {project_id}"
    bookmarks = []
    
    # List all files in the repository
    tree_response = requests.get(
        f"{api_url}/projects/{project_id}/repository/tree?recursive=true&per_page=100",
        headers=headers
    )
    
    if tree_response.status_code != 200:
        print(f"Error fetching files for project {project_path}: {tree_response.status_code}", file=sys.stderr)
        return []
    
    files = tree_response.json()
    yaml_files = [file for file in files if file['path'].endswith(('.yml', '.yaml'))]
    
    for yaml_file in yaml_files:
        file_path = yaml_file['path']
        
        # Skip certain files that are unlikely to contain bookmarks
        if file_path.startswith('.gitlab-ci') or '/gitlab-ci' in file_path:
            continue
        
        # Get file content
        encoded_file_path = quote(file_path, safe='')
        file_response = requests.get(
            f"{api_url}/projects/{project_id}/repository/files/{encoded_file_path}/raw?ref=main",
            headers=headers
        )
        
        if file_response.status_code != 200:
            print(f"Error fetching content for file {file_path}: {file_response.status_code}", file=sys.stderr)
            continue
        
        try:
            content = file_response.text
            yaml_content = yaml.safe_load(content)
            
            if not yaml_content or not isinstance(yaml_content, list):
                continue
            
            for item in yaml_content:
                if isinstance(item, dict) and 'url' in item:
                    # Add source info for error reporting
                    item['_source_project'] = project_path
                    item['_source_file'] = file_path
                    bookmarks.append(item)
        except yaml.YAMLError as e:
            print(f"Error parsing {project_path}/{file_path}: {str(e)}", file=sys.stderr)
    
    return bookmarks

def fetch_all_bookmarks(gitlab_url, headers, group_id, exclude_project_id=None):
    """
    Fetch all bookmark data from all projects in a group.
    
    Args:
        gitlab_url (str): GitLab instance URL
        headers (dict): Authentication headers
        group_id (str): The ID of the group to fetch projects from
        exclude_project_id (str, optional): Project ID to exclude from results
        
    Returns:
        list: List of all bookmark dictionaries from all projects
    """
    all_bookmarks = []
    
    # Get all projects in the group
    projects = fetch_group_projects(gitlab_url, headers, group_id, exclude_project_id)
    print(f"Found {len(projects)} projects in group {group_id}", file=sys.stderr)
    
    # Fetch YAML files from each project
    for project in projects:
        project_id = project['id']
        project_path = project['path_with_namespace']
        print(f"Fetching YAML files from project: {project_path}", file=sys.stderr)
        
        project_bookmarks = fetch_project_yaml_files(gitlab_url, headers, project_id, project_path)
        print(f"Found {len(project_bookmarks)} bookmarks in project {project_path}", file=sys.stderr)
        
        all_bookmarks.extend(project_bookmarks)
    
    return all_bookmarks