from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from same directory as app.py
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path, override=True)

app = FastAPI()



import git
import logging


from typing import Optional, List
from fastapi.middleware.cors import CORSMiddleware


from git_operations import (
    init_local_repo, create_branch, add_and_commit, push_changes, 
    merge_branch, repo_status, generate_gitignore, download_github_gitignore, 
    list_directory_contents, read_file_contents, format_response, detect_project_type, add_file_with_content,
    add_multiple_files
)
from github_api import (
    create_github_repo, list_repositories, list_branches, create_issue,
    list_pull_requests
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fastapi_server')

# Initialize FastAPI app
app = FastAPI(
    title="GitHub Automation API",
    description="REST API for automating Git and GitHub operations",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request validation
class RepoCreate(BaseModel):
    repo_name: str = Field(..., description="Name of the repository")
    private: bool = Field(True, description="Whether the repository is private")
    description: Optional[str] = Field(None, description="Repository description")

class BranchCreate(BaseModel):
    repo_path: str = Field(..., description="Path to the repository")
    branch_name: str = Field(..., description="Name of the branch to create")

class CommitRequest(BaseModel):
    repo_path: str = Field(..., description="Path to the repository")
    commit_message: str = Field(..., description="Commit message")

class PushRequest(BaseModel):
    repo_path: str = Field(..., description="Path to the repository")
    remote_name: str = Field("origin", description="Remote name")
    branch: Optional[str] = Field(None, description="Branch name")

class FileRequest(BaseModel):
    repo_path: str = Field(..., description="Path to the repository")
    file_name: str = Field(..., description="File name")
    content: str = Field(..., description="File content")

class MergeRequest(BaseModel):
    repo_path: str = Field(..., description="Path to the repository")
    source_branch: str = Field(..., description="Source branch name")
    target_branch: str = Field("main", description="Target branch name")

class PRRequest(BaseModel):
    repo_path: str = Field(..., description="Path to the repository")
    branch_name: str = Field(..., description="Branch name")
    title: Optional[str] = Field(None, description="PR title")
    body: Optional[str] = Field(None, description="PR description")

class GitignoreRequest(BaseModel):
    repo_path: str = Field(..., description="Path to the repository")
    project_type: Optional[str] = Field(None, description="Project type")

class IssueRequest(BaseModel):
    repo_name: str = Field(..., description="Repository name")
    title: str = Field(..., description="Issue title")
    body: Optional[str] = Field(None, description="Issue description")
    labels: Optional[List[str]] = Field(None, description="Issue labels")

class Credentials(BaseModel):
    username: str
    token: str

class RepoInitRequest(BaseModel):
    repo_path: str = Field(..., description="Path to initialize the repository")

class FileRequest(BaseModel):
    repo_path: str = Field(..., description="Path to the repository")
    file_name: str = Field(..., description="File name")
    content: str = Field(..., description="File content")


class FileContent(BaseModel):
    path: str = Field(..., example="src/main.py", description="Relative path of the file")
    content: str = Field(..., example="print('Hello')", description="File content")

class BatchFileRequest(BaseModel):
    repo_path: str = Field(..., example="./bundle", description="Path to the repository")
    files: List[FileContent] = Field(..., description="List of files to add")


class AddAllRequest(BaseModel):
    repo_path: str = Field(..., description="Path to the repository")
    include_untracked: bool = Field(
        True, 
        description="Whether to include untracked files (git add -A when True, git add . when False)"
    )

# Root endpoint
@app.get("/")
async def root():
    return format_response(True, "GitHub Automation API is running")

@app.post("/auth/setup")
async def setup_credentials(credentials: Credentials):
    try:
        # Set for current process
        os.environ["GITHUB_USERNAME"] = credentials.username
        os.environ["GITHUB_TOKEN"] = credentials.token
        
        # Write to .env file
        with open(env_path, "w") as f:
            f.write(f"GITHUB_USERNAME={credentials.username}\n")
            f.write(f"GITHUB_TOKEN={credentials.token}\n")
            
        return {
            "status": "success",
            "message": "Credentials saved to .env",
            "env_path": str(env_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/verify")
async def verify_credentials():
    return {
        "username": os.getenv("GITHUB_USERNAME"),
        "token_exists": bool(os.getenv("GITHUB_TOKEN"))
    }


@app.post("/repos/init", summary="Initialize a local Git repository")
async def initialize_repo(request: RepoInitRequest):
    try:
        repo = init_local_repo(request.repo_path)
        return format_response(
            True, 
            f"Repository initialized at {request.repo_path}",
            {"repo_path": request.repo_path}
        )
    except Exception as e:
        logger.error(f"Error initializing repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/repos/create-branch", summary="Create a new branch")
async def create_new_branch(request: BranchCreate):
    try:
        result = create_branch(request.repo_path, request.branch_name)
        return format_response(True, result)
    except Exception as e:
        logger.error(f"Error creating branch: {e}")
        raise HTTPException(status_code=500, detail=str(e))





@app.post("/repos/add-files", 
          summary="Add multiple files to repository",
          response_description="Result of the batch file operation")
async def api_add_multiple_files(request: BatchFileRequest):
    """
    Add multiple files to a repository in one operation.
    
    Example:
    {
        "repo_path": "./bundle",
        "files": [
            {"path": "README.md", "content": "# My Project"},
            {"path": "src/main.py", "content": "print('Hello')"}
        ]
    }
    """
    try:
        # Convert Pydantic model to dict format expected by the operation
        files_list = [{"path": f.path, "content": f.content} for f in request.files]
        
        result = add_multiple_files(request.repo_path, files_list)
        
        if result["success"]:
            return format_response(
                True,
                result["message"],
                {"created_files": result["created_files"]}
            )
        else:
            return format_response(
                False,
                result["message"],
                {
                    "created_files": result.get("created_files", []),
                    "errors": result.get("errors", [])
                }
            )
    except Exception as e:
        logger.error(f"API Error: Failed to add files: {e}")
        raise HTTPException(status_code=500, detail=str(e))








@app.post("/repos/commit", summary="Stage and commit changes")
async def commit_changes(request: CommitRequest):
    try:
        result = add_and_commit(request.repo_path, request.commit_message)
        return format_response(True, f"Changes committed with message: {request.commit_message}")
    except Exception as e:
        logger.error(f"Error committing changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/repos/push")
async def push_to_remote(request: PushRequest):
    try:
        success = push_changes(request.repo_path, request.remote_name, request.branch)
        return {
            "success": success,
            "message": "Pushed changes successfully" if success else "Push failed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/repos/merge", summary="Merge branches")
async def merge(request: MergeRequest):
    try:
        result = merge_branch(request.repo_path, request.source_branch, request.target_branch)
        return format_response(True, f"Merged {request.source_branch} into {request.target_branch} successfully")
    except Exception as e:
        logger.error(f"Error merging branches: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/repos/status/{repo_path:path}", summary="Get repository status")
async def get_status(repo_path: str):
    try:
        status = repo_status(repo_path)
        return format_response(True, "Repository status retrieved", {"status": status})
    except Exception as e:
        logger.error(f"Error getting repository status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/repos/generate-gitignore", summary="Generate gitignore file")
async def generate(request: GitignoreRequest):
    try:
        path = generate_gitignore(request.repo_path)
        return format_response(True, f"Gitignore file generated at {path}")
    except Exception as e:
        logger.error(f"Error generating gitignore: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/repos/download-gitignore", summary="Download GitHub gitignore template")
async def download_gitignore(request: GitignoreRequest):
    try:
        path = download_github_gitignore(request.repo_path, request.project_type)
        return format_response(True, f"GitHub gitignore template downloaded to {path}")
    except Exception as e:
        logger.error(f"Error downloading gitignore: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/repos/detect-project-type/{repo_path:path}", summary="Detect project type")
async def detect_type(repo_path: str):
    try:
        project_types = detect_project_type(repo_path)
        return format_response(True, "Project type detected", {"project_types": project_types})
    except Exception as e:
        logger.error(f"Error detecting project type: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/repos/list-files/{repo_path:path}", summary="List directory contents")
async def list_files(repo_path: str):
    try:
        contents = list_directory_contents(repo_path)
        return format_response(True, f"Contents of {repo_path}", {"contents": contents})
    except Exception as e:
        logger.error(f"Error listing directory contents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/repos/read-file/{repo_path:path}/{file_name:path}", summary="Read file contents")
async def read_file(repo_path: str, file_name: str):
    try:
        contents = read_file_contents(repo_path, file_name)
        return format_response(True, f"Contents of {file_name}", {"contents": contents})
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/repos/add-file", summary="Add a file with content to repository")
async def add_file(request: FileRequest):
    try:
        result = add_file_with_content(
            request.repo_path,
            request.file_name,
            request.content
        )
        return format_response(True, result)
    except Exception as e:
        logger.error(f"Error adding file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# GitHub API operations
@app.post("/github/create-repo", summary="Create a GitHub repository")
async def create_repo(request: RepoCreate):
    try:
        repo_info = create_github_repo(request.repo_name, request.private, request.description)
        return format_response(True, f"Repository {request.repo_name} created", {"repo_info": repo_info})
    except Exception as e:
        logger.error(f"Error creating GitHub repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/github/list-repos", summary="List GitHub repositories")
async def list_repos(page: int = 1, per_page: int = 30):
    try:
        repos = list_repositories(page, per_page)
        return format_response(True, f"Retrieved {len(repos)} repositories", {"repositories": repos})
    except Exception as e:
        logger.error(f"Error listing repositories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/github/list-branches/{repo_name}", summary="List branches in a repository")
async def list_repo_branches(repo_name: str):
    try:
        branches = list_branches(repo_name)
        return format_response(True, f"Retrieved branches for {repo_name}", {"branches": branches})
    except Exception as e:
        logger.error(f"Error listing branches: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/github/create-issue", summary="Create an issue")
async def create_github_issue(request: IssueRequest):
    try:
        issue = create_issue(request.repo_name, request.title, request.body, request.labels)
        return format_response(True, f"Issue created in {request.repo_name}", {"issue": issue})
    except Exception as e:
        logger.error(f"Error creating issue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

"""@app.post("/github/create-pr", summary="Create a pull request")
async def create_github_pr(request: PRRequest):
    try:
        pr_info = create_pr(request.repo_path, request.branch_name, request.title, request.body)
        return format_response(True, "Pull request created", {"pull_request": pr_info})
    except Exception as e:
        logger.error(f"Error creating pull request: {e}")
        raise HTTPException(status_code=500, detail=str(e))
"""
@app.get("/github/list-prs/{repo_name}", summary="List pull requests")
async def list_prs(repo_name: str, state: str = "open"):
    try:
        prs = list_pull_requests(repo_name, state)
        return format_response(True, f"Retrieved {len(prs)} pull requests for {repo_name}", {"pull_requests": prs})
    except Exception as e:
        logger.error(f"Error listing pull requests: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    


@app.post("/repos/add-all", summary="Stage all changes (git add -A or git add .)")
async def add_all_changes(request: AddAllRequest):
    """
    Stage all changes in the repository.
    
    Equivalent to:
    - git add -A (when include_untracked=True)
    - git add . (when include_untracked=False)
    """
    try:
        repo = git.Repo(request.repo_path)
        
        if request.include_untracked:
            # git add -A (stages all changes including untracked files)
            repo.git.add(A=True)
            action = "Added all changes including untracked files (-A)"
        else:
            # git add . (stages only tracked files in current dir)
            repo.git.add(".")
            action = "Added current directory changes (.)"
            
        changed_files = [item.a_path for item in repo.index.diff(None)] + \
                       [item.a_path for item in repo.index.diff("HEAD")]
        
        return format_response(
            True,
            action,
            {"staged_files": list(set(changed_files))}  # Remove duplicates
        )
    except Exception as e:
        logger.error(f"Error adding changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)