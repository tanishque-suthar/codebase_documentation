import requests
import re
import json
from typing import Dict, List
from pathlib import Path


def parse_github_url(url: str) -> Dict[str, str]:
    """Parse GitHub URL to extract owner, repo, and optional path"""
    # Remove trailing slash and normalize URL
    url = url.rstrip('/')
    
    # Handle different GitHub URL formats
    patterns = [
        r'https?://github\.com/([^/]+)/([^/]+)/?$',  # Basic repo URL
        r'https?://github\.com/([^/]+)/([^/]+)/tree/[^/]+/(.+)',  # Branch with path
        r'https?://github\.com/([^/]+)/([^/]+)/blob/[^/]+/(.+)',  # File URL
        r'https?://github\.com/([^/]+)/([^/]+)/tree/[^/]+/?$',  # Branch URL
    ]
    
    for pattern in patterns:
        match = re.match(pattern, url)
        if match:
            owner = match.group(1)
            repo = match.group(2)
            path = match.group(3) if len(match.groups()) > 2 else ""
            return {"owner": owner, "repo": repo, "path": path}
    
    raise ValueError("Invalid GitHub URL format")


def get_github_contents(owner: str, repo: str, path: str = "") -> List[Dict]:
    """Fetch repository contents using GitHub API"""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    
    try:
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            contents = response.json()
            # If it's a single file, wrap in list
            if isinstance(contents, dict):
                return [contents]
            return contents
        elif response.status_code == 404:
            raise ValueError("Repository or path not found")
        elif response.status_code == 403:
            raise ValueError("API rate limit exceeded or repository is private")
        else:
            raise ValueError(f"GitHub API error: {response.status_code}")
    except requests.RequestException as e:
        raise ValueError(f"Failed to connect to GitHub: {str(e)}")


def get_file_content(download_url: str) -> str:
    """Download and decode file content from GitHub"""
    try:
        response = requests.get(download_url, timeout=30)
        if response.status_code == 200:
            return response.text
        else:
            raise ValueError(f"Failed to download file: {response.status_code}")
    except requests.RequestException as e:
        raise ValueError(f"Failed to download file: {str(e)}")


def get_all_files_recursively(owner: str, repo: str, path: str = "", current_depth: int = 0, max_depth: int = 8) -> List[Dict]:
    """
    Recursively collect all files and directories for AI prioritization
    """
    if current_depth >= max_depth:
        return []
    
    all_items = []
    try:
        contents = get_github_contents(owner, repo, path)
        
        for item in contents:
            # Add current item to list
            all_items.append({
                'name': item['name'],
                'path': item['path'],
                'type': item['type'],
                'size': item.get('size', 0),
                'depth': current_depth
            })
            
            # If it's a directory, recursively explore it
            if item['type'] == 'dir':
                # Skip known non-code directories to save API calls
                skip_dirs = {
                    '.git', '.github', 'node_modules', '__pycache__', '.vscode', 
                    'dist', 'build', 'target', 'out', '.idea', 'logs', 'tmp', 
                    '.next', '.nuxt', 'coverage', '.pytest_cache', 'vendor'
                }
                
                if item['name'].lower() not in skip_dirs:
                    sub_items = get_all_files_recursively(
                        owner, repo, item['path'], 
                        current_depth + 1, max_depth
                    )
                    all_items.extend(sub_items)
        
        return all_items
    except Exception as e:
        print(f"Error exploring {path} at depth {current_depth}: {e}")
        return []
