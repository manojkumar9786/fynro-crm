# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Convert a CRM Lead into a CRM Prospect / CRM Customer, and a CRM Prospect into a CRM Customer.

Every field that exists on both doctypes is copied (standard and custom), child tables with the
same row type are copied too, the record's owner and assignees carry over, and the source record
keeps a link to the new one.
"""

import frappe
from frappe import _
from frappe.desk.form.assign_to import _add as assign

NAME_FIELD = {
	"CRM Lead": "lead_name",
	"CRM Prospect": "prospect_name",
	"CRM Customer": "customer_name",
}
OWNER_FIELD = {
	"CRM Lead": "lead_owner",
	"CRM Prospect": "prospect_owner",
	"CRM Customer": "customer_owner",
}
STATUS_DOCTYPE = {
	"CRM Lead": "CRM Lead Status",
	"CRM Prospect": "CRM Prospect Status",
	"CRM Customer": "CRM Customer Status",
}

# Never copied: identity, audit, workflow state and SLA data that belongs to the source record only
SKIP_FIELDS = {
	"name",
	"naming_series",
	"creation",
	"modified",
	"modified_by",
	"owner",
	"idx",
	"docstatus",
	"amended_from",
	"status",
	"lead",
	"prospect",
	"customer",
	"converted",
	"lost_reason",
	"lost_notes",
	"sla",
	"sla_status",
	"sla_creation",
	"response_by",
	"first_response_time",
	"first_responded_on",
	"last_response_time",
	"last_responded_on",
	"communication_status",
	"status_change_log",
	"rolling_responses",
}
LAYOUT_FIELDTYPES = {"Section Break", "Column Break", "Tab Break", "HTML", "Button", "Heading"}
SKIP_CHILD_KEYS = {"name", "parent", "parenttype", "parentfield", "creation", "modified", "modified_by", "owner", "idx", "docstatus", "doctype"}


def convert_record(source_doctype: str, source_name: str, target_doctype: str) -> str:
	"""Create `target_doctype` from the source record and return its name. Idempotent."""
	link_field = target_doctype.split()[1].lower()  # "prospect" / "customer"

	if not frappe.has_permission(source_doctype, "write", source_name):
		frappe.throw(
			_("Not allowed to convert {0} {1}").format(_(source_doctype), source_name), frappe.PermissionError
		)

	existing = frappe.db.get_value(source_doctype, source_name, link_field)
	if existing and frappe.db.exists(target_doctype, existing):
		return existing

	source = frappe.get_doc(source_doctype, source_name)
	target = frappe.new_doc(target_doctype)

	copy_fields(source, target)

	# The person's full name lives in a differently named field on each doctype
	target.set(NAME_FIELD[target_doctype], source.get(NAME_FIELD[source_doctype]))

	# Whoever owned the source owns the new record
	assignees = [user for user in (source.get_assigned_users() or []) if user]
	owner = source.get(OWNER_FIELD[source_doctype]) or (assignees[0] if assignees else None)
	target.set(OWNER_FIELD[target_doctype], owner or frappe.session.user)

	target.status = get_default_status(target_doctype)

	# Keep the trail back to the lead (a prospect converted to a customer inherits the prospect's lead)
	origin_lead = source_name if source_doctype == "CRM Lead" else source.get("lead")
	if origin_lead and target.meta.has_field("lead"):
		target.lead = origin_lead

	target.insert(ignore_permissions=True)

	# Everyone who was assigned to the source stays assigned
	for user in assignees:
		if user != target.get(OWNER_FIELD[target_doctype]):
			assign({"assign_to": [user], "doctype": target_doctype, "name": target.name}, ignore_permissions=True)

	mark_converted(source_doctype, source_name, target_doctype, target.name, origin_lead)
	return target.name


def copy_fields(source, target):
	target_meta = target.meta
	for field in source.meta.fields:
		fieldname = field.fieldname
		if fieldname in SKIP_FIELDS or field.fieldtype in LAYOUT_FIELDTYPES:
			continue
		target_field = target_meta.get_field(fieldname)
		if not target_field or target_field.fieldtype != field.fieldtype:
			continue

		if field.fieldtype in ("Table", "Table MultiSelect"):
			if target_field.options != field.options:
				continue
			for row in source.get(fieldname) or []:
				target.append(fieldname, {k: v for k, v in row.as_dict().items() if k not in SKIP_CHILD_KEYS})
			continue

		value = source.get(fieldname)
		if value not in (None, ""):
			target.set(fieldname, value)


def get_default_status(doctype: str) -> str | None:
	status_doctype = STATUS_DOCTYPE[doctype]
	if frappe.db.exists(status_doctype, "Active"):
		return "Active"
	statuses = frappe.get_all(status_doctype, {"type": "Open"}, pluck="name", order_by="position asc", limit=1)
	return statuses[0] if statuses else None


def mark_converted(source_doctype, source_name, target_doctype, target_name, origin_lead):
	link_field = target_doctype.split()[1].lower()

	if source_doctype == "CRM Lead":
		values = {link_field: target_name, "converted": 1}
		converted_status = "Converted" if frappe.db.exists("CRM Lead Status", "Converted") else "Qualified"
		if frappe.db.exists("CRM Lead Status", converted_status):
			values["status"] = converted_status
		frappe.db.set_value("CRM Lead", source_name, values)
	elif source_doctype == "CRM Prospect":
		values = {link_field: target_name}
		if frappe.db.exists("CRM Prospect Status", "Converted"):
			values["status"] = "Converted"
		frappe.db.set_value("CRM Prospect", source_name, values)
		# The lead that started the chain also points at the customer
		if origin_lead and frappe.db.exists("CRM Lead", origin_lead):
			frappe.db.set_value("CRM Lead", origin_lead, {link_field: target_name, "converted": 1})
