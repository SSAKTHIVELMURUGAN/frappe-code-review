# Copyright (c) 2025, Sakthi and contributors
# For license information, please see license.txt

import frappe, json
from frappe.model.document import Document

from frappe_code_reviewer.api.api_call import get_github_access, send_to_ai_model

class CodeReview(Document):
	# def validate(self):
	# 	self.generate_response()

	def on_submit(self):
		self.generate_response()

	def generate_response(self):
		link, token, code_data = get_github_access()
		print("code dataa", code_data)
		import json
		print("Generating response...")
		self.github_repo_response = json.dumps(code_data, indent=2)
		results = send_to_ai_model(code_data)
		print("Results:", results)
		doc = frappe.new_doc("Code Review Response")
		doc.response = json.dumps(results, indent=2)
		doc.save()



