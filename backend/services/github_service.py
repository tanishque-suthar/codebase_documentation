import requests
import re
import json
import time
import os
import hashlib
from typing import Dict, List, Optional
from pathlib import Path
from functools import lru_cache
from datetime import datetime, timedelta

# AI-Priority File Content Caching System
FILE_CONTENT_CACHE = {}
CACHE_CONFIG = {
    'max_cached_files': int(os.getenv('CACHE_MAX_FILES', '20')),  # Cache top 20 files
    'cache_ttl_hours': int(os.getenv('CACHE_TTL_HOURS', '24')),   # 24 hour TTL
    'min_ai_score': int(os.getenv('CACHE_MIN_AI_SCORE', '3')),    # Only cache files with AI score >= 3
    'enabled': os.getenv('FILE_CACHE_ENABLED', 'true').lower() == 'true'
}


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


def check_rate_limit_headers(response):
    """Check GitHub rate limit headers and return rate limit info"""
    rate_limit_info = {
        'limit': int(response.headers.get('X-RateLimit-Limit', 0)),
        'remaining': int(response.headers.get('X-RateLimit-Remaining', 0)),
        'reset': int(response.headers.get('X-RateLimit-Reset', 0)),
        'used': int(response.headers.get('X-RateLimit-Used', 0))
    }
    return rate_limit_info


def handle_github_response(response: requests.Response, context: str = ""):
    """Centralized error handling for GitHub API responses"""
    if response.status_code == 200:
        return response
    elif response.status_code == 404:
        raise ValueError(f"Repository or path not found{f' ({context})' if context else ''}")
    elif response.status_code == 403:
        error_text = response.text.lower()
        if 'rate limit' in error_text:
            raise ValueError(f"GitHub API rate limit exceeded. Please try again later.{f' ({context})' if context else ''}")
        else:
            raise ValueError(f"Repository is private or access denied{f' ({context})' if context else ''}")
    elif response.status_code == 429:
        raise ValueError(f"GitHub API rate limit exceeded. Please try again later.{f' ({context})' if context else ''}")
    else:
        raise ValueError(f"GitHub API error: {response.status_code}{f' ({context})' if context else ''}")


def handle_rate_limit_error(response):
    """Handle rate limit exceeded responses"""
    if response.status_code in [403, 429]:
        # Check if it's actually a rate limit error
        error_message = response.text.lower()
        if 'rate limit' in error_message or 'exceeded' in error_message:
            reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
            current_time = int(time.time())
            wait_seconds = max(0, reset_time - current_time)
            
            if wait_seconds > 0:
                print(f"GitHub API rate limit exceeded. Rate limit resets in {wait_seconds} seconds.")
                print(f"Waiting {wait_seconds + 1} seconds before retrying...")
                time.sleep(wait_seconds + 1)
                return True  # Indicates we should retry
            else:
                print("Rate limit exceeded but reset time has passed. Retrying immediately...")
                return True
    return False  # Not a rate limit error or shouldn't retry


def make_github_request(url: str, headers: dict = None) -> requests.Response:
    """Make a GitHub API request with rate limit handling"""
    if headers is None:
        headers = {}
    
    # Add GitHub token if available for higher rate limits
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token and "Authorization" not in headers:
        headers["Authorization"] = f"token {github_token}"
    
    try:
        response = requests.get(url, timeout=30, headers=headers)
        
        # Log rate limit info for monitoring
        rate_info = check_rate_limit_headers(response)
        print(f"GitHub API - Remaining: {rate_info['remaining']}/{rate_info['limit']}")
        if rate_info['remaining'] < 10:
            print(f"⚠️  Warning: Only {rate_info['remaining']} GitHub API requests remaining")
        
        # Handle rate limit errors
        if response.status_code in [403, 429]:
            if handle_rate_limit_error(response):
                # Retry once after waiting
                print("Retrying GitHub API request...")
                response = requests.get(url, timeout=30, headers=headers)
        
        return response
        
    except requests.RequestException as e:
        raise ValueError(f"Failed to connect to GitHub: {str(e)}")


