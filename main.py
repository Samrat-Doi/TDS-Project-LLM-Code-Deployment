from fastapi import FastAPI, Request, HTTPException
import requests
import os
import base64
import time
#from dotenv import load_dotenv 
import traceback
import json

#load_dotenv() 

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
AIPIPE_API_KEY = os.getenv("AIPIPE_API_KEY") 
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
SECRET = os.getenv("SECRET")

if not all([GITHUB_TOKEN, AIPIPE_API_KEY, GITHUB_USERNAME, SECRET]):
    print("FATAL: Missing one or more essential environment variables.")

task_registry = {}

app = FastAPI()

def validate_secret(secret: str) -> bool:
    return secret == SECRET

def get_repo_info(repo_name: str):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    response = requests.get(f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}", headers=headers)
    if response.status_code == 200:
        print(f"Repository {repo_name} already exists. Using existing one.")
        return response.json()
    return None

def create_github_repo(repo_name: str):
    print(f"Attempting to create or find repository: {repo_name}")
    repo_info = get_repo_info(repo_name)
    if repo_info:
        return repo_info

    payload = {"name": repo_name, "private": False, "auto_init": False, "license_template": "mit"}
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    response = requests.post("https://api.github.com/user/repos", headers=headers, json=payload)

    if response.status_code == 201:
        print(f"Successfully created new repository: {repo_name}")
        return response.json()
    if response.status_code == 422:
        repo_info = get_repo_info(repo_name)
        if repo_info:
            return repo_info
        else:
            raise Exception(f"Repo creation failed (422) AND subsequent GET failed: {response.content.decode('utf-8')}")
    
    raise Exception(f"Failed to create repository with status {response.status_code}: {response.content.decode('utf-8')}")

