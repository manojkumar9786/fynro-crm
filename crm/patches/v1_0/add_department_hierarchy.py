import json

import frappe

LAYOUT_DOCTYPES = ("CRM Lead", "CRM Prospect", "CRM Customer")

# (layout type, field to insert after, section / column that holds it)
ANCHORS = {
	"Quick Entry": "status",
	"Side Panel": "territory",
	"Data Fields": "territory",
}


def execute():
	frappe.reload_doc("fcrm", "doctype", "crm_department")
	frappe.reload_doc("fcrm", "doctype", "crm_lead_form")
	frappe.reload_doc("fcrm", "doctype", "crm_sales_hierarchy")
	for doctype in ("crm_lead", "crm_prospect", "crm_customer"):
		frappe.reload_doc("fcrm", "doctype", doctype)

	add_department_to_layouts()
	backfill_hierarchy_nodes()


def add_department_to_layouts():
	for doctype in LAYOUT_DOCTYPES:
		for layout_type, anchor in ANCHORS.items():
			name = f"{doctype}-{layout_type}"
			if not frappe.db.exists("CRM Fields Layout", name):
				continue
			layout = json.loads(frappe.db.get_value("CRM Fields Layout", name, "layout") or "[]")
			if _insert_after(layout, anchor, "department"):
				frappe.db.set_value("CRM Fields Layout", name, "layout", json.dumps(layout))


def _insert_after(node, anchor, fieldname) -> bool:
	"""Insert `fieldname` after `anchor` in the first column that has it. False if already present."""
	if _contains(node, fieldname):
		return False
	if isinstance(node, dict):
		fields = node.get("fields")
		if isinstance(fields, list) and anchor in fields:
			fields.insert(fields.index(anchor) + 1, fieldname)
			return True
		return any(_insert_after(v, anchor, fieldname) for v in node.values() if isinstance(v, list | dict))
	if isinstance(node, list):
		return any(_insert_after(v, anchor, fieldname) for v in node if isinstance(v, dict | list))
	return False


def _contains(node, fieldname) -> bool:
	if isinstance(node, dict):
		fields = node.get("fields")
		if isinstance(fields, list) and fieldname in fields:
			return True
		return any(_contains(v, fieldname) for v in node.values() if isinstance(v, list | dict))
	if isinstance(node, list):
		return any(_contains(v, fieldname) for v in node if isinstance(v, dict | list))
	return False


def backfill_hierarchy_nodes():
	"""Existing hierarchy nodes predate Department / Level. Give them a default so they stay valid."""
	nodes = frappe.get_all("CRM Sales Hierarchy", filters={"department": ["is", "not set"]}, fields=["name", "user"])
	if not nodes:
		return

	if not frappe.db.exists("CRM Department", "General"):
		frappe.get_doc({"doctype": "CRM Department", "department_name": "General"}).insert(ignore_permissions=True)

	for node in nodes:
		roles = frappe.get_roles(node.user)
		level = "Manager" if "Sales Manager" in roles else "Agent"
		frappe.db.set_value(
			"CRM Sales Hierarchy",
			node.name,
			{"department": "General", "hierarchy_level": level},
			update_modified=False,
		)
