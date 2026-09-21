# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Route incoming leads to a department and to one of its agents.

A lead that carries an ad form id (Facebook / LinkedIn) is mapped to a department
through the `CRM Lead Form` master, then handed to the department's next Agent
(round-robin over the Agents of `CRM Sales Hierarchy`).
"""

import frappe

# CRM Lead field holding the form id -> `CRM Lead Form.platform`
FORM_ID_FIELDS = {
	"facebook_form_id": "Facebook",
	"linkedin_form_id": "LinkedIn",
}


def route_lead(doc, method=None):
	"""`CRM Lead` before_insert hook."""
	form_department = get_department_for_lead(doc)
	if not form_department:
		# Unmapped form / manual lead: keep whatever the creator chose (may be blank)
		return

	if not doc.get("department"):
		doc.department = form_department

	if not doc.get("lead_owner"):
		agent = get_next_agent(doc.department)
		if agent:
			doc.lead_owner = agent


def get_department_for_lead(doc) -> str | None:
	for fieldname, platform in FORM_ID_FIELDS.items():
		form_id = (doc.get(fieldname) or "").strip()
		if not form_id:
			continue
		department = frappe.db.get_value(
			"CRM Lead Form",
			{"platform": platform, "form_id": form_id, "enabled": 1},
			"department",
		)
		if department and frappe.db.get_value("CRM Department", department, "enabled"):
			return department
	return None


def get_next_agent(department: str) -> str | None:
	"""Round-robin over the department's enabled Agents. Returns None if there are none."""
	# Lock the department row so two leads arriving together do not pick the same agent
	last = frappe.db.sql(
		"select last_assigned_user from `tabCRM Department` where name = %s for update",
		department,
	)
	last_user = last[0][0] if last else None

	agents = [
		row.user
		for row in frappe.get_all(
			"CRM Sales Hierarchy",
			filters={"department": department, "hierarchy_level": "Agent"},
			fields=["user"],
			order_by="creation asc, name asc",
		)
		if frappe.db.get_value("User", row.user, "enabled")
	]
	if not agents:
		return None

	next_index = agents.index(last_user) + 1 if last_user in agents else 0
	agent = agents[next_index % len(agents)]
	frappe.db.set_value("CRM Department", department, "last_assigned_user", agent, update_modified=False)
	return agent
