# github_api.py
import os
import requests
import logging
from urllib.parse import urljoin

# Set up logging
logger = logging.getLogger('github_api')

# Configuration
BASE_URL = "https://api.github.com"
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors."""
    def __init__(self, message, status_code=None, response=None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)

# In github_api.py, modify the _check_token function:

def _check_token():
    """Check if GitHub token is available."""
    global GITHUB_TOKEN
    # Try to get the token from the environment again if it's not set
    if not GITHUB_TOKEN:
        GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
        
    if not GITHUB_TOKEN:
        raise GitHubAPIError(
            "GitHub token not found. Please set the GITHUB_TOKEN environment variable."
        )

def _make_request(method, endpoint, data=None, params=None):
    """Make a request to the GitHub API with error handling."""
    _check_token()
    
    url = urljoin(BASE_URL, endpoint)
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    logger.debug(f"Making {method} request to {url}")
    
    try:
        if method.lower() == 'get':
            response = requests.get(url, headers=headers, params=params)
        elif method.lower() == 'post':
            response = requests.post(url, headers=headers, json=data)
        elif method.lower() == 'put':
            response = requests.put(url, headers=headers, json=data)
        elif method.lower() == 'delete':
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        # Check for error status codes
        if response.status_code >= 400:
            error_msg = f"GitHub API error ({response.status_code})"
            try:
                error_detail = response.json().get('message', 'No details available')
                error_msg += f": {error_detail}"
            except:
                pass
            
            raise GitHubAPIError(error_msg, response.status_code, response)
            
        return response
        
    except requests.RequestException as e:
        raise GitHubAPIError(f"Request failed: {e}")
    







    

def create_github_repo(repo_name, private=True, description=None):
    """
    Create a new GitHub repository.
    
    Args:
        repo_name (str): Name of the repository
        private (bool): Whether the repository should be private
        description (str, optional): Repository description
        
    Returns:
        dict: Repository information
    
    Raises:
        GitHubAPIError: If the repository creation fails
    """
    data = {
        "name": repo_name,
        "private": private,
        "auto_init": False,  # Don't initialize with README (we'll do it locally)
    }
    
    if description:
        data["description"] = description
    
    response = _make_request('post', "/user/repos", data=data)
    
    if response.status_code == 201:
        repo_info = response.json()
        logger.info(f"Repository '{repo_name}' created successfully at {repo_info['html_url']}")
        return repo_info
    else:
        # Log the full error response for debugging
        error_detail = response.json()
        logger.error(f"GitHub API error details: {error_detail}")
        raise GitHubAPIError(f"Repository creation failed. Details: {error_detail.get('message', 'Unknown error')}", response.status_code, response)



def list_repositories(page=1, per_page=30):
    """
    List repositories for the authenticated user.
    
    Args:
        page (int): Page number for pagination
        per_page (int): Number of repositories per page
        
    Returns:
        list: List of repository information dictionaries
    """
    params = {
        "page": page,
        "per_page": per_page,
        "sort": "updated",
        "direction": "desc"
    }
    
    response = _make_request('get', "/user/repos", params=params)
    return response.json()

def get_repository(repo_name):
    """
    Get information about a specific repository.
    
    Args:
        repo_name (str): Name of the repository
        
    Returns:
        dict: Repository information
        
    Raises:
        GitHubAPIError: If the repository doesn't exist
    """
    endpoint = f"/repos/{GITHUB_USERNAME}/{repo_name}"
    response = _make_request('get', endpoint)
    return response.json()

def delete_repository(repo_name):
    """
    Delete a repository.
    
    Args:
        repo_name (str): Name of the repository to delete
        
    Returns:
        bool: True if deletion was successful
        
    Raises:
        GitHubAPIError: If deletion fails
    """
    endpoint = f"/repos/{GITHUB_USERNAME}/{repo_name}"
    response = _make_request('delete', endpoint)
    
    # Successful deletion returns 204 No Content
    return response.status_code == 204

def list_branches(repo_name):
    """
    List all branches in a repository.
    
    Args:
        repo_name (str): Name of the repository
        
    Returns:
        list: List of branch information dictionaries
    """
    endpoint = f"/repos/{GITHUB_USERNAME}/{repo_name}/branches"
    response = _make_request('get', endpoint)
    return response.json()

def create_issue(repo_name, title, body=None, labels=None):
    """
    Create an issue in a repository.
    
    Args:
        repo_name (str): Name of the repository
        title (str): Issue title
        body (str, optional): Issue description
        labels (list, optional): List of label names
        
    Returns:
        dict: Issue information
    """
    data = {
        "title": title
    }
    
    if body:
        data["body"] = body
        
    if labels:
        data["labels"] = labels
    
    endpoint = f"/repos/{GITHUB_USERNAME}/{repo_name}/issues"
    response = _make_request('post', endpoint, data=data)
    
    issue_info = response.json()
    logger.info(f"Issue created: {issue_info['html_url']}")
    return issue_info

def list_pull_requests(repo_name, state="open"):
    """
    List pull requests in a repository.
    
    Args:
        repo_name (str): Name of the repository
        state (str): State of pull requests to list ('open', 'closed', 'all')
        
    Returns:
        list: List of pull request information dictionaries
    """
    endpoint = f"/repos/{GITHUB_USERNAME}/{repo_name}/pulls"
    params = {"state": state}
    
    response = _make_request('get', endpoint, params=params)
    return response.json()




def create_pull_request(repo_name, branch_name, base_branch="main", title=None, body=None):
    """
    Create a pull request on GitHub.
    
    Args:
        repo_name (str): Name of the repository.
        branch_name (str): Name of the branch to merge from (head).
        base_branch (str): Name of the branch to merge into (base).
        title (str, optional): Title for the pull request.
        body (str, optional): Body/description for the pull request.
        
    Returns:
        dict: Pull request information.
    """
    # Default title and body if not provided
    if not title:
        title = f"Merge {branch_name} into {base_branch}"
    if not body:
        body = f"Automated PR: Merging {branch_name} into {base_branch}"
    
    data = {
        "title": title,
        "head": branch_name,
        "base": base_branch,
        "body": body
    }
    
    endpoint = f"/repos/{GITHUB_USERNAME}/{repo_name}/pulls"
    response = _make_request('post', endpoint, data=data)
    
    pr_info = response.json()
    logger.info(f"Pull Request created: {pr_info['html_url']}")
    return pr_info


















# For testing purposes
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Test creating a repository
        repo_info = create_github_repo("test-repo", private=True, description="Testing GitHub API")
        print(f"Created repo: {repo_info['html_url']}")
        
        # List all repositories
        repos = list_repositories()
        print(f"Found {len(repos)} repositories")
        
    except GitHubAPIError as e:
        print(f"Error: {e}")
        


