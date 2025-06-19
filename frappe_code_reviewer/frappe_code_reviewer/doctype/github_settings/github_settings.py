import frappe
from frappe.model.document import Document
import requests
from base64 import b64decode
import json
import re

class GitHubSettings(Document):
    pass

@frappe.whitelist()
def start_filewise_code_review(owner, repo, token=None, branch='main'):
    try:
        settings = frappe.get_single("GitHub Settings")
        github_token = settings.get_password("github_access_token") or token

        all_files = get_all_files(owner, repo, github_token, branch)
        crr = frappe.new_doc("Code Review Response")
        crr.code_review = ",".join(all_files)
        crr.save()
        frappe.db.commit()
        reviewed_files = []
        skipped_files = []

        for path in all_files:
            file_status = "Skipped"
            file_url = f"https://github.com/{owner}/{repo}/blob/{branch}/{path}"

            if path.endswith(('.py', '.js')):
                content = get_file_content(owner, repo, path, github_token)

                if content:
                    file_status = "From Review"
                    reviewed_files.append(path)

                    log_doc = create_log(
                        api_name="GitHub File Context",
                        api_endpoint=file_url,
                        crr_name=crr.name,
                        api_request_data={"owner": owner, "repo": repo, "file_path": path},
                        api_response=content,
                        api_response_status_code=200
                    )

                    make_response(log_doc, crr.name)
                else:
                    skipped_files.append(path)
                    log_doc = ""
            else:
                skipped_files.append(path)
                log_doc = ""

            crr.append("code_review_file_list", {
                "file_name": path,
                "status": file_status,
                "doc_link": log_doc
            })
       
        crr = frappe.get_doc("Code Review Response", crr.name)
        crr.code_review = ", ".join(reviewed_files)
        crr.skipped_files = ", ".join(skipped_files)
        crr.review_response = crr.response
        crr.workflow_state = "From Review"
        crr.save()
        frappe.db.commit()

        return {
            "status": "success",
            "reviewed_files": reviewed_files,
            "skipped_files": skipped_files
        }

    except Exception as e:
        frappe.log_error(f"Code Review Error: {str(e)}")
        create_log(
            api_name="GitHub Code Review",
            api_endpoint=f"https://github.com/{owner}/{repo}",
            crr_name=crr.name if 'crr' in locals() else None,
            api_request_data={"owner": owner, "repo": repo},
            api_response=str(e),
            api_response_status_code=500
        )
        return {
            "status": "error",
            "message": f"🚫 Error: {str(e)}",
            "reviewed_files": []
        }

def get_all_files(owner, repo, token=None, branch='main'):
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    headers = {"Authorization": f"token {token}"} if token else {}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print("Error fetching repo tree:", res.text)
        return []
    return [item["path"] for item in res.json()["tree"] if item["type"] == "blob"]

def is_skippable(content, file_path):
    file_path = file_path.lower()
    if file_path.startswith("test_") or "/test_" in file_path or file_path.endswith("_test.py") or "test" in file_path:
        return True

    is_python = file_path.endswith(".py")
    is_javascript = file_path.endswith(".js") or file_path.endswith(".ts")

    lines = content.strip().splitlines()
    lines = [line for line in lines if line.strip()]

    if is_python:
        non_comment_lines = [line for line in lines if not line.strip().startswith("#")]
        if len(non_comment_lines) == 1 and re.match(r"^class\s+\w+\s*:\s*pass\s*$", non_comment_lines[0].strip()):
            return True
    elif is_javascript:
        in_block_comment = False
        non_comment_lines = []
        for line in lines:
            line = line.strip()
            if line.startswith("/*"):
                in_block_comment = True
                continue
            elif "*/" in line:
                in_block_comment = False
                continue
            elif in_block_comment or line.startswith("//"):
                continue
            else:
                non_comment_lines.append(line)

        if not non_comment_lines or (len(non_comment_lines) == 1 and re.match(r"^class\s+\w+\s*{\s*}$", non_comment_lines[0])):
            return True
    else:
        return True

    return not non_comment_lines

