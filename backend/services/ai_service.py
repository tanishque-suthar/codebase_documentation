import base64
import json
from typing import Dict, List
from datetime import datetime
import google.generativeai as genai
import os
from pathlib import Path


class AIDocumentationService:
    def __init__(self):
        """Initialize the AI service with Google AI client"""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set.")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemma-3-12b-it")
    
    def decode_code(self, code: str, is_base64: bool = False) -> str:
        """Decode code from base64 if needed"""
        if is_base64:
            return base64.b64decode(code).decode('utf-8')
        return code
    
    def generate_code_documentation(self, code: str) -> str:
        """Generate documentation for a single code snippet"""
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
        
        # Generate documentation with AI
        response = self.model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=1024
            )
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
        
        return ai_content
    
    def get_ai_file_priorities(self, file_list: List[Dict], repo_info: Dict) -> Dict:
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
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=1024
                )
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
    
    def generate_repository_documentation(self, file_contents: List[Dict], repo_info: Dict, strategy: Dict) -> str:
        """Generate comprehensive repository documentation"""
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
        
        # Generate documentation with increased token limit
        response = self.model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=2048
            )
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
        
        if repo_info.get("path"):
            final_markdown += f"**Path:** `{repo_info['path']}`\n"
        
        final_markdown += "\n---\n\n"
        final_markdown += ai_content
        
        return final_markdown
