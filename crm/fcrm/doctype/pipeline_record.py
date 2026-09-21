# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Shared controller for the person-centric CRM records that follow a Lead
(CRM Prospect and CRM Customer), so they behave like a CRM Lead."""

import frappe
from frappe import _
from frappe.desk.form.assign_to import _add as assign
from frappe.model.document import Document
from frappe.utils import validate_email_address

from crm.fcrm.doctype.utils import add_or_remove_lost_reason_section_in_sidepanel


class PipelineRecord(Document):
	# Set by the concrete doctype
	NAME_FIELD = ""  # e.g. "prospect_name"
	OWNER_FIELD = ""  # e.g. "prospect_owner"
	STATUS_DOCTYPE = ""  # e.g. "CRM Prospect Status"
	LABEL = ""  # e.g. "Prospect"
	TRACK_LOST_REASON = False

	def validate(self):
		self.validate_status()
		self.set_full_name()
		self.set_record_name()
		self.validate_email()
		if self.TRACK_LOST_REASON:
			self.validate_lost_reason()
		owner = self.get(self.OWNER_FIELD)
		if not self.is_new() and self.has_value_changed(self.OWNER_FIELD) and owner:
			self.share_with_agent(owner)
			self.assign_agent(owner)

	def after_insert(self):
		owner = self.get(self.OWNER_FIELD)
		if owner:
			if owner != frappe.session.user:
				self.share_with_agent(owner)
			self.assign_agent(owner)

	def validate_status(self):
		if self.is_new() and not self.status:
			statuses = frappe.get_all(self.STATUS_DOCTYPE, {"type": "Open"}, pluck="name", order_by="position asc")
			if statuses:
				self.status = statuses[0]

	def set_full_name(self):
		if self.first_name:
			self.set(
				self.NAME_FIELD,
				" ".join(
					name
					for name in [self.salutation, self.first_name, self.middle_name, self.last_name]
					if name
				),
			)

	def set_record_name(self):
		if not self.get(self.NAME_FIELD):
			if not self.organization and not self.email and not self.flags.ignore_mandatory:
				frappe.throw(_("A {0} requires either a person's name or an organization's name").format(self.LABEL))
			elif self.organization:
				self.set(self.NAME_FIELD, self.organization)
			elif self.email:
				self.set(self.NAME_FIELD, self.email.split("@")[0])
			else:
				self.set(self.NAME_FIELD, f"Unnamed {self.LABEL}")

	def validate_email(self):
		if self.email:
			if not self.flags.ignore_email_validation:
				validate_email_address(self.email, throw=True)

			if self.email == self.get(self.OWNER_FIELD):
				frappe.throw(_("{0} Owner cannot be same as the {0} Email Address").format(self.LABEL))

	def validate_lost_reason(self):
		if self.status and frappe.get_cached_value(self.STATUS_DOCTYPE, self.status, "type") == "Lost":
			if not self.lost_reason:
				frappe.throw(
					_("Please specify a reason for losing the {0}.").format(self.LABEL.lower()),
					frappe.ValidationError,
				)
			elif self.lost_reason == "Other" and not self.lost_notes:
				frappe.throw(
					_("Please specify the reason for losing the {0}.").format(self.LABEL.lower()),
					frappe.ValidationError,
				)
		if self.has_value_changed("status"):
			add_or_remove_lost_reason_section_in_sidepanel(self)

	def assign_agent(self, agent):
		if not agent:
			return

		if agent in (self.get_assigned_users() or []):
			return

		assign({"assign_to": [agent], "doctype": self.doctype, "name": self.name}, ignore_permissions=True)

	def share_with_agent(self, agent):
		if not agent:
			return

		docshares = frappe.get_all(
			"DocShare",
			filters={"share_name": self.name, "share_doctype": self.doctype},
			fields=["name", "user"],
		)

		shared_with = [d.user for d in docshares] + [agent]

		for user in shared_with:
			if user == agent and not frappe.db.exists(
				"DocShare",
				{"user": agent, "share_name": self.name, "share_doctype": self.doctype},
			):
				frappe.share.add_docshare(
					self.doctype,
					self.name,
					agent,
					write=1,
					flags={"ignore_share_permission": True},
				)
			elif user != agent:
				frappe.share.remove(
					self.doctype,
					self.name,
					user,
					flags={"ignore_share_permission": True, "ignore_permissions": True},
				)

	@classmethod
	def default_list_data(cls):
		columns = [
			{"label": "Full Name", "type": "Data", "key": cls.NAME_FIELD, "width": "12rem"},
			{
				"label": "Organization",
				"type": "Link",
				"key": "organization",
				"options": "CRM Organization",
				"width": "10rem",
			},
			{
				"label": "Status",
				"type": "Link",
				"options": cls.STATUS_DOCTYPE,
				"key": "status",
				"width": "8rem",
			},
			{"label": "Email", "type": "Data", "key": "email", "width": "12rem"},
			{"label": "Mobile No.", "type": "Data", "key": "mobile_no", "width": "11rem"},
			{"label": "Assigned To", "type": "Text", "key": "_assign", "width": "10rem"},
			{"label": "Last Modified", "type": "Datetime", "key": "modified", "width": "8rem"},
		]
		rows = [
			"name",
			cls.NAME_FIELD,
			"organization",
			"status",
			"email",
			"mobile_no",
			cls.OWNER_FIELD,
			"first_name",
			"modified",
			"_assign",
			"image",
		]
		return {"columns": columns, "rows": rows}

	@classmethod
	def default_kanban_settings(cls):
		return {
			"column_field": "status",
			"title_field": cls.NAME_FIELD,
			"kanban_fields": '["organization", "email", "mobile_no", "_assign", "modified"]',
		}