def get_file_content(owner, repo, path, token=None):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}"} if token else {}
    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        print(f"\u274c Error fetching file {path}")
        return None

    data = res.json()
    if data.get("encoding") == "base64":
        content = b64decode(data["content"]).decode("utf-8")
        if is_skippable(content, path):
            print(f"\u26a0\ufe0f Skipping file {path} (Not meaningful for review)")
            return None
        return content
    else:
        print(f"\u26a0\ufe0f Unsupported encoding for file {path}")
        return None

def create_log(api_name, api_endpoint, crr_name=None, api_request_header=None, api_request_data=None, api_response=None, api_response_status_code=None):
    log_doc = frappe.new_doc("Code Review Log")
    log_doc.api_method = api_name
    log_doc.url = api_endpoint
    if api_request_header:
        log_doc.header = json.dumps(api_request_header, indent=4) if isinstance(api_request_header, dict) else str(api_request_header)

    if api_request_data:
        log_doc.payload = json.dumps(api_request_data, indent=4) if isinstance(api_request_data, dict) else str(api_request_data)

    if api_response:
        log_doc.response = json.dumps(api_response, indent=4) if isinstance(api_response, dict) else str(api_response)

    log_doc.status_code = api_response_status_code
    log_doc.insert(ignore_permissions=True)
    frappe.db.commit()

    if crr_name:
        code_review_doc = frappe.get_doc("Code Review Response", crr_name)
        code_review_doc.append("code_review_file_list", {
            "file_name": log_doc.url,
            "doc_link": log_doc.name
        })
        code_review_doc.save()
        frappe.db.commit()

        frappe.db.set_value("Code Review Log", log_doc.name,"code_review_response",code_review_doc.name )

    return log_doc.name

def make_response(log_doc, crr):
    frappe.enqueue(
        job_name="AI Response",
        method=send_to_model,
        queue='long',
        log_doc=log_doc,
        crr=crr
    )

def send_to_model(log_doc,crr, model_name="gemma3:4b"):
    # 1) Fetch the log, build AI response as before
    doc = frappe.get_doc("Code Review Log", log_doc)
    ai_response = generate_ai_response(doc.response)  # your existing logic

    # 2) Persist the AI response and workflow state directly in the DB
    frappe.db.set_value(
        "Code Review Log", log_doc,
        {
            "ai_response": json.dumps({
                "model": model_name,
                "response": ai_response
            }, indent=2),
            "workflow_state": "Response"
        }
    )

    # 3) Now patch the parent Code Review Response
    existing = frappe.db.get_value("Code Review Response", crr, "response") or ""
    html_output = frappe.utils.markdown(ai_response)
    html_output = (html_output
        .replace("###", "<strong>")
        .replace("**", "<strong>")
        .replace("</strong><strong>", "</strong><br><strong>")
    )
    updated = existing + (f"<hr>{html_output}" if existing else html_output)

    frappe.db.set_value(
        "Code Review Response", crr,
        {
            "response": updated,
            "review_response": updated,
        }
    )

    # 4) Finally, mark the single file‐row in the child table as 'Response'
    #    (bypass loading the parent child‐table in memory)
    frappe.db.sql("""
        UPDATE `tabCode Review File List`
        SET status='Response'
        WHERE parent=%s AND doc_link=%s
    """, (crr, log_doc))


def generate_ai_response(response, model_name="gemma3:4b"):
    from ollama import chat
    from ollama import ChatResponse

    prompt = (
        "You are an expert Python developer familiar with the Frappe Framework.\n\n"
        "Please give a brief review of the following code. Keep it short:\n"
        "1. Short summary.\n"
        "2. Major issues or bad practices (if any).\n"
        "3. Quick suggestions.\n\n"
        f"Code:\n{response[:25000]}"
    )
    response: ChatResponse = chat(model=model_name, messages=[
        {'role': 'assistant', 'content': prompt},
    ])
    ai_response = response.message.content
    return ai_response
