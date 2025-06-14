frappe.ui.form.on("GitHub Settings", {
    refresh(frm) {
        frm.add_custom_button("Get Response", function () {
            frappe.call({
                method: "frappe_code_reviewer.frappe_code_reviewer.doctype.github_settings.github_settings.start_filewise_code_review",
                args: {
                    owner: frm.doc.github_user_name,
                    repo: frm.doc.github_repo_name,
                    token: frm.doc.github_access_token // optional
                },
                callback: function (r) {
                    if (r.message) {
                        frappe.msgprint({
                            title: "Model Response",
                            message: `<div style="max-height: 400px; overflow-y: auto; white-space: pre-wrap;">${r.message}</div>`,
                            indicator: 'green'
                        });
                    } else {
                        frappe.msgprint("⚠️ No response received.");
                    }
                }
            });
        });
    },
});