def enable_github_pages(repo_name: str):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    payload = {"source": {"branch": "main", "path": "/"}}
    
    response = requests.post(f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/pages", headers=headers, json=payload)
    
    if response.status_code not in [201, 409]:
        raise Exception(f"Failed to enable GitHub Pages (Status {response.status_code}): {response.content.decode('utf-8')}")
    
    print(f"GitHub Pages enabled for {repo_name}.")
    
    pages_response = requests.get(f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/pages", headers=headers)
    if pages_response.status_code == 200:
        return pages_response.json().get('html_url')
    
    return f"https://{GITHUB_USERNAME}.github.io/{repo_name}/" 

def get_sha_of_latest_commit(repo_name: str, branch: str = "main") -> str:
    response = requests.get(
        f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/commits/{branch}",
        headers={"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    )
    if response.status_code != 200:
        if response.status_code == 404:
            return None
        raise Exception(f"Failed to get latest commit SHA (Status {response.status_code}): {response.content.decode('utf-8')}")
    return response.json().get("sha")

def push_files_to_repo(repo_name: str, files: list, deployment_round: int):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    
    for file in files:
        file_name = file.get("name")
        file_content = file.get("content")
        
        if isinstance(file_content, bytes):
            content_b64 = base64.b64encode(file_content).decode()
        elif isinstance(file_content, str):
            content_b64 = base64.b64encode(file_content.encode('utf-8')).decode()
        else:
            raise TypeError(f"File content for {file_name} must be bytes or str.")

        payload = {
            "message": f"[Round {deployment_round}] Update {file_name}",
            "content": content_b64,
            "branch": "main" 
        }

        file_info_response = requests.get(
            f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/contents/{file_name}?ref=main",
            headers=headers
        )
        
        if file_info_response.status_code == 200:
            payload["sha"] = file_info_response.json().get("sha")
        
        response = requests.put(
            f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/contents/{file_name}",
            headers=headers,
            json=payload
        )
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to push/update {file_name} (Status {response.status_code}): {response.content.decode('utf-8')}")
        
        print(f"Successfully pushed {file_name}. Commit SHA: {response.json().get('commit', {}).get('sha')}")

def generate_app_code(brief: str, attachments: list):
    system_instruction = (
        "You are an expert software engineer and code generator. "
        "Your only job is to generate a single, complete HTML file (index.html) based on the user's request. "
        "Do NOT include any external explanation, markdown delimiters (```), or comments in the final output. "
        "The output must be the raw, ready-to-use HTML code only."
    )
    user_prompt = (
        f"Generate a minimal, complete, and functional web application as a single index.html file "
        f"based on this brief: '{brief}'. "
        f"Context/Attachments provided: {attachments}. "
        "Ensure the HTML file is valid and complete."
    )
    
    combined_prompt = f"{system_instruction}\n\nUser Request: {user_prompt}"

    if not AIPIPE_API_KEY:
        raise Exception("AIPIPE_API_KEY environment variable is not set.")

    headers = {"Authorization": f"Bearer {AIPIPE_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "openai/gpt-4o-mini", "input": combined_prompt}
    
    aipipe_url = "https://aipipe.org/openrouter/v1/responses"
    print(f"Calling Ai pipe API at {aipipe_url}...")
    
    response = requests.post(aipipe_url, headers=headers, json=payload, timeout=60)
    
    if response.status_code != 200:
        try:
            error_details = response.json().get('error', {})
            error_message = error_details.get('message', f"Unknown error (Status {response.status_code})")
        except json.JSONDecodeError:
            error_message = response.content.decode('utf-8')
        raise Exception(f"Ai pipe API error: {error_message}")
        
    result = response.json()
    
    try:
        code = result['output'][0]['content'][0]['text'].strip()
    except (KeyError, IndexError, TypeError):
        print("ERROR: Could not parse AI response. Received structure:")
        print(json.dumps(result, indent=2))
        raise Exception("Failed to parse generated code from AI response.")

    return code

def generate_readme(data: dict, brief: str) -> str:
    task_name = data['task']
    return f"""# {task_name}

## Summary

This application was automatically generated based on the following brief:
> {brief}

## Setup

This is a static HTML application hosted on GitHub Pages. No setup is required. Simply visit the GitHub Pages URL to view the live application.

## Usage

Open the `index.html` file in your browser or visit the live GitHub Pages link.

## Code Explanation

The application consists of a single `index.html` file. It was generated by an AI model to fulfill the requirements of the project brief.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
"""

def generate_license() -> str:
    return """MIT License

Copyright (c) [2024] [Your Name or GitHub Username]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

def deploy_app(data, deployment_round: int):
    brief = data['brief']
    attachments = data.get('attachments', [])
    
    if deployment_round == 2:
        round2_data = data.get('round2', [])
        if round2_data and isinstance(round2_data, list):
            update_data = round2_data[0] 
            brief = update_data.get('brief', brief)
            if update_data.get('attachments'):
                attachments = update_data['attachments'] 

    task_name = data['task'].replace(' ', '-').lower() 
    repo_name = f"{task_name}_{data['nonce']}" 
    
    create_github_repo(repo_name)
    
    code_str = generate_app_code(brief, attachments)
    readme_content = generate_readme(data, brief)
    license_content = generate_license()

    files = [
        {"name": "index.html", "content": code_str},
        {"name": "README.md", "content": readme_content},
        {"name": "LICENSE", "content": license_content}
    ]
    
    push_files_to_repo(repo_name, files, deployment_round) 
    pages_url = enable_github_pages(repo_name)
    repo_url = f"https://github.com/{GITHUB_USERNAME}/{repo_name}"
    
    return repo_url, pages_url, repo_name

def post_evaluation(data, repo_url, sha, pages_url, round):
    payload = {
        "email": data["email"], "task": data["task"], "round": round, "nonce": data["nonce"],
        "repo_url": repo_url, "commit_sha": sha, "pages_url": pages_url
    }
    headers = {"Content-Type": "application/json"}
    
    evaluation_url = data.get("evaluation_url")
    if not evaluation_url:
         print("CRITICAL: evaluation_url is missing from the request data. Cannot post results.")
         return

    max_retries = 5
    retry_delay = 1

    for attempt in range(max_retries):
        print(f"Posting evaluation for Round {round} to {evaluation_url}... (Attempt {attempt + 1}/{max_retries})")
        try:
            response = requests.post(evaluation_url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                print("Successfully posted evaluation.")
                return
            print(f"Evaluation post failed with status {response.status_code}: {response.content.decode('utf-8')}")
        except requests.exceptions.RequestException as e:
            print(f"Evaluation post failed due to network error: {e}")

        if attempt < max_retries - 1:
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            retry_delay *= 2
    
    print("CRITICAL: All evaluation post attempts failed.")

def handle_round1(data):
    repo_url, pages_url, repo_name = deploy_app(data, deployment_round=1)
    sha = get_sha_of_latest_commit(repo_name)
    task_registry[data['nonce']] = repo_name
    post_evaluation(data, repo_url, sha, pages_url, round=1)

def handle_round2(data):
    nonce = data['nonce']
    known_repo = task_registry.get(nonce)
    
    if known_repo and get_repo_info(known_repo):
        repo_url, pages_url, repo_name = deploy_app(data, deployment_round=2)
        sha = get_sha_of_latest_commit(repo_name)
        post_evaluation(data, repo_url, sha, pages_url, round=2)
    else:
        repo_url, pages_url, repo_name = deploy_app(data, deployment_round=2)
        task_registry[nonce] = repo_name
        print(f"Repo not in registry or deleted. Used/Created repo {repo_name} and deployed.")
        sha = get_sha_of_latest_commit(repo_name)
        post_evaluation(data, repo_url, sha, pages_url, round=2)

@app.post("/handle_task")
async def handle_task(request: Request):
    try:
        data = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format.")

    if not validate_secret(data.get("secret")):
        raise HTTPException(status_code=401, detail="Invalid secret.")
    
    required_keys = ["round", "nonce", "task", "email", "evaluation_url"] 
    if not all(key in data for key in required_keys):
         missing = [key for key in required_keys if key not in data]
         raise HTTPException(status_code=400, detail=f"Missing required data keys: {', '.join(missing)}.")

    try:
        round_number = data.get("round")
        task_name = data['task'].replace(' ', '-').lower() 
        repo_name = f"{task_name}_{data['nonce']}" 

        if round_number == 1:
            handle_round1(data)
            return {"message": "Round 1 completed successfully", "repo_name": repo_name, "status": "success"}
        elif round_number == 2:
            handle_round2(data)
            return {"message": "Round 2 completed successfully", "repo_name": repo_name, "status": "success"}
        else:
            raise HTTPException(status_code=400, detail="Invalid round number. Must be 1 or 2.")
            
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Deployment Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
