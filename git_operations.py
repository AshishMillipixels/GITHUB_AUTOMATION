import os
import git
import logging
import requests



# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('git_automation')



logger = logging.getLogger(__name__)

def init_local_repo(repo_path):
    """
    Initialize a local Git repository and set up the GitHub remote.
    
    Args:
        repo_path (str): Path where the repository should be initialized
    
    Returns:
        git.Repo: Initialized Git repository object
    
    Raises:
        Exception: If there's an error during repository initialization
    """
    try:
        # Ensure the repository path exists
        os.makedirs(repo_path, exist_ok=True)
        
        # Initialize the repository
        repo = git.Repo.init(repo_path)
        
        # Retrieve GitHub username from environment variable
        github_username = os.getenv("GITHUB_USERNAME")
        if not github_username:
            logger.warning("GITHUB_USERNAME environment variable is not set")
            return repo
        
        # Generate remote URL using repository basename
        repo_name = os.path.basename(repo_path)
        origin_url = f"https://github.com/{github_username}/{repo_name}.git"
        
        # Remove existing origin remote if it exists
        try:
            if "origin" in repo.remotes:
                repo.delete_remote("origin")
        except Exception as remote_delete_error:
            logger.warning(f"Could not delete existing remote: {remote_delete_error}")
        
        # Create new origin remote
        repo.create_remote("origin", origin_url)
        logger.info(f"Remote 'origin' set to: {origin_url}")
        
        return repo
    
    except Exception as e:
        logger.error(f"Error initializing repository: {e}")
        raise
    
def ensure_main_branch(repo_path):
    """Ensure the main branch exists and is set as default."""
    try:
        logger.info(f"Ensuring main branch exists in repository '{repo_path}'")
        repo = git.Repo(repo_path)

        # Check if 'main' exists
        if "main" not in [head.name for head in repo.heads]:
            # Convert master to main if it exists
            if "master" in [head.name for head in repo.heads]:
                repo.git.branch("-m", "master", "main")
                logger.info("Renamed 'master' branch to 'main'.")
            else:
                # Create an empty commit if repo is empty
                if not repo.heads:
                    repo.git.commit("--allow-empty", "-m", "Initial commit")
                    logger.info("Created initial empty commit.")
                # Now create main branch
                repo.git.checkout("-b", "main")
                logger.info("Created new 'main' branch.")

        # Set tracking if origin exists
        if "origin" in [remote.name for remote in repo.remotes]:
            try:
                repo.git.push("--set-upstream", "origin", "main")
                logger.info("'main' branch is now tracking origin/main.")
            except git.exc.GitCommandError as e:
                logger.warning(f"Could not set upstream: {e}")
                logger.info("You may need to create the remote repository first.")
        else:
            logger.warning("Remote 'origin' not found. Please add a remote manually.")
            
        return True
    except Exception as e:
        logger.error(f"Error ensuring main branch: {e}")
        raise

def create_branch(repo_path, branch_name):
    """Create a new branch if it doesn't already exist and check it out."""
    try:
        logger.info(f"Creating branch '{branch_name}' in repository '{repo_path}'")
        repo = git.Repo(repo_path)

        # Check if the branch already exists
        if branch_name in [head.name for head in repo.heads]:
            logger.info(f"Branch '{branch_name}' already exists.")
            repo.git.checkout(branch_name)
            logger.info(f"Switched to branch '{branch_name}'.")
            return f"Branch '{branch_name}' already exists and checked out."

        # Create the branch and check it out
        new_branch = repo.create_head(branch_name)
        repo.head.reference = new_branch
        repo.head.reset(index=True, working_tree=True)
        logger.info(f"Branch '{branch_name}' created successfully and checked out.")
        return f"Branch '{branch_name}' created and checked out."
    except Exception as e:
        logger.error(f"Error creating branch: {e}")
        raise

def add_and_commit(repo_path, commit_message):
    """Stage all changes and commit them with the specified message."""
    try:
        logger.info(f"Committing changes in repository '{repo_path}' with message: {commit_message}")
        repo = git.Repo(repo_path)

        # Check if there are changes to commit
        if not repo.is_dirty(untracked_files=True):
            logger.info("No changes to commit.")
            return False
        
        repo.git.add(A=True)
        commit = repo.index.commit(commit_message)
        logger.info(f"Changes committed: {commit_message} (Commit ID: {commit.hexsha[:7]})")
        return True
    except Exception as e:
        logger.error(f"Error committing changes: {e}")
        raise



