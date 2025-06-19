# Copyright (c) 2025, Sakthi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from frappe.utils.pdf import get_pdf
from frappe.utils.file_manager import save_file
from frappe.utils import get_url
from frappe import _

class CodeReviewResponse(Document):
    pass

@frappe.whitelist()
def export_review_as_pdf(docname):
    doc = frappe.get_doc("Code Review Response", docname)
    
    if not doc.response:
        frappe.throw(_("No review response found."))

    html = f"""
    <h2 style="text-align: center;">Code Review Summary</h2>
    <hr>
    {doc.response}
    """

    pdf_file = get_pdf(html)
    filename = f"Code_Review_{docname}.pdf"

    filedoc = save_file(
        fname=filename,
        content=pdf_file,
        dt="Code Review Response",
        dn=docname,
        folder="Home/Attachments",
        is_private=0
    )

    return get_url(filedoc.file_url)
