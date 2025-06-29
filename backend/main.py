from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
import uvicorn
import base64
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel
from typing import Optional, List, Dict
from google import genai
from google.genai import types
import os
from tempfile import NamedTemporaryFile
from datetime import datetime
from dotenv import load_dotenv
from middleware import setup_cors_middleware
import requests
import re
import json
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Document AI App", 
              description="API for processing documents with AI",
              version="0.1.0",
              docs_url="/api-docs")

# Apply CORS middleware
app = setup_cors_middleware(app)

# Initialize Google AI client
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable is not set.")
    
client = genai.Client(api_key=api_key)

# Define request model
class CodeDocumentationRequest(BaseModel):
    code: str
    isBase64: bool = False  # Flag to indicate if code is base64 encoded
    
    class Config:
        schema_extra = {
            "example": {
                "code": "def hello_world():\n    print('Hello, world!')",
                "isBase64": False
            }
        }

# Define response model
class DocumentationResponse(BaseModel):
    markdown: str

# Define GitHub request model
class GitHubDocumentationRequest(BaseModel):
    github_url: str
    max_files: int = 10  # Limit files processed for MVP
    
    class Config:
        schema_extra = {
            "example": {
                "github_url": "https://github.com/owner/repository",
                "max_files": 10
            }
        }

# GitHub helper functions
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

@app.get("/")
async def root():
    return {
        "message": "Welcome to Code Documentation API",
        "usage": {
            "text_input": {
                "endpoint": "/docs/gen",
                "method": "POST",
                "body": {
                    "code": "Your code here (any programming language)",
                    "isBase64": "Optional boolean (default: false) to indicate if the code is base64 encoded"
                }
            },
            "file_upload": {
                "endpoint": "/docs/from-upload",
                "method": "POST",
                "form": "file: Upload a text file containing code"
            },
            "github_repo": {
                "endpoint": "/docs/from-github",
                "method": "POST",
                "body": {
                    "github_url": "GitHub repository URL",
                    "max_files": "Optional number (default: 10) to limit files processed"
                }
            },
            "download": {
                "endpoint": "/docs/download",
                "method": "POST",
                "options": "Can accept either a request body with code OR a file upload"
            },
            "github_download": {
                "endpoint": "/docs/download-github",
                "method": "POST",
                "body": {
                    "github_url": "GitHub repository URL",
                    "max_files": "Optional number (default: 10) to limit files processed"
                },
                "description": "Download documentation for GitHub repository as .md file"
            }
        },
        "example": {
            "code": "def hello_world():\n    print('Hello, world!')",
            "isBase64": False
        }
    }

