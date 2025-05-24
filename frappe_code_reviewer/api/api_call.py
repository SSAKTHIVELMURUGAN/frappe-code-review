import requests
import frappe

def get_github_access():
	settings = frappe.get_single("GitHub Settings")
	github_repo_link = settings.github_repo_link
	owner = settings.github_user_name
	repo = settings.github_repo_name
	path = settings.path
	print(f"Path: {path}")
	print(f"Owner: {owner}")
	print(f"Repo: {repo}")

	github_token = settings.get_password("github_access_token")

	# Capture the repo code
	repo_code = get_repo_code(owner=owner, repo=repo, path=path, token=github_token)

	return github_repo_link, github_token, repo_code

def get_repo_code(owner, repo, path, token=None):
	url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
	headers = {}
	if token:
		headers['Authorization'] = f'token {token}'

	try:
		response = requests.get(url, headers=headers)
		response.raise_for_status()
		files = response.json()
		print(f"Files in {path}: {files}")
		code_by_file = {}

		for file in files:
			if file['type'] == 'file' and file['name'].endswith(('.py', '.js', '.html', '.css')):
				file_url = file['download_url']
				file_response = requests.get(file_url)
				if file_response.status_code == 200:
					file_content = file_response.text
					code_by_file[file['path']] = file_content  # Use full path for clarity

			elif file['type'] == 'dir':
				# Recurse into subdirectory
				sub_code = get_repo_code(owner, repo, file['path'], token)

				if sub_code:
					code_by_file.update(sub_code)

		return code_by_file

	except requests.exceptions.RequestException as e:
		print(f"Error during request: {e}")
		return None


def send_to_ai_model(code_by_file):
	results = {}

	print("Sending code to AI model...")
	print("Code by file:", code_by_file)
	for file_path, code in code_by_file.items():
		prompt = f"""
You are a Senior Software Developer reviewing the following file, which is part of a Frappe app project. The file path is: {file_path}

Your tasks:

As a senior developer, review the code and identify any bugs, code smells, bad practices, or potential runtime issues.

Suggest improvements, including:

Refactoring opportunities

Optimization (performance or clarity)

Include corrected or improved code snippets

Explain the logic and structure of the code in technical terms, especially how it fits into the Frappe framework (such as hooks like before_save, before_submit, and DB integrations).

Provide a beginner-friendly explanation of the code — what it does and why it’s useful.

Write full developer documentation that includes:

A concise summary of the code’s purpose

Detailed descriptions of key functions, methods, and variables

An overview of how this code integrates into the Frappe backend system

Create a Mermaid.js sequence diagram using sequenceDiagram format that visually shows the flow and interactions of the code.

At the end, provide a clean, improved version of the full code that follows best practices for clarity, maintainability, and performance — as a senior developer would.


Here is the code:
```python
{code}
"""
		print(f"Sending to AI model for file: {file_path}")
		response = requests.post(
				"http://localhost:11434/api/generate",
				json={
					"model": "qwen3:8b",
        			"prompt": prompt,
					"stream": False	
				}
			)
		result = response.json()["response"]
		print(result)
		results[file_path] = result
	return results



# def review_entire_repo(repo_link, token):
#     files = fetch_repo_files(repo_link, token)
#     for file in files:
#         if file["name"].endswith((".py", ".js", ".html")):
#             raw_code = requests.get(file["download_url"]).text
#             ai_response = send_to_ai_model(raw_code)
#             print(f"Review for {file['name']}:\n", ai_response)
