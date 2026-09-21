# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class CRMLeadForm(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		department: DF.Link
		enabled: DF.Check
		form_id: DF.Data
		form_name: DF.Data | None
		platform: DF.Literal["Facebook", "LinkedIn"]
	# end: auto-generated types

	def validate(self):
		self.form_id = (self.form_id or "").strip()
