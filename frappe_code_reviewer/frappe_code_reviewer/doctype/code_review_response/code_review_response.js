frappe.ui.form.on("Code Review Response", {
    refresh(frm) {
        frm.add_custom_button("Download Review as PDF", () => {
            frappe.call({
                method: "frappe_code_reviewer.frappe_code_reviewer.doctype.code_review_response.code_review_response.export_review_as_pdf",
                args: {
                    docname: frm.doc.name
                },
                callback(r) {
                    if (r.message) {
                        window.open(r.message); // Opens the PDF URL
                    }
                }
            });
        });
    }
});