def is_likely_code_file(filename: str) -> bool:
    """Check if a file is likely to contain code based on its extension"""
    code_extensions = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.cs', '.php',
        '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.m', '.h', '.hpp',
        '.css', '.scss', '.sass', '.less', '.html', '.htm', '.xml', '.json',
        '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.md', '.rst',
        '.txt', '.sql', '.sh', '.bat', '.ps1', '.dockerfile', '.makefile'
    }
    
    filename_lower = filename.lower()
    file_ext = '.' + filename_lower.split('.')[-1] if '.' in filename_lower else ''
    
    # Check common filenames without extensions
    common_files = {'readme', 'license', 'changelog', 'makefile', 'dockerfile'}
    if filename_lower in common_files:
        return True
    
    return file_ext in code_extensions


def should_skip_directory(dir_name: str) -> bool:
    """Determine if a directory should be skipped to save API calls"""
    skip_dirs = {
        '.git', '.github', 'node_modules', '__pycache__', '.vscode', 
        'dist', 'build', 'target', 'out', '.idea', 'logs', 'tmp', 
        '.next', '.nuxt', 'coverage', '.pytest_cache', 'vendor',
        'bower_components', '.sass-cache', '.cache', 'public/assets',
        'static/assets', 'assets/vendor', 'third_party', 'external',
        '.terraform', '.vagrant', 'venv', 'env', '.env'
    }
    return dir_name.lower() in skip_dirs


@lru_cache(maxsize=100)
def get_repo_languages(owner: str, repo: str) -> Dict[str, int]:
    """Get repository languages to prioritize file types (cached)"""
    url = f"https://api.github.com/repos/{owner}/{repo}/languages"
    try:
        response = make_github_request(url)
        response = handle_github_response(response, context="get_repo_languages")
        return response.json()
    except Exception as e:
        print(f"Could not fetch repo languages: {e}")
    return {}


def prioritize_files_by_language(files: List[Dict], repo_languages: Dict[str, int]) -> List[Dict]:
    """Prioritize files based on repository's primary languages"""
    if not repo_languages:
        return files
    
    # Get primary languages (top 3)
    primary_langs = list(repo_languages.keys())[:3]
    
    # Language to file extension mapping
    lang_extensions = {
        'Python': ['.py'],
        'JavaScript': ['.js', '.jsx'],
        'TypeScript': ['.ts', '.tsx'],
        'Java': ['.java'],
        'C++': ['.cpp', '.cc', '.cxx'],
        'C': ['.c'],
        'C#': ['.cs'],
        'PHP': ['.php'],
        'Ruby': ['.rb'],
        'Go': ['.go'],
        'Rust': ['.rs'],
        'Swift': ['.swift'],
        'Kotlin': ['.kt']
    }
    
    def get_priority(file_item):
        filename = file_item['name'].lower()
        file_ext = '.' + filename.split('.')[-1] if '.' in filename else ''
        
        # Highest priority for primary language files
        for i, lang in enumerate(primary_langs):
            if lang in lang_extensions:
                if file_ext in lang_extensions[lang]:
                    return i  # 0 = highest priority
        
        # Medium priority for other code files
        if is_likely_code_file(filename):
            return 10
        
        # Lower priority for other files
        return 20
    
    return sorted(files, key=get_priority)


def get_github_contents(owner: str, repo: str, path: str = "") -> List[Dict]:
    """Fetch repository contents using GitHub API"""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    
    try:
        response = make_github_request(url)
        response = handle_github_response(response, context=f"get_github_contents: {path}")
        contents = response.json()
        # If it's a single file, wrap in list
        if isinstance(contents, dict):
            return [contents]
        return contents
    except Exception as e:
        raise ValueError(f"Failed to get GitHub contents: {e}")


def get_file_content(download_url: str) -> str:
    """Download and decode file content from GitHub with rate limit handling"""
    response = make_github_request(download_url)
    response = handle_github_response(response, context="get_file_content")
    return response.text


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
                if not should_skip_directory(item['name']):
                    sub_items = get_all_files_recursively(
                        owner, repo, item['path'], 
                        current_depth + 1, max_depth
                    )
                    all_items.extend(sub_items)
        
        return all_items
    except Exception as e:
        print(f"Error exploring {path} at depth {current_depth}: {e}")
        return []


