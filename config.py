from dotenv import load_dotenv
import os
from getpass import getpass
from pathlib import Path

# Load .env from same directory as config.py
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

def get_github_credentials():
    """Prompt the user for GitHub credentials."""
    try:
        github_username = input("Enter your GitHub username: ").strip()
        if not github_username:
            raise ValueError("GitHub username cannot be empty.")
        
        github_token = getpass("Enter your GitHub API token: ").strip()
        if not github_token:
            raise ValueError("GitHub API token cannot be empty.")
        
        return github_username, github_token
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        exit(1)

def set_github_credentials():
    """Set GitHub credentials as environment variables and save to .env"""
    try:
        github_username, github_token = get_github_credentials()
        
        # Set for current process
        os.environ["GITHUB_USERNAME"] = github_username
        os.environ["GITHUB_TOKEN"] = github_token
        
        # Write to .env file (absolute path)
        with open(env_path, "w") as env_file:
            env_file.write(f"GITHUB_USERNAME={github_username}\n")
            env_file.write(f"GITHUB_TOKEN={github_token}\n")
            
        print(f"GitHub credentials saved to {env_path}")
        return github_username, github_token
    except Exception as e:
        print(f"Error setting credentials: {e}")
        exit(1)

def ensure_credentials():
    """Ensure credentials exist, prompt if missing"""
    if not os.getenv("GITHUB_USERNAME") or not os.getenv("GITHUB_TOKEN"):
        return set_github_credentials()
    return os.getenv("GITHUB_USERNAME"), os.getenv("GITHUB_TOKEN")