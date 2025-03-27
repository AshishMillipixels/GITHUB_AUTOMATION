## GitHub Automation CLI

 **command-line automation tool**

---

##  Features & Usage

###  **1. Create a New GitHub Repository**
- **Command:**  
  ```bash
  python3 main.py create-repo repo_name
### **2. Initialize a Local Git Repository**
- **Command:**
     ```bash
     python3 main.py init ./repo_path

###  **3. Create & Switch Branches**
- **Command:**  
  ```bash
  python3 main.py branch ./repo_path new-feature

###  **4 Generate a .gitignore File**
- **Command:**  
  ```bash
  python3 main.py generate-gitignore ./repo_path


###  **5. Add & Commit Changes**
- **Command:**  
  ```bash
  python3 main.py commit ./repo_path "Added new feature"

###  **6.  Push Changes to GitHub**
- **Command:**  
  ```bash
  python3 main.py push ./repo_path origin main

###  **7.  Merge Branches**
- **Command:**  
  ```bash
  python3 main.py merge ./repo_path feature-branch main

###  **8.  Merge Branches**
- **Command:**  
  ```bash
  python3 main.py pr ./repo_path feature-branch "Merging feature-branch into main"





