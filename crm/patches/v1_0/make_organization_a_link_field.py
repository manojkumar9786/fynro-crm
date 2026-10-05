import frappe

# CRM Organization's autoname is "field:organization_name", so the Data value
# already stored in `organization` on each of these doctypes is exactly the
# name a CRM Organization record for it would have — once one exists.
DOCTYPES = ("CRM Lead", "CRM Prospect", "CRM Customer")


def execute():
	backfill_organizations()

	for doctype in ("crm_lead", "crm_prospect", "crm_customer"):
		frappe.reload_doc("fcrm", "doctype", doctype)

	frappe.db.commit()


def backfill_organizations():
	existing = set(frappe.get_all("CRM Organization", pluck="name"))

	names = set()
	for doctype in DOCTYPES:
		values = frappe.get_all(
			doctype, filters={"organization": ["is", "set"]}, pluck="organization", distinct=True
		)
		names.update(v.strip() for v in values if v and v.strip())

	for name in sorted(names - existing):
		if frappe.db.exists("CRM Organization", name):  # race-safe re-check
			continue
		frappe.get_doc({"doctype": "CRM Organization", "organization_name": name}).insert(
			ignore_permissions=True
		)
