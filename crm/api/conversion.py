import frappe

from crm.fcrm.doctype.record_conversion import convert_record


@frappe.whitelist()
def convert_to_prospect(lead_name):
	return convert_record("CRM Lead", lead_name, "CRM Prospect")


@frappe.whitelist()
def convert_to_customer(lead_name):
	return convert_record("CRM Lead", lead_name, "CRM Customer")
