import json

import frappe

LAYOUTS = {
	"CRM Lead-Side Panel": "lead_owner",
	"CRM Lead-Data Fields": "lead_owner",
}
NEW_FIELDS = ["not_interest_lead", "is_ringing_rule_bucket"]


def execute():
	frappe.reload_doc("fcrm", "doctype", "crm_lead")

	for name, anchor in LAYOUTS.items():
		if not frappe.db.exists("CRM Fields Layout", name):
			continue
		layout = json.loads(frappe.db.get_value("CRM Fields Layout", name, "layout") or "[]")
		changed = False
		for fieldname in NEW_FIELDS:
			if _insert_after(layout, anchor, fieldname):
				changed = True
		if changed:
			frappe.db.set_value("CRM Fields Layout", name, "layout", json.dumps(layout))


def _insert_after(node, anchor, fieldname) -> bool:
	"""Insert `fieldname` right after `anchor` in the first column that has it. False if already present."""
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