def get_optimized_file_list(owner: str, repo: str, max_files: int = 100) -> List[Dict]:
    """
    Get a smart, limited list of files optimized for documentation generation
    This reduces API calls significantly by using the tree API first
    """
    print(f"🚀 Fetching optimized file list for {owner}/{repo} (max {max_files} files)")
    
    # Try the efficient tree API first (only 1-2 API calls)
    tree_files = get_repository_tree(owner, repo, max_files)
    if tree_files:
        return tree_files
    
    # Fallback to the old method if tree API fails
    print("🔄 Tree API failed, using fallback method...")
    
    # Get repo languages first to understand the project
    repo_languages = get_repo_languages(owner, repo)
    print(f"📊 Repository languages: {list(repo_languages.keys())[:3]}")
    
    # Start with root directory
    all_files = []
    try:
        root_contents = get_github_contents(owner, repo, "")
        
        # Prioritize important root files
        important_root_files = ['readme.md', 'readme.txt', 'readme', 'package.json', 
                               'requirements.txt', 'setup.py', 'makefile', 'dockerfile',
                               'cargo.toml', 'go.mod', 'pom.xml', 'build.gradle']
        
        # Add important root files first
        for item in root_contents:
            if item['type'] == 'file' and item['name'].lower() in important_root_files:
                all_files.append({
                    'name': item['name'],
                    'path': item['path'],
                    'type': item['type'],
                    'size': item.get('size', 0),
                    'priority': 'high'
                })
        
        # Add source directories (limit depth to save API calls)
        source_dirs = ['src', 'lib', 'app', 'components', 'modules', 'services', 'utils']
        for item in root_contents:
            if (item['type'] == 'dir' and 
                item['name'].lower() in source_dirs and 
                not should_skip_directory(item['name'])):
                
                # Get files from source directories (limit to 2 levels deep)
                dir_files = get_all_files_recursively(
                    owner, repo, item['path'], 
                    current_depth=0, max_depth=2
                )
                
                # Filter to only code files and limit count
                code_files = [f for f in dir_files if f['type'] == 'file' and is_likely_code_file(f['name'])]
                all_files.extend(code_files[:20])  # Limit per directory
                
                if len(all_files) >= max_files:
                    break
        
        # If we still need more files, add some from root level
        if len(all_files) < max_files:
            root_files = [item for item in root_contents if item['type'] == 'file']
            if repo_languages:
                root_files = prioritize_files_by_language(root_files, repo_languages)
            
            for file in root_files:
                if is_likely_code_file(file['name']) and len(all_files) < max_files:
                    all_files.append({
                        'name': file['name'],
                        'path': file['path'],
                        'type': file['type'],
                        'size': file.get('size', 0),
                        'priority': 'medium'
                    })
        
        print(f"✅ Retrieved {len(all_files)} files using fallback strategy")
        return all_files[:max_files]
        
    except Exception as e:
        print(f"❌ Error in fallback file fetching: {e}")
        # Final fallback to basic recursive method
        return get_all_files_recursively(owner, repo, max_depth=3)[:max_files]


def get_repository_tree(owner: str, repo: str, max_files: int = 100) -> List[Dict]:
    """
    Get repository file tree using GitHub's tree API - much more efficient than recursive calls
    This uses a single API call to get the entire repository structure
    """
    print(f"🌳 Fetching repository tree for {owner}/{repo} using tree API")
    
    try:
        # First get the default branch
        repo_url = f"https://api.github.com/repos/{owner}/{repo}"
        repo_response = make_github_request(repo_url)
        repo_response = handle_github_response(repo_response, context="get_repository_info")
        repo_data = repo_response.json()
        default_branch = repo_data.get('default_branch', 'main')
        
        # Get the tree for the default branch (recursive=1 gets all files in one call)
        tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
        tree_response = make_github_request(tree_url)
        tree_response = handle_github_response(tree_response, context="get_repository_tree")
        tree_data = tree_response.json()
        
        if 'tree' not in tree_data:
            print("⚠️ Tree API response missing 'tree' field, falling back to contents API")
            return []
        
        # Process the tree data
        all_files = []
        for item in tree_data['tree']:
            # Skip directories and focus on files
            if item['type'] == 'blob':  # blob = file in git terminology
                file_path = item['path']
                file_name = file_path.split('/')[-1]
                
                # Apply filtering logic
                if not is_likely_code_file(file_name):
                    continue
                    
                # Skip files in directories we want to avoid
                if any(should_skip_directory(part) for part in file_path.split('/')):
                    continue
                
                all_files.append({
                    'name': file_name,
                    'path': file_path,
                    'type': 'file',
                    'size': item.get('size', 0),
                    'sha': item['sha'],
                    'url': item['url']
                })
        
        # Get repository languages for prioritization
        repo_languages = get_repo_languages(owner, repo)
        if repo_languages:
            all_files = prioritize_files_by_language(all_files, repo_languages)
        
        # Prioritize important files (README, config files, etc.)
        important_files = []
        other_files = []
        
        important_patterns = [
            'readme', 'package.json', 'requirements.txt', 'setup.py', 
            'makefile', 'dockerfile', 'cargo.toml', 'go.mod', 'pom.xml', 
            'build.gradle', 'tsconfig.json', 'webpack.config', 'vite.config'
        ]
        
        for file_item in all_files:
            file_name_lower = file_item['name'].lower()
            file_path_lower = file_item['path'].lower()
            
            is_important = (
                any(pattern in file_name_lower for pattern in important_patterns) or
                file_path_lower.count('/') <= 1  # Prefer root or near-root files
            )
            
            if is_important:
                important_files.append(file_item)
            else:
                other_files.append(file_item)
        
        # Combine important files first, then others
        result = important_files + other_files
        result = result[:max_files]
        
        print(f"✅ Retrieved {len(result)} files using tree API (1-2 API calls total)")
        return result
        
    except Exception as e:
        print(f"❌ Tree API failed: {e}")
        print("🔄 Falling back to contents API...")
        return []


