# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.nestedset import NestedSet, update_nsm


# Lower rank = higher in the tree
LEVEL_RANK = {"Manager": 0, "Team Lead": 1, "Agent": 2}


class CRMSalesHierarchy(NestedSet):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		department: DF.Link
		enabled: DF.Check
		full_name: DF.Data | None
		hierarchy_level: DF.Literal["Manager", "Team Lead", "Agent"]
		is_group: DF.Check
		lft: DF.Int
		old_parent: DF.Link | None
		reports_to: DF.Link | None
		rgt: DF.Int
		user: DF.Link | None
	# end: auto-generated types

	nsm_parent_field = "reports_to"

	def on_update(self):
		update_nsm(self)
		frappe.cache.delete_value("crm_sales_hierarchy_subtree")

	def validate(self):
		if self.user:
			# Ensure the same user is not mapped to two different nodes
			existing = frappe.db.get_value(
				"CRM Sales Hierarchy",
				{"user": self.user, "name": ["!=", self.name]},
				"name",
			)
			if existing:
				frappe.throw(
					frappe._("User {0} is already mapped to hierarchy node {1}.").format(self.user, existing)
				)

		self.validate_department_and_level()

		# A node with reports_to becomes a child so its parent must be a group
		if self.reports_to and not frappe.db.get_value("CRM Sales Hierarchy", self.reports_to, "is_group"):
			frappe.db.set_value("CRM Sales Hierarchy", self.reports_to, "is_group", 1)

	def validate_department_and_level(self):
		if not self.department:
			frappe.throw(frappe._("Department is mandatory for a hierarchy node."))
		if self.hierarchy_level not in LEVEL_RANK:
			frappe.throw(frappe._("Level must be one of Manager, Team Lead or Agent."))

		rank = LEVEL_RANK[self.hierarchy_level]

		if self.reports_to:
			parent = frappe.db.get_value(
				"CRM Sales Hierarchy",
				self.reports_to,
				["department", "hierarchy_level", "user"],
				as_dict=True,
			)
			if self.hierarchy_level == "Manager":
				frappe.throw(frappe._("A Manager is at the top of a department and cannot report to anyone."))
			if parent.department != self.department:
				frappe.throw(
					frappe._("{0} belongs to department {1}, so this node must be in the same department.").format(
						parent.user, parent.department
					)
				)
			if LEVEL_RANK.get(parent.hierarchy_level, 99) >= rank:
				frappe.throw(
					frappe._("A {0} cannot report to a {1}.").format(self.hierarchy_level, parent.hierarchy_level)
				)

		# Existing reports must stay valid after a level / department change
		if not self.is_new():
			children = frappe.get_all(
				"CRM Sales Hierarchy",
				{"reports_to": self.name},
				["user", "department", "hierarchy_level"],
			)
			for child in children:
				if child.department != self.department or LEVEL_RANK.get(child.hierarchy_level, 99) <= rank:
					frappe.throw(
						frappe._(
							"{0} ({1}, {2}) reports to this node. Move them before changing the department or level."
						).format(child.user, child.hierarchy_level, child.department)
					)

	def on_trash(self):
		frappe.cache.delete_value("crm_sales_hierarchy_subtree")


def on_doctype_update():
	frappe.db.add_index("CRM Sales Hierarchy", ["lft", "rgt"])
	frappe.db.add_index("CRM Sales Hierarchy", ["user"])