def push_changes(repo_path, remote_name="origin", branch=None):
    
    try:
        # Open the repository
        repo = git.Repo(repo_path)
        
        # Set default branch to 'main' if not specified
        if branch is None:
            branch = "main"
        
        # Ensure there's a remote configured
        github_username = os.getenv("GITHUB_USERNAME")
        if not github_username:
            raise ValueError("GITHUB_USERNAME environment variable is not set")
        
        repo_name = os.path.basename(repo_path)
        remote_url = f"https://github.com/{github_username}/{repo_name}.git"
        
        # Check if remote exists, create if not
        try:
            origin = repo.remote(name=remote_name)
        except ValueError:
            # Remote doesn't exist, create it
            origin = repo.create_remote(remote_name, remote_url)
            logger.info(f"Created remote '{remote_name}' with URL: {remote_url}")
        
        # Check if branch exists locally; if not, create it
        if branch not in repo.heads:
            repo.git.checkout("-b", branch)  # Create and checkout branch
            logger.info(f"Created local branch '{branch}'")
        
        # Ensure local branch is tracking remote branch
        try:
            repo.git.branch(f"--set-upstream-to={remote_name}/{branch}", branch)
            logger.info(f"Set upstream for local branch '{branch}' to '{remote_name}/{branch}'")
        except git.GitCommandError as upstream_error:
            logger.warning(f"Could not set upstream: {upstream_error}")
        
        # Ensure there are changes to commit
        if repo.is_dirty(untracked_files=True):
            # Add all changes
            repo.git.add(A=True)
            
            # Commit changes with a default message
            commit_message = "Initial commit or update"
            repo.index.commit(commit_message)
            logger.info("Committed changes")
        
        # Push changes
        try:
            push_result = origin.push(branch)
            
            # Check push result
            if push_result and push_result[0].flags & push_result[0].ERROR:
                raise ValueError(f"Push failed: {push_result[0].summary}")
            
            logger.info(f"Successfully pushed {branch} to {remote_name}")
            return True
        
        except git.GitCommandError as push_error:
            logger.error(f"Git push error: {push_error}")
            raise
    
    except Exception as e:
        logger.error(f"Push error: {str(e)}")
        raise

def ensure_main_branch(repo_path):
    try:
        repo = git.Repo(repo_path)
        if "main" not in repo.heads:
            # Create main branch if it doesn't exist
            repo.git.checkout("-b", "main")
            logger.info("Created 'main' branch")
        
        # Link to origin/main if remote exists
        if "origin" in repo.remotes and "origin/main" in repo.remote().refs:
            repo.git.push("--set-upstream", "origin", "main")
            logger.info("Linked 'main' to 'origin/main'")
        
        return True
    except Exception as e:
        logger.error(f"Error ensuring main branch: {str(e)}")
        raise


def add_file_with_content(repo_path, file_name, content):
    """
    Create a file with the specified content in the repository.
    
    Args:
        repo_path (str): Path to the repository
        file_name (str): Name of the file to create
        content (str): Content to write to the file
    
    Returns:
        str: Success message
    """
    try:
        logger.info(f"Creating file '{file_name}' in repository '{repo_path}'")
        
        # Create the full path for the file
        file_path = os.path.join(repo_path, file_name)
        
        # Write content directly to file using Python instead of shell commands
        with open(file_path, 'w') as f:
            f.write(content)
            
        logger.info(f"File '{file_name}' created successfully")
        return f"File '{file_name}' created successfully"
    except Exception as e:
        logger.error(f"Error creating file: {e}")
        raise
    
def merge_branch(repo_path, source_branch, target_branch="main"):
    """Merge source branch into target branch."""
    try:
        logger.info(f"Merging branch '{source_branch}' into '{target_branch}' in repository '{repo_path}'")
        repo = git.Repo(repo_path)

        # Make sure branches exist
        if source_branch not in [head.name for head in repo.heads]:
            error_msg = f"Source branch '{source_branch}' does not exist!"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if target_branch not in [head.name for head in repo.heads]:
            error_msg = f"Target branch '{target_branch}' does not exist!"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Save current branch to return to it later
        current_branch = repo.active_branch.name
        
        # Checkout target branch
        repo.git.checkout(target_branch)
        logger.info(f"Checked out '{target_branch}'")

        # Attempt merge
        try:
            repo.git.merge(source_branch)
            logger.info(f"Merged '{source_branch}' into '{target_branch}' successfully!")
            success = True
        except git.exc.GitCommandError as e:
            logger.error(f"Merge failed: {e}")
            # Abort merge if conflict occurred
            repo.git.merge("--abort")
            logger.info("Merge aborted due to conflicts.")
            success = False
        
        # Return to original branch if different
        if current_branch != target_branch:
            repo.git.checkout(current_branch)
            logger.info(f"Returned to '{current_branch}'")
            
        return success
    except Exception as e:
        logger.error(f"Error during merge operation: {e}")
        raise