def get_multiple_file_contents(file_items: List[Dict], max_concurrent: int = 5) -> Dict[str, str]:
    """
    Efficiently fetch multiple file contents with limited concurrency
    Returns a dict mapping file paths to their content
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    file_contents = {}
    errors = {}
    
    def fetch_single_file(file_item: Dict) -> tuple:
        """Fetch a single file's content"""
        try:
            if 'download_url' in file_item:
                content = get_file_content(file_item['download_url'])
                return file_item['path'], content, None
            else:
                # If no download_url, try to get content via API
                owner, repo = file_item.get('owner'), file_item.get('repo')
                if owner and repo:
                    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_item['path']}"
                    response = make_github_request(url)
                    response = handle_github_response(response, context=f"fetch_file: {file_item['path']}")
                    file_data = response.json()
                    
                    if file_data.get('encoding') == 'base64':
                        import base64
                        content = base64.b64decode(file_data['content']).decode('utf-8')
                        return file_item['path'], content, None
                    else:
                        return file_item['path'], file_data.get('content', ''), None
                else:
                    return file_item['path'], '', f"Missing owner/repo info for {file_item['path']}"
        except Exception as e:
            return file_item['path'], '', str(e)
    
    # Limit concurrent requests to avoid overwhelming the API
    with ThreadPoolExecutor(max_workers=min(max_concurrent, len(file_items))) as executor:
        # Submit all tasks
        future_to_file = {executor.submit(fetch_single_file, file_item): file_item 
                         for file_item in file_items}
        
        # Process completed requests
        for future in as_completed(future_to_file):
            file_path, content, error = future.result()
            if error:
                errors[file_path] = error
                print(f"❌ Error fetching {file_path}: {error}")
            else:
                file_contents[file_path] = content
                print(f"✅ Fetched {file_path} ({len(content)} chars)")
    
    if errors:
        print(f"⚠️ Failed to fetch {len(errors)} files")
    
    return file_contents


