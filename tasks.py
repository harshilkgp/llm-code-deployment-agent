# tasks.py
import os
import base64
import time
import requests
from github import Github, GithubException, ContentFile
import google.generativeai as genai
from models import TaskRequest

# --- CONFIGURATION ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
g = Github(GITHUB_TOKEN)
github_user = g.get_user()
llm_model = genai.GenerativeModel('gemini-1.5-flash-latest')

# --- 1. LLM INTERACTION ---
def generate_code_from_llm(brief: str, checks: list, attachments: dict) -> tuple[str, str]:
    """
    Generates HTML code and a README file based on the task brief.
    Returns a tuple of (html_code, readme_content).
    """
    code_prompt = f"""
    You are an expert frontend web developer. Your task is to create a complete, self-contained, single-file HTML application.
    - All CSS must be in a single <style> tag in the <head>.
    - All JavaScript must be in a single <script> tag at the end of the <body>.
    - Do not use any external files for CSS or JS unless explicitly asked.
    - The HTML must be well-structured and professional.

    **Project Brief:**
    {brief}

    **File Attachments:**
    The following file contents are available for your use in the JavaScript code. You will need to embed this data directly into your script.
    """
    for name, content in attachments.items():
        prompt_content = content.replace("`", "\\`")
        code_prompt += f"\n- `{name}` data:\n```\n{prompt_content}\n```"

    code_prompt += """
    **Strict Requirements & Checks:**
    The final HTML code MUST satisfy the following checks. Use these as a guide to ensure your code is correct. The page must contain all the specific DOM elements (like IDs and classes) mentioned in the checks.
    """
    for check in checks:
        code_prompt += f"\n- A check will be performed using this JavaScript: `{check}`"

    code_prompt += """
    Provide ONLY the complete HTML code in a single markdown code block. Do not include any explanations, notes, or apologies. Your response should start with ```html and end with ```.
    """
    
    print("🤖 Generating code from LLM...")
    response = llm_model.generate_content(code_prompt)
    html_code = response.text.strip().removeprefix("```html").removesuffix("```").strip()

    readme_prompt = f"""
    Based on the following project brief, write a professional README.md file.

    **Brief:** {brief}

    The README should include these sections:
    - **Project Summary**: A brief overview of the application's purpose.
    - **Setup & Usage**: Explain that this is a single HTML file and can be opened in any web browser.
    - **Code Explanation**: Briefly describe the structure (HTML, CSS, JS).
    - **License**: Mention it is under the MIT License.
    """
    print("🤖 Generating README from LLM...")
    readme_response = llm_model.generate_content(readme_prompt)
    readme_content = readme_response.text.strip()
    
    return html_code, readme_content

# --- 2. GITHUB AND NOTIFICATION ---
def notify_evaluator(url: str, payload: dict):
    """Posts the results back to the evaluation URL with exponential backoff retries."""
    retries = [1, 2, 4, 8]
    for delay in retries:
        try:
            print(f"📡 Notifying evaluator at {url}...")
            response = requests.post(url, json=payload, timeout=15)
            if response.status_code == 200:
                print(f"✅ Successfully notified evaluator. Status: {response.status_code}")
                return
            else:
                print(f"⚠️ Evaluator returned status {response.status_code}. Retrying...")
        except requests.RequestException as e:
            print(f"❌ Error notifying evaluator: {e}. Retrying in {delay}s...")
        time.sleep(delay)
    print(f"⛔️ Failed to notify evaluator after all retries.")

# --- 3. MAIN TASK HANDLER ---
def handle_build_task(request_data: TaskRequest):
    """Orchestrates the entire Round 1 'Build' process."""
    print(f"\n🚀 Starting BUILD task: {request_data.task}")
    
    decoded_attachments = {}
    for att in request_data.attachments:
        header, encoded = att.url.split(",", 1)
        decoded_content = base64.b64decode(encoded).decode('utf-8')
        decoded_attachments[att.name] = decoded_content
    
    html_code, readme_content = generate_code_from_llm(
        request_data.brief, 
        request_data.checks, 
        decoded_attachments
    )
    
    repo_name = f"llm-agent-task-{request_data.task}"
    print(f"⚙️ Creating GitHub repo: {repo_name}")
    try:
        repo = github_user.get_repo(repo_name)
        print("Repo already exists. Deleting for a fresh start.")
        repo.delete()
        time.sleep(2)
    except GithubException as e:
        if e.status != 404: raise 
            
    repo = github_user.create_repo(repo_name, private=False, auto_init=False)
    
    repo.create_file("LICENSE", "feat: Add MIT License", "MIT License\n...", branch="main")
    repo.create_file("README.md", "docs: Create README", readme_content, branch="main")
    commit_info = repo.create_file("index.html", "feat: Add initial application code", html_code, branch="main")
    
    print("🌎 Enabling GitHub Pages...")
    pages_url = f"https://{github_user.login}.github.io/{repo.name}/"
    print(f"✅ Deployment initiated. Pages URL will be: {pages_url}")
    
    payload = {
        "email": request_data.email,
        "task": request_data.task,
        "round": request_data.round,
        "nonce": request_data.nonce,
        "repo_url": repo.html_url,
        "commit_sha": commit_info['commit'].sha,
        "pages_url": pages_url
    }
    notify_evaluator(request_data.evaluation_url, payload)
    print(f"🏁 Finished BUILD task: {request_data.task}\n")

def handle_revise_task(request_data: TaskRequest):
    """Placeholder for Round 2 logic."""
    print(f"\n🚧 REVISE task received for {request_data.task}. Logic not yet implemented.")
    pass