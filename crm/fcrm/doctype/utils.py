import json

import frappe


def ensure_organization_exists(organization_name, doc=None):
	"""Auto-create a matching CRM Organization so `organization` (a Link field on
	CRM Lead / Prospect / Customer) never breaks when set to a plain company name —
	by domain enrichment, a Facebook/LinkedIn lead, data import, or a user typing a
	new name into the field. `doc` (the record being saved) donates its own
	website/territory/industry/annual_revenue to a newly created Organization,
	mirroring CRM Lead.create_organization()."""
	if not organization_name or frappe.db.exists("CRM Organization", organization_name):
		return

	organization = frappe.new_doc("CRM Organization")
	organization.organization_name = organization_name
	if doc:
		for fieldname in ("website", "territory", "industry", "annual_revenue"):
			if doc.meta.has_field(fieldname) and doc.get(fieldname):
				organization.set(fieldname, doc.get(fieldname))
	organization.insert(ignore_permissions=True)


def add_or_remove_lost_reason_section_in_sidepanel(doc):
	doctype = doc.doctype
	status_doctypes = {
		"CRM Deal": "CRM Deal Status",
		"CRM Lead": "CRM Lead Status",
		"CRM Prospect": "CRM Prospect Status",
	}
	status_doctype = status_doctypes.get(doctype)
	if not status_doctype:
		return

	status = None
	if getattr(doc, "status", None):
		status = frappe.db.get_value(status_doctype, doc.status, "type")
	is_lost = status and status == "Lost"

	layout_doc = frappe.get_doc("CRM Fields Layout", f"{doctype}-Side Panel")
	sections = json.loads(layout_doc.layout)

	lost_reason_section = {
		"name": "lost_reason_section",
		"label": "Lost Reason",
		"opened": True,
		"columns": [
			{
				"name": "lost_reason_column",
				"fields": ["lost_reason", "lost_notes"],
			}
		],
	}

	section_exists = any(section.get("name") == "lost_reason_section" for section in sections)

	if is_lost and not section_exists:
		if sections and sections[0].get("name") == "contacts_section":
			sections = [*sections[:1], lost_reason_section, *sections[1:]]
		else:
			sections = [lost_reason_section, *sections]
		layout_doc.layout = json.dumps(sections)
		layout_doc.save(ignore_permissions=True)
	elif not is_lost and section_exists:
		sections = [section for section in sections if section.get("name") != "lost_reason_section"]
		layout_doc.layout = json.dumps(sections)
		layout_doc.save(ignore_permissions=True)
