from fastapi import APIRouter, HTTPException
from typing import List, Dict
from pathlib import Path
from models.schemas import GitHubDocumentationRequest, DocumentationResponse
from services.ai_service import AIDocumentationService
from services.github_service import (
    parse_github_url, 
    get_github_contents, 
    get_file_content, 
    get_all_files_recursively
)

router = APIRouter(prefix="/docs", tags=["github"])

# Initialize AI service
ai_service = AIDocumentationService()

def get_ai_file_priorities(file_list: List[Dict], repo_info: Dict) -> Dict:
    """
    Use AI to rank file importance and suggest exploration strategy
    """
    return ai_service.get_ai_file_priorities(file_list, repo_info)

@router.post("/from-github", response_model=DocumentationResponse)
async def generate_docs_from_github(request: GitHubDocumentationRequest):
    """Generate documentation from GitHub repository"""
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
        try:
            final_markdown = ai_service.generate_repository_documentation(file_contents, repo_info, strategy)
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
