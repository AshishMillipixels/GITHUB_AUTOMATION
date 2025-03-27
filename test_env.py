from dotenv import load_dotenv
import os
load_dotenv()
print("GITHUB_USERNAME:", os.getenv("GITHUB_USERNAME"))
print("GITHUB_TOKEN:", os.getenv("GITHUB_TOKEN"))