def create_pr(repo_path, branch_name, title=None, body=None):
    """
    Create a pull request for the given branch.
    
    Args:
        repo_path (str): Path to the local repository.
        branch_name (str): Name of the branch to create a PR for.
        title (str, optional): Title of the pull request.
        body (str, optional): Body/description of the pull request.
        
    Returns:
        dict: Pull request information from GitHub API.
    """
    try:
        logger.info(f"Creating PR for branch '{branch_name}' in repository '{repo_path}'")
        repo = git.Repo(repo_path)
        repo_name = os.path.basename(repo_path)
        base_branch = "main"  # Default base branch
        
        # Default title and body if not provided
        if not title:
            title = f"Merge {branch_name} into {base_branch}"
            logger.info(f"Using default PR title: {title}")
        if not body:
            body = f"Automated PR: Merging {branch_name} into {base_branch}"
            logger.info(f"Using default PR body: {body}")
        
        # Importing here to avoid circular import if this module is imported elsewhere
        from github_api import create_pull_request
        
        # Create the pull request using the GitHub API
        pr_info = create_pull_request(repo_name, branch_name, base_branch, title, body)
        logger.info(f"Pull request created successfully: {pr_info['html_url']}")
        return pr_info
    except Exception as e:
        logger.error(f"Error creating pull request: {e}")
        raise

def repo_status(repo_path):
    """Check and return the status of the repository."""
    try:
        logger.info(f"Checking status of repository '{repo_path}'")
        repo = git.Repo(repo_path)
        status = repo.git.status()
        logger.info(f"Repository status:\n{status}")
        return status
    except Exception as e:
        logger.error(f"Error checking repository status: {e}")
        raise

# Predefined Gitignore Templates
GITIGNORE_TEMPLATES = {
    "python": """
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Virtual environment
venv/
env/
*.egg-info/
.Python
pip-log.txt
pip-delete-this-directory.txt

# IDE settings
.vscode/
.idea/
*.swp
""",
    "node": """
# Node.js dependencies
node_modules/
npm-debug.log
yarn-error.log
""",
    "rust": """
# Rust specific
/target/
**/*.rs.bk
Cargo.lock
""",
    "general": """
# Logs
logs
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# OS files
.DS_Store
Thumbs.db
"""
}

def detect_project_type(repo_path):
    """
    Detect the project type based on existing files.
    Returns a list of detected project types.
    """
    try:
        logger.info(f"Detecting project type for repository at '{repo_path}'")
        project_types = set()
        
        if not os.path.exists(repo_path):
            logger.warning(f"Repository path {repo_path} does not exist.")
            return ["general"]
            
        files = os.listdir(repo_path)
        
        # Python detection
        if any(f.endswith(".py") for f in files) or "requirements.txt" in files:
            project_types.add("python")
            logger.info("Python project detected")

        # Node.js detection
        if any(f.endswith(".js") for f in files) or "package.json" in files:
            project_types.add("node")
            logger.info("Node.js project detected")
            
        # Rust detection
        if any(f.endswith(".rs") for f in files) or "Cargo.toml" in files:
            project_types.add("rust")
            logger.info("Rust project detected")
            
        # Default to general if no specific type detected
        if not project_types:
            project_types.add("general")
            logger.info("No specific project type detected, using general")
            
        logger.info(f"Detected project types: {', '.join(project_types)}")
        return list(project_types)
    except Exception as e:
        logger.error(f"Error detecting project type: {e}")
        return ["general"]

def generate_gitignore(repo_path):
    """
    Generate a .gitignore file by detecting the project type.
    Combines multiple templates if multiple project types are detected.
    """
    try:
        logger.info(f"Generating .gitignore file for repository at '{repo_path}'")
        gitignore_path = os.path.join(repo_path, ".gitignore")
        project_types = detect_project_type(repo_path)
        
        # Combine templates for all detected project types
        gitignore_content = "\n".join(
            GITIGNORE_TEMPLATES.get(ptype, GITIGNORE_TEMPLATES["general"]) 
            for ptype in project_types
        )

        # Write .gitignore file
        with open(gitignore_path, "w") as gitignore_file:
            gitignore_file.write(gitignore_content.strip())

        logger.info(f".gitignore file generated for {', '.join(project_types)} projects at {gitignore_path}")
        
        # Optionally commit the .gitignore file
        try:
            repo = git.Repo(repo_path)
            repo.git.add(".gitignore")
            repo.index.commit(f"Add .gitignore for {', '.join(project_types)} project")
            logger.info(".gitignore committed successfully.")
        except Exception as e:
            logger.warning(f"Could not commit .gitignore: {e}")
            
        return gitignore_path
    except Exception as e:
        logger.error(f"Error generating .gitignore: {e}")
        raise