def get_file_content_by_sha(owner: str, repo: str, sha: str) -> str:
    """
    Get file content directly by SHA (more efficient for tree API results)
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/git/blobs/{sha}"
    response = make_github_request(url)
    response = handle_github_response(response, context=f"get_file_by_sha: {sha}")
    blob_data = response.json()
    
    if blob_data.get('encoding') == 'base64':
        import base64
        return base64.b64decode(blob_data['content']).decode('utf-8')
    else:
        return blob_data.get('content', '')


def get_repository_info_batch(owner: str, repo: str) -> Dict:
    """
    Get multiple repository details in a single API call to reduce overhead
    """
    url = f"https://api.github.com/repos/{owner}/{repo}"
    
    try:
        response = make_github_request(url)
        response = handle_github_response(response, context="get_repository_info_batch")
        repo_data = response.json()
        
        # Extract useful info for optimization decisions
        return {
            'name': repo_data.get('name', ''),
            'full_name': repo_data.get('full_name', ''),
            'default_branch': repo_data.get('default_branch', 'main'),
            'size': repo_data.get('size', 0),  # Repository size in KB
            'language': repo_data.get('language', ''),
            'archived': repo_data.get('archived', False),
            'private': repo_data.get('private', False),
            'fork': repo_data.get('fork', False),
            'created_at': repo_data.get('created_at', ''),
            'updated_at': repo_data.get('updated_at', ''),
            'pushed_at': repo_data.get('pushed_at', ''),
            'stargazers_count': repo_data.get('stargazers_count', 0),
            'topics': repo_data.get('topics', [])
        }
    except Exception as e:
        print(f"❌ Failed to get repository info: {e}")
        return {'default_branch': 'main'}


def batch_api_requests(urls: List[str], headers: dict = None) -> List[Dict]:
    """
    Make multiple API requests efficiently with rate limiting awareness
    """
    if not urls:
        return []
    
    results = []
    failed_requests = []
    
    # Process in smaller batches to avoid rate limiting
    batch_size = 3  # Conservative batch size
    
    for i in range(0, len(urls), batch_size):
        batch_urls = urls[i:i + batch_size]
        
        for url in batch_urls:
            try:
                response = make_github_request(url, headers)
                response = handle_github_response(response, context=f"batch_request: {url}")
                results.append({
                    'url': url,
                    'status_code': response.status_code,
                    'data': response.json()
                })
            except Exception as e:
                failed_requests.append({'url': url, 'error': str(e)})
        
        # Small delay between batches to be respectful to API
        if i + batch_size < len(urls):
            time.sleep(0.1)
    
    if failed_requests:
        print(f"⚠️ {len(failed_requests)} requests failed in batch operation")
    
    return results

# TODO: Implement file content caching utilities here

def get_cache_key_for_file(owner: str, repo: str, file_path: str, last_modified: str = None) -> str:
    """Generate a unique cache key for a file"""
    # Include last_modified or file hash to invalidate cache when file changes
    key_parts = [owner, repo, file_path]
    if last_modified:
        key_parts.append(last_modified)
    
    cache_string = "_".join(key_parts)
    return hashlib.md5(cache_string.encode()).hexdigest()

def is_file_cache_valid(cache_entry: Dict) -> bool:
    """Check if cached file content is still valid"""
    if not cache_entry:
        return False
    
    cache_time = cache_entry.get('cached_at')
    if not cache_time:
        return False
    
    # Check if cache has expired
    expiry_time = cache_time + timedelta(hours=CACHE_CONFIG['cache_ttl_hours'])
    return datetime.now() < expiry_time

def cache_file_content(cache_key: str, content: str, ai_score: int, file_path: str):
    """Cache file content if it meets the criteria"""
    if not CACHE_CONFIG['enabled']:
        return
    
    # Only cache high-priority files
    if ai_score < CACHE_CONFIG['min_ai_score']:
        print(f"⏭️  Skipping cache for {file_path} (AI score {ai_score} < {CACHE_CONFIG['min_ai_score']})")
        return
    
    # Check cache size limit
    if len(FILE_CONTENT_CACHE) >= CACHE_CONFIG['max_cached_files']:
        # Remove least recently used entry
        cleanup_file_cache()
    
    FILE_CONTENT_CACHE[cache_key] = {
        'content': content,
        'cached_at': datetime.now(),
        'ai_score': ai_score,
        'file_path': file_path,
        'content_size': len(content),
        'access_count': 1,
        'last_accessed': datetime.now()
    }
    
    print(f"💾 Cached file content: {file_path} (AI score: {ai_score}, size: {len(content)} chars)")

def get_cached_file_content(cache_key: str) -> Optional[str]:
    """Retrieve cached file content if valid"""
    if not CACHE_CONFIG['enabled']:
        return None
    
    cache_entry = FILE_CONTENT_CACHE.get(cache_key)
    if not cache_entry:
        return None
    
    if not is_file_cache_valid(cache_entry):
        # Remove expired entry
        del FILE_CONTENT_CACHE[cache_key]
        print(f"🗑️  Removed expired cache entry: {cache_entry['file_path']}")
        return None
    
    # Update access tracking
    cache_entry['access_count'] += 1
    cache_entry['last_accessed'] = datetime.now()
    
    print(f"✅ Cache hit: {cache_entry['file_path']} (accessed {cache_entry['access_count']} times)")
    return cache_entry['content']

def cleanup_file_cache():
    """Remove old or low-priority cached files to make room"""
    if len(FILE_CONTENT_CACHE) < CACHE_CONFIG['max_cached_files']:
        return
    
    # Sort by priority: access_count desc, then ai_score desc, then last_accessed desc
    cache_items = list(FILE_CONTENT_CACHE.items())
    cache_items.sort(key=lambda x: (
        x[1]['access_count'],
        x[1]['ai_score'], 
        x[1]['last_accessed']
    ))
    
    # Remove the least valuable entries (first 25% or at least 1)
    remove_count = max(1, len(cache_items) // 4)
    
    for i in range(remove_count):
        cache_key, cache_entry = cache_items[i]
        removed_file = cache_entry['file_path']
        del FILE_CONTENT_CACHE[cache_key]
        print(f"🧹 Removed low-priority cache: {removed_file} (score: {cache_entry['ai_score']}, access: {cache_entry['access_count']})")

def get_file_content_with_cache(owner: str, repo: str, file_path: str, ai_score: int = 0, download_url: str = None, sha: str = None) -> str:
    """Get file content with smart caching for high-priority files"""
    
    # Generate cache key
    cache_key = get_cache_key_for_file(owner, repo, file_path)
    
    # Try cache first
    cached_content = get_cached_file_content(cache_key)
    if cached_content is not None:
        return cached_content
    
    # Cache miss - fetch from GitHub
    try:
        if download_url:
            content = get_file_content(download_url)
        elif sha:
            content = get_file_content_by_sha(owner, repo, sha)
        else:
            # Fallback to contents API
            url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
            response = make_github_request(url)
            response = handle_github_response(response, context=f"get_file_content: {file_path}")
            file_data = response.json()
            
            if file_data.get('encoding') == 'base64':
                import base64
                content = base64.b64decode(file_data['content']).decode('utf-8')
            else:
                content = file_data.get('content', '')
        
        # Cache the content if it's high priority
        cache_file_content(cache_key, content, ai_score, file_path)
        
        return content
        
    except Exception as e:
        print(f"❌ Failed to fetch content for {file_path}: {e}")
        return ""

def get_multiple_files_with_cache(file_items: List[Dict], ai_scores: Dict[str, int] = None) -> Dict[str, str]:
    """
    Efficiently fetch multiple file contents with AI-priority caching
    """
    if ai_scores is None:
        ai_scores = {}
    
    file_contents = {}
    cache_hits = 0
    api_calls = 0
    
    print(f"📥 Fetching {len(file_items)} files with AI-priority caching...")
    
    for file_item in file_items:
        file_path = file_item['path']
        ai_score = ai_scores.get(file_path, 0)
        
        try:
            # Check if we already have cached content before making any calls
            cache_key = get_cache_key_for_file(
                file_item.get('owner', ''),
                file_item.get('repo', ''),
                file_path
            )
            
            cached_content = get_cached_file_content(cache_key)
            if cached_content is not None:
                file_contents[file_path] = cached_content
                cache_hits += 1
                continue
            
            content = get_file_content_with_cache(
                owner=file_item.get('owner', ''),
                repo=file_item.get('repo', ''),
                file_path=file_path,
                ai_score=ai_score,
                download_url=file_item.get('download_url'),
                sha=file_item.get('sha')
            )
            
            file_contents[file_path] = content
            api_calls += 1
                
        except Exception as e:
            print(f"❌ Error fetching {file_path}: {e}")
            file_contents[file_path] = ""
    
    print(f"📊 Cache performance: {cache_hits} hits, {api_calls} API calls")
    return file_contents

def warm_cache_for_priority_files(owner: str, repo: str, priority_files: List[Dict], ai_scores: Dict[str, int]):
    """
    Pre-warm cache with high-priority files
    """
    if not CACHE_CONFIG['enabled']:
        return
    
    high_priority_files = [
        file_item for file_item in priority_files 
        if ai_scores.get(file_item['path'], 0) >= CACHE_CONFIG['min_ai_score']
    ]
    
    # Limit to cache size
    high_priority_files = high_priority_files[:CACHE_CONFIG['max_cached_files']]
    
    print(f"🔥 Warming cache with {len(high_priority_files)} high-priority files...")
    
    # Add owner/repo info to file items
    for file_item in high_priority_files:
        file_item['owner'] = owner
        file_item['repo'] = repo
    
    get_multiple_files_with_cache(high_priority_files, ai_scores)

def get_cache_statistics() -> Dict[str, any]:
    """Get detailed cache statistics"""
    if not FILE_CONTENT_CACHE:
        return {'status': 'empty', 'enabled': CACHE_CONFIG['enabled']}
    
    total_size = sum(entry['content_size'] for entry in FILE_CONTENT_CACHE.values())
    total_accesses = sum(entry['access_count'] for entry in FILE_CONTENT_CACHE.values())
    
    # Calculate average AI scores of cached files
    ai_scores = [entry['ai_score'] for entry in FILE_CONTENT_CACHE.values()]
    avg_ai_score = sum(ai_scores) / len(ai_scores) if ai_scores else 0
    
    # Find most accessed files
    most_accessed = sorted(
        FILE_CONTENT_CACHE.values(), 
        key=lambda x: x['access_count'], 
        reverse=True
    )[:5]
    
    return {
        'enabled': CACHE_CONFIG['enabled'],
        'total_files_cached': len(FILE_CONTENT_CACHE),
        'total_content_size': f"{total_size:,} characters",
        'total_cache_accesses': total_accesses,
        'average_ai_score': round(avg_ai_score, 2),
        'cache_hit_efficiency': f"{(total_accesses / len(FILE_CONTENT_CACHE)):.1f} avg accesses per file" if FILE_CONTENT_CACHE else "0",
        'most_accessed_files': [
            f"{item['file_path']} (score: {item['ai_score']}, accesses: {item['access_count']})"
            for item in most_accessed
        ],
        'config': CACHE_CONFIG
    }

def clear_file_content_cache():
    """Clear all cached file content"""
    global FILE_CONTENT_CACHE
    cache_count = len(FILE_CONTENT_CACHE)
    FILE_CONTENT_CACHE.clear()
    print(f"🧹 Cleared {cache_count} cached files")


def get_api_optimization_summary() -> Dict[str, str]:
    """
    Get a summary of API optimization features available in this service
    """
    return {
        'ai_priority_caching': 'Smart file content caching based on AI priority scores',
        'tree_api': 'Uses GitHub tree API to fetch entire repo structure in 1-2 calls',
        'batching': 'Batch API requests with concurrency control',
        'rate_limiting': 'Automatic rate limit detection and backoff',
        'file_filtering': 'Smart filtering to skip non-code files and directories',
        'prioritization': 'Language-aware file prioritization',
        'fallback_strategy': 'Multiple fallback approaches for resilience',
        'concurrent_fetching': 'Parallel file content fetching with rate limiting'
    }


# Main optimization function for external use
def fetch_repository_efficiently(owner: str, repo: str, max_files: int = 100) -> Dict[str, any]:
    """
    Main entry point for efficiently fetching repository data
    Returns both file list and repository metadata in optimized way
    """
    print(f"🚀 Starting efficient repository fetch for {owner}/{repo}")
    
    # Get repository info and file list in optimized manner
    repo_info = get_repository_info_batch(owner, repo)
    file_list = get_optimized_file_list(owner, repo, max_files)
    
    optimization_summary = get_api_optimization_summary()
    
    result = {
        'repository': repo_info,
        'files': file_list,
        'optimization_features': optimization_summary,
        'total_files_found': len(file_list)
    }
    
    print(f"✅ Efficiently fetched data for {owner}/{repo} - {len(file_list)} files")
    
    return result

def fetch_repository_with_smart_caching(owner: str, repo: str, max_files: int = 100, ai_scores: Dict[str, int] = None) -> Dict[str, any]:
    """
    Enhanced repository fetch with AI-priority file content caching
    """
    print(f"🚀 Starting repository fetch with smart caching for {owner}/{repo}")
    
    # Get repository info and file list
    repo_info = get_repository_info_batch(owner, repo)
    file_list = get_optimized_file_list(owner, repo, max_files)
    
    # Add owner/repo to file items for caching
    for file_item in file_list:
        file_item['owner'] = owner
        file_item['repo'] = repo
    
    # If AI scores provided, warm cache with high-priority files
    if ai_scores and CACHE_CONFIG['enabled']:
        warm_cache_for_priority_files(owner, repo, file_list, ai_scores)
    
    # Get file contents with caching
    file_contents = get_multiple_files_with_cache(file_list, ai_scores or {})
    
    # Get cache statistics
    cache_stats = get_cache_statistics()
    
    result = {
        'repository': repo_info,
        'files': file_list,
        'file_contents': file_contents,
        'cache_statistics': cache_stats,
        'total_files_found': len(file_list),
        'optimization_features': get_api_optimization_summary()
    }
    
    print(f"✅ Repository fetch complete - {len(file_list)} files, {len(file_contents)} with content")
    
    return result
