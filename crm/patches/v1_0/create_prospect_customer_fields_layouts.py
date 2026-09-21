from crm.install import add_default_fields_layout


def execute():
	# Creates the Quick Entry, Side Panel and Data Fields layouts for CRM Prospect
	# and CRM Customer. Existing layouts are left untouched.
	add_default_fields_layout()
