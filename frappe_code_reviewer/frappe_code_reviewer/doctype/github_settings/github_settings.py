# Copyright (c) 2025, Sakthi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import requests
from base64 import b64decode
import json

class GitHubSettings(Document):
    pass

@frappe.whitelist()
def start_filewise_code_review(owner, repo, token=None, branch='main'):
    try:
        settings = frappe.get_single("GitHub Settings")
        github_token = settings.get_password("github_access_token") or token

        all_files = get_all_files(owner, repo, github_token, branch)

        reviewed_files = []

        for path in all_files:
            if path.endswith(('.py', '.js', '.md', '.txt', '.html', '.css')):
                content = get_file_content(owner, repo, path, github_token)
                if content:
                    file_url = f"https://github.com/{owner}/{repo}/blob/{branch}/{path}"

                    # Log raw file content
                    create_log(
                        api_name="GitHub File Context",
                        api_endpoint=file_url,
                        api_request_data={"owner": owner, "repo": repo, "file_path": path},
                        api_response=content[:3000],
                        api_response_status_code=200
                    )

                    # Send to model (each file separately)
                    review_response = send_to_model(content)

                    # Log model response
                    create_log(
                        api_name="GitHub Code Review",
                        api_endpoint=file_url,
                        api_request_data={"owner": owner, "repo": repo, "file_path": path},
                        api_response=review_response,
                        api_response_status_code=200
                    )

                    reviewed_files.append({
                        "file_path": path,
                        "review": review_response
                    })

        return {
            "status": "success",
            "message": "File-wise review completed.",
            "reviewed_files": reviewed_files
        }

    except Exception as e:
        frappe.log_error(f"Code Review Error: {str(e)}")
        create_log(
            api_name="GitHub Code Review",
            api_endpoint=f"https://github.com/{owner}/{repo}",
            api_request_data={"owner": owner, "repo": repo},
            api_response=str(e),
            api_response_status_code=500
        )
        return {
            "status": "error",
            "message": f"🚫 Error: {str(e)}",
            "reviewed_files": []
        }

# Fetch all file paths in repo
def get_all_files(owner, repo, token=None, branch='main'):
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    headers = {"Authorization": f"token {token}"} if token else {}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print("Error fetching repo tree:", res.text)
        return []
    return [item["path"] for item in res.json()["tree"] if item["type"] == "blob"]

# Fetch content of one file
def get_file_content(owner, repo, path, token=None):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}"} if token else {}
    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        print(f"Error fetching file {path}")
        return None

    data = res.json()
    if data.get("encoding") == "base64":
        return b64decode(data["content"]).decode("utf-8")
    return None

# Send context to model
def send_to_model(context,model_name="gemma3:27b-it-fp16"):
    from ollama import Client
    prompt = (
        "You are a highly experienced Python developer and expert in the Frappe Framework.\n\n"
        "Please analyze the following source code from a custom Frappe app. This code may include elements like DocTypes, Python controllers, server scripts, API endpoints, hooks, and frontend integrations (JS/HTML).\n\n"
        "Your task:\n"
        "1. Provide a brief summary of the code’s purpose.\n"
        "2. Identify any potential bugs, misconfigurations, or bad practices (specific to Frappe).\n"
        "3. Suggest improvements for performance, security, and maintainability.\n"
        "4. Highlight any missing or inefficient Frappe conventions (e.g., missing permission checks, incorrect use of `frappe.db`, not using `frappe.get_doc`, etc.).\n\n"
        "Here is the code:\n\n"
        f"{context[:25000]}"
    )
    print("Generating model response...")
    # client = Client(hos/t='')
    data = {
        "model":model_name,
        "messages":[{"role": "user", "content": prompt}],
        "stream":False
    }
    url = 'http://localhost:11434/api/chat'
    response = requests.post(url, json=data)
    response_json = json.loads(response.text)
    ai_reply = response_json['message']['content']
    return ai_reply

# Create log in "Code Review" doctype
def create_log(
    api_name,
    api_endpoint,
    api_request_header=None,
    api_request_data=None,
    api_response=None,
    api_response_status_code=None,
):
    log_doc = frappe.new_doc("Code Review")
    log_doc.api_method = api_name
    log_doc.url = api_endpoint

    if api_request_header:
        log_doc.header = (
            json.dumps(api_request_header, indent=4)
            if isinstance(api_request_header, dict)
            else str(api_request_header)
        )

    if api_request_data:
        log_doc.payload = (
            json.dumps(api_request_data, indent=4)
            if isinstance(api_request_data, dict)
            else str(api_request_data)
        )

    if api_response:
        log_doc.response = (
            json.dumps(api_response, indent=4)
            if isinstance(api_response, dict)
            else str(api_response)
        )

    log_doc.status_code = api_response_status_code
    log_doc.insert(ignore_permissions=True)
    frappe.db.commit()