def download_github_gitignore(repo_path, project_type=None):
    """
    Download a .gitignore template from GitHub's gitignore repository.
    If project_type is None, it will be auto-detected.
    """
    try:
        logger.info(f"Downloading GitHub .gitignore template for repository at '{repo_path}'")
        if project_type is None:
            detected_types = detect_project_type(repo_path)
            # Use the first detected type
            project_type = detected_types[0].capitalize()
            logger.info(f"Auto-detected project type: {project_type}")
            
        gitignore_url = f"https://raw.githubusercontent.com/github/gitignore/main/{project_type}.gitignore"
        logger.info(f"Fetching .gitignore template from: {gitignore_url}")
        
        response = requests.get(gitignore_url)
        
        if response.status_code == 200:
            gitignore_path = os.path.join(repo_path, ".gitignore")
            with open(gitignore_path, "w") as f:
                f.write(response.text)
            logger.info(f".gitignore downloaded successfully for {project_type} project at {gitignore_path}")
            
            # Commit the downloaded .gitignore
            try:
                repo = git.Repo(repo_path)
                repo.git.add(".gitignore")
                repo.index.commit(f"Add GitHub's {project_type} .gitignore template")
                logger.info(".gitignore committed successfully")
            except Exception as e:
                logger.warning(f"Could not commit .gitignore: {e}")
                
            return gitignore_path
        else:
            logger.warning(f"Failed to download .gitignore template: HTTP {response.status_code}")
            logger.info("Falling back to local template generation")
            # Fall back to local template
            return generate_gitignore(repo_path)
    except Exception as e:
        logger.error(f"Error downloading GitHub .gitignore: {e}")
        logger.info("Falling back to local template generation")
        # Fall back to local template
        return generate_gitignore(repo_path)
    
def list_directory_contents(repo_path):
    """List the contents of a directory."""
    try:
        logger.info(f"Listing contents of directory '{repo_path}'")
        if not os.path.exists(repo_path):
            error_msg = f"Directory '{repo_path}' does not exist."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        contents = os.listdir(repo_path)
        logger.info(f"Contents of '{repo_path}': {contents}")
        return contents
    except Exception as e:
        logger.error(f"Error listing directory contents: {e}")
        raise

def add_file_with_content(repo_path: str, file_name: str, content: str):
    """Create a file with content in the repository"""
    try:
        file_path = os.path.join(repo_path, file_name)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w') as f:
            f.write(content)
            
        logger.info(f"File {file_name} created at {repo_path}")
        return f"File {file_name} added successfully"
        
    except Exception as e:
        logger.error(f"Error adding file: {e}")
        raise

def read_file_contents(repo_path, file_name):
    """Read the contents of a file."""
    try:
        logger.info(f"Reading contents of file '{file_name}' in '{repo_path}'")
        file_path = os.path.join(repo_path, file_name)
        if not os.path.exists(file_path):
            error_msg = f"File '{file_name}' does not exist in '{repo_path}'."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        with open(file_path, "r") as file:
            contents = file.read()
            logger.info(f"Successfully read contents of '{file_name}'")
            return contents
    except Exception as e:
        logger.error(f"Error reading file contents: {e}")
        raise

# Example usage for FastAPI response formatting
def format_response(success, message, data=None):
    """Format a consistent response for FastAPI endpoints"""
    response = {
        "success": success,
        "message": message
    }
    if data is not None:
        response["data"] = data
    return response


def add_multiple_files(repo_path: str, files: list):
    """
    Add multiple files to the repository at once.
    
    Args:
        repo_path: Path to the repository (string)
        files: List of dictionaries with 'path' and 'content' keys
        
    Returns:
        Dictionary with operation results
    """
    try:
        logger.info(f"Adding multiple files to repository '{repo_path}'")
        created_files = []
        errors = []
        
        for file_info in files:
            try:
                file_path = file_info['path']
                content = file_info['content']
                full_path = os.path.join(repo_path, file_path)
                
                # Create directory structure if needed
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                with open(full_path, 'w') as f:
                    f.write(content)
                
                logger.info(f"File '{file_path}' created successfully")
                created_files.append(file_path)
            except Exception as e:
                error_msg = f"Failed to create file '{file_path}': {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        return {
            "success": len(errors) == 0,
            "message": f"Created {len(created_files)} files, {len(errors)} errors",
            "created_files": created_files,
            "errors": errors
        }
    except Exception as e:
        logger.error(f"Error in batch file creation: {e}")
        raise