@app.post("/docs/gen", response_model=DocumentationResponse)
async def generate_documentation(request: CodeDocumentationRequest):
    try:
        if not request.code:
            raise HTTPException(status_code=400, detail="Code cannot be empty")
        
        # Decode base64 if the flag is set
        try:
            if request.isBase64:
                code = base64.b64decode(request.code).decode('utf-8')
            else:
                code = request.code
        except Exception as decode_error:
            raise HTTPException(status_code=400, detail=f"Error decoding base64: {str(decode_error)}")
        print(f"Decoded code:\n{code}\n")     
        # Create a prompt for documentation generation with consistent formatting
        prompt = f"""
Generate concise brief documentation for the following code:\n\n
{code}\n
Generate documentation with the following sections:
# 1. PROJECT OVERVIEW
- main purpose
- Key features and working
- Main user workflows(if applicable)\n
# 2. API REFERENCE (if applicable)
- Available endpoints and their purpose along with function signatures
- Request/response formats
# 3. FUNCTIONS
- List all non-API functions with their purpose and parameters.\n
Format the documentation as clear, well-structured Markdown.
Output in a code block.
        """
        #print(f"Generated prompt for AI:\n{prompt}\n")
        
        # Generation configuration
        gen_config = types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=1024
        )
        
        # Generate documentation with AI
        try:
            response = client.models.generate_content(
                model="gemma-3-12b-it",
                contents=prompt,
                config=gen_config
            )
            ai_content = response.text.strip()

            # Remove markdown code blocks if present
            if ai_content.startswith('```markdown'):
                ai_content = ai_content[11:].strip()
                if ai_content.endswith('```'):
                    ai_content = ai_content[:-3].strip()
            elif ai_content.startswith('```'):
                ai_content = ai_content[3:].strip()
                if ai_content.endswith('```'):
                    ai_content = ai_content[:-3].strip()

            return DocumentationResponse(
                markdown=ai_content
            )
        except Exception as api_error:
            raise HTTPException(
                status_code=500, 
                detail=f"Error generating documentation: {str(api_error)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# Adding file upload endpoint for documentation generation
@app.post("/docs/from-upload", response_model=DocumentationResponse)
async def generate_docs_from_upload(file: UploadFile = File(...)):
    try:
        # Read contents of the uploaded file
        file_content = await file.read()
        
        # Try to decode as text first to verify it's a valid text file
        try:
            # Just to verify it's readable text
            file_content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File could not be decoded as text. Please upload a text file containing code.")
        
        # Encode the file content as base64
        base64_code = base64.b64encode(file_content).decode('utf-8')
        
        # Create a request object with base64 encoded content
        request = CodeDocumentationRequest(code=base64_code, isBase64=True)
        
        # Use the existing documentation generation endpoint
        return await generate_documentation(request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


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

def get_ai_file_priorities(file_list: List[Dict], repo_info: Dict) -> Dict:
    """
    Use AI to rank file importance and suggest exploration strategy
    """
    # Format file list for AI analysis
    file_summary = []
    for item in file_list:
        file_summary.append({
            'name': item['name'],
            'path': item['path'],
            'type': item['type'],
            'size': item.get('size', 0),
            'depth': item.get('depth', 0)
        })
    
    prompt = f"""
Repository: {repo_info['owner']}/{repo_info['repo']}

Analyze this repository structure and rank files by documentation importance:

Files and directories found:
{json.dumps(file_summary, indent=2)}

Rank each FILE (not directories) on importance for documentation (1-5 scale):
5 = Core business logic (main APIs, key components, entry points)
4 = Important supporting code (utilities, services, components)
3 = Secondary code (helpers, configs with logic)
2 = Tests, examples, demos
1 = Build configs, package files (skip these)

Also suggest exploration strategy.

Return ONLY valid JSON in this exact format:
{{
    "rankings": {{
        "filename.ext": 5,
        "another-file.js": 4
    }},
    "strategy": {{
        "max_depth_recommended": 4,
        "focus_extensions": [".py", ".js", ".jsx"],
        "project_type": "web_app"
    }}
}}
"""
    
    try:
        gen_config = types.GenerateContentConfig(
            temperature=0.2,  # Low temperature for consistent JSON
            max_output_tokens=1024
        )
        
        response = client.models.generate_content(
            model="gemma-3-12b-it",
            contents=prompt,
            config=gen_config
        )
        
        # Parse AI response
        response_text = response.text.strip()
        
        # Extract JSON from response (handle markdown code blocks)
        if '```json' in response_text:
            json_start = response_text.find('```json') + 7
            json_end = response_text.find('```', json_start)
            response_text = response_text[json_start:json_end]
        elif '```' in response_text:
            json_start = response_text.find('```') + 3
            json_end = response_text.find('```', json_start)
            response_text = response_text[json_start:json_end]
        
        ai_response = json.loads(response_text.strip())
        return ai_response
        
    except (json.JSONDecodeError, Exception) as e:
        print(f"Error parsing AI response: {e}")
        # Fallback to default priorities
        return {
            "rankings": {},
            "strategy": {
                "max_depth_recommended": 4,
                "focus_extensions": [".py", ".js", ".jsx", ".ts", ".tsx"],
                "project_type": "unknown"
            }
        }

@app.post("/docs/from-github", response_model=DocumentationResponse)
async def generate_docs_from_github(request: GitHubDocumentationRequest):
    try:
        # Parse GitHub URL
        repo_info = parse_github_url(request.github_url)
        
        # Step 1: Get all files recursively for AI analysis
        print(f"Exploring repository structure for {repo_info['owner']}/{repo_info['repo']}...")
        all_files = get_all_files_recursively(
            repo_info["owner"], 
            repo_info["repo"], 
            repo_info["path"],
            max_depth=6  # Initial exploration depth
        )
        
        if not all_files:
            raise HTTPException(
                status_code=404, 
                detail="No files found in the specified repository or path"
            )
        
        print(f"Found {len(all_files)} total items")
        
        # Step 2: Get AI prioritization
        print("Getting AI file prioritization...")
        ai_analysis = get_ai_file_priorities(all_files, repo_info)
        rankings = ai_analysis.get("rankings", {})
        strategy = ai_analysis.get("strategy", {})
        
        print(f"AI recommended max depth: {strategy.get('max_depth_recommended', 4)}")
        print(f"AI detected project type: {strategy.get('project_type', 'unknown')}")
        
        # Step 3: Filter and prioritize files based on AI rankings
        prioritized_files = []
        
        print(f"AI rankings received: {rankings}")
        
        # Only include files (not directories) and prioritize by AI ranking
        for item in all_files:
            if item['type'] == 'file':
                filename = item['name']
                ai_score = rankings.get(filename, 0)
                
                print(f"File: {filename}, AI score: {ai_score}, Extension: {Path(filename).suffix.lower()}")
                
                # Include files with score 3 or higher (skip low-priority config files)
                if ai_score >= 3:
                    item['ai_score'] = ai_score
                    prioritized_files.append(item)
                    print(f"  ✓ Added {filename} with AI score {ai_score}")
                elif ai_score == 0:
                    # If AI didn't rank it, use fallback logic
                    file_ext = Path(filename).suffix.lower()
                    important_extensions = strategy.get('focus_extensions', ['.py', '.js', '.jsx', '.ts', '.tsx'])
                    if file_ext in important_extensions:
                        item['ai_score'] = 2  # Default medium priority
                        prioritized_files.append(item)
                        print(f"  ✓ Added {filename} with fallback score 3 (extension: {file_ext})")
                    else:
                        print(f"  ✗ Skipped {filename} (extension {file_ext} not in focus list)")
                else:
                    print(f"  ✗ Skipped {filename} (AI score {ai_score} < 3)")
        
        # Sort by AI score (highest first) and limit files
        prioritized_files.sort(key=lambda x: x.get('ai_score', 0), reverse=True)
        final_files = prioritized_files[:request.max_files]
        
        print(f"Final files selected: {[f['name'] for f in final_files]}")
        
        if not final_files:
            raise HTTPException(
                status_code=404, 
                detail=f"No high-priority code files found based on AI analysis. Total files explored: {len(all_files)}, AI rankings: {len(rankings)}"
            )
        
        print(f"Selected {len(final_files)} files for documentation based on AI priorities")
        
        # Step 4: Generate comprehensive repository documentation
        file_contents = []
        for file_info in final_files:
            try:
                print(f"Processing file: {file_info['name']} at path: {file_info['path']}")
                
                # Get fresh file details with download_url
                # For files, we need to get the specific file details which include download_url
                try:
                    file_details = get_github_contents(repo_info["owner"], repo_info["repo"], file_info["path"])
                    if file_details and len(file_details) > 0:
                        file_detail = file_details[0]
                        if file_detail.get('download_url'):
                            file_content = get_file_content(file_detail["download_url"])
                            file_contents.append({
                                "filename": file_info["name"],
                                "path": file_info["path"],
                                "content": file_content,
                                "ai_score": file_info.get("ai_score", 0),
                                "size": file_info.get("size", 0)
                            })
                            print(f"✓ Processed {file_info['name']} (AI score: {file_info.get('ai_score', 0)})")
                        else:
                            print(f"No download_url for {file_info['name']}")
                    else:
                        print(f"No file details returned for {file_info['path']}")
                except Exception as api_error:
                    print(f"API error getting file details for {file_info['name']}: {api_error}")
                    continue
                
            except Exception as e:
                print(f"Error processing {file_info['name']}: {e}")
                continue
        
        if not file_contents:
            # Provide detailed error information
            error_details = f"Failed to process any files. "
            error_details += f"Total files found: {len(all_files)}, "
            error_details += f"Files prioritized: {len(final_files)}, "
            error_details += f"AI rankings: {len(rankings)}"
            
            if final_files:
                error_details += f". Files attempted: {[f['name'] for f in final_files]}"
            
            raise HTTPException(
                status_code=500, 
                detail=error_details
            )
        
        # Step 5: Generate repository-level documentation with AI
        repo_name = f"{repo_info['owner']}/{repo_info['repo']}"
        
        # Create comprehensive prompt for repository analysis
        files_content = "\n\n".join([
            f"=== {item['filename']} (Priority: {item['ai_score']}/5) ===\nPath: {item['path']}\n{item['content']}" 
            for item in file_contents
        ])
        
        prompt = f"""
Analyze this codebase from repository '{repo_name}' and generate concise technical project documentation.

Project type: {strategy.get('project_type', 'unknown')}

CODEBASE CONTENT:
{files_content}

Generate well-structured documentation with these sections:

# 1. PROJECT OVERVIEW
- What this project does and its main purpose
- Key features and how it works
- Main user workflows(if applicable)
- Tech stack used

# 2. ARCHITECTURE & STRUCTURE  
- Overall project architecture
- Main components and their relationships
- Directory structure and organization

# 3. API REFERENCE (if applicable)
- Available endpoints and their purpose
- Request/response formats
- Authentication if needed

# 4. SETUP & USAGE
- How to install and run the project
- Configuration requirements
- Basic usage examples

Focus on the big picture and component relationships. Be practical and useful for developers who want to understand and work with this codebase.

Format as clear, well-structured Markdown.
"""
        
        print("Generating comprehensive documentation with AI...")
        
        # Generate documentation with increased token limit
        gen_config = types.GenerateContentConfig(
            temperature=0.3,  # Balanced for comprehensive analysis
            max_output_tokens=2048
        )
        
        try:
            response = client.models.generate_content(
                model="gemma-3-12b-it",
                contents=prompt,
                config=gen_config
            )
            
            # Clean up AI response by removing markdown code block wrappers
            ai_content = response.text.strip()
            
            # Remove markdown code blocks if present
            if ai_content.startswith('```markdown'):
                # Remove opening ```markdown
                ai_content = ai_content[11:].strip()
                # Remove closing ```
                if ai_content.endswith('```'):
                    ai_content = ai_content[:-3].strip()
            elif ai_content.startswith('```'):
                # Remove opening ```
                ai_content = ai_content[3:].strip()
                # Remove closing ```
                if ai_content.endswith('```'):
                    ai_content = ai_content[:-3].strip()
            
            # Create final documentation with metadata
            final_markdown = f"# {repo_name} - Project Documentation\n\n"
            final_markdown += f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            final_markdown += f"**AI Analysis:** {len(file_contents)} files prioritized and analyzed\n"
            final_markdown += f"**Project Type:** {strategy.get('project_type', 'unknown')}\n"
            
            if repo_info["path"]:
                final_markdown += f"**Path:** `{repo_info['path']}`\n"
            
            final_markdown += "\n---\n\n"
            final_markdown += ai_content
           
            return DocumentationResponse(markdown=final_markdown)
            
        except Exception as api_error:
            raise HTTPException(
                status_code=500, 
                detail=f"Error generating documentation: {str(api_error)}"
            )
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Unexpected error generating documentation from GitHub: {str(e)}"
        )


@app.post("/docs/download")
async def download_documentation(
    file: Optional[UploadFile] = File(None),
    code: Optional[str] = Form(None),
    isBase64: bool = Form(False)
):
    try:
        final_request = None
        
        # Debug information
        print(f"Code: {code and code[:50]}...")
        print(f"isBase64: {isBase64}")
        print(f"File: {file}")
        
        # Process uploaded file if present
        if file and file.filename:
            file_content = await file.read()
            try:
                file_content.decode('utf-8')  # Validate text file
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="Invalid text file.")
                
            # Create request from file
            base64_code = base64.b64encode(file_content).decode('utf-8')
            print(f"File content encoded to base64: {base64_code[:50]}...")
            final_request = CodeDocumentationRequest(code=base64_code, isBase64=True)
        
        # Process direct code input if present
        elif code:
            final_request = CodeDocumentationRequest(code=code, isBase64=isBase64)
            print(f"Using provided code input: {code[:50]}...")
          # If neither is provided
        else:
            raise HTTPException(status_code=400, detail="Either 'code' or 'file' field is required")
            
        # Generate documentation using the same logic as /docs/gen endpoint
        doc_response = await generate_documentation(final_request)
        
        # Create a timestamped filename for the download
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        doc_filename = f"code_documentation_{timestamp}.md"
        
        # Create a temporary file with the markdown content
        with NamedTemporaryFile(delete=False, mode='w', suffix='.md') as temp_file:
            temp_file.write(doc_response.markdown)
            temp_path = temp_file.name
        
        # Return the file as a download
        return FileResponse(
            path=temp_path,
            filename=doc_filename,
            media_type='text/markdown',
            background=BackgroundTask(lambda: os.unlink(temp_path))  # Delete file after download
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/docs/download-github")
async def download_github_documentation(request: GitHubDocumentationRequest):
    """
    Generate and download documentation for a GitHub repository as a .md file
    """
    try:
        # Use the existing GitHub documentation generation logic
        doc_response = await generate_docs_from_github(request)
        
        # Parse GitHub URL for filename
        repo_info = parse_github_url(request.github_url)
        repo_name = f"{repo_info['owner']}_{repo_info['repo']}"
        
        # Create a timestamped filename for the download
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        doc_filename = f"github_docs_{repo_name}_{timestamp}.md"
        
        # Create a temporary file with the markdown content
        with NamedTemporaryFile(delete=False, mode='w', suffix='.md', encoding='utf-8') as temp_file:
            temp_file.write(doc_response.markdown)
            temp_path = temp_file.name
        
        # Return the file as a download
        return FileResponse(
            path=temp_path,
            filename=doc_filename,
            media_type='text/markdown',
            background=BackgroundTask(lambda: os.unlink(temp_path))  # Delete file after download
        )
    except HTTPException:
        # Re-raise HTTP exceptions from generate_docs_from_github
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error generating GitHub documentation download: {str(e)}"
        )

# Add this if you want to run directly using python (not needed for uvicorn command line)
if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)