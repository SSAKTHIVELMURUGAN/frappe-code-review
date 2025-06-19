frappe.ui.form.on("GitHub Settings", {
    refresh(frm) {
        frm.add_custom_button("Fetch Files for Review", function () {
            // Show progress
            frappe.show_progress('Starting Code Review...', 10, 100, 'Fetching data from GitHub');

            frappe.call({
                method: "frappe_code_reviewer.frappe_code_reviewer.doctype.github_settings.github_settings.start_filewise_code_review",
                args: {
                    owner: frm.doc.github_user_name,
                    repo: frm.doc.github_repo_name,
                    token: frm.doc.github_access_token // optional
                },
                callback: function (r) {
                    // Hide progress after completion
                    frappe.hide_progress();

                    if (r.message) {
                        frappe.msgprint({
                            title: "Code Review Response",
                            message: `<div style="max-height: 400px; overflow-y: auto; white-space: pre-wrap;">${r.message}</div>`,
                            indicator: 'green'
                        });
                    } else {
                        frappe.msgprint({
                            title: "No Response",
                            message: "⚠️ No response received from the server.",
                            indicator: 'orange'
                        });
                    }
                },
                error: function (err) {
                    // Hide progress in case of error
                    frappe.hide_progress();

                    frappe.msgprint({
                        title: "Error",
                        message: `❌ Something went wrong. Please check the console.`,
                        indicator: 'red'
                    });
                    console.error(err);
                }
            });
        });
    },
});
