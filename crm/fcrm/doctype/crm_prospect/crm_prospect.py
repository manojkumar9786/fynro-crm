# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from crm.fcrm.doctype.pipeline_record import PipelineRecord


class CRMProspect(PipelineRecord):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from crm.fcrm.doctype.crm_contacts.crm_contacts import CRMContacts
		from crm.fcrm.doctype.crm_products.crm_products import CRMProducts
		from crm.fcrm.doctype.crm_rolling_response_time.crm_rolling_response_time import CRMRollingResponseTime
		from crm.fcrm.doctype.crm_status_change_log.crm_status_change_log import CRMStatusChangeLog
		from frappe.types import DF

		annual_revenue: DF.Currency
		closed_date: DF.Date | None
		communication_status: DF.Link | None
		company_description: DF.SmallText | None
		contact: DF.Link | None
		contacts: DF.Table[CRMContacts]
		currency: DF.Link | None
		customer: DF.Link | None
		email: DF.Data | None
		exchange_rate: DF.Float
		expected_closure_date: DF.Date | None
		expected_prospect_value: DF.Currency
		facebook: DF.Data | None
		first_name: DF.Data | None
		first_responded_on: DF.Datetime | None
		first_response_time: DF.Duration | None
		gender: DF.Link | None
		middle_name: DF.Data | None
		image: DF.AttachImage | None
		industry: DF.Link | None
		job_title: DF.Data | None
		last_name: DF.Data | None
		last_responded_on: DF.Datetime | None
		last_response_time: DF.Duration | None
		lead: DF.Link | None
		linkedin: DF.Data | None
		lost_notes: DF.Text | None
		lost_reason: DF.Link | None
		mobile_no: DF.Data | None
		naming_series: DF.Literal["CRM-PROSPECT-.YYYY.-"]
		net_total: DF.Currency
		next_step: DF.Data | None
		no_of_employees: DF.Literal["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]
		organization: DF.Data | None
		organization_logo: DF.AttachImage | None
		organization_name: DF.Data | None
		phone: DF.Data | None
		probability: DF.Percent
		products: DF.Table[CRMProducts]
		prospect_name: DF.Data | None
		prospect_owner: DF.Link | None
		prospect_value: DF.Currency
		response_by: DF.Datetime | None
		rolling_responses: DF.Table[CRMRollingResponseTime]
		salutation: DF.Link | None
		sla: DF.Link | None
		sla_creation: DF.Datetime | None
		sla_status: DF.Literal["", "First Response Due", "Rolling Response Due", "Failed", "Fulfilled"]
		source: DF.Link | None
		status: DF.Link
		status_change_log: DF.Table[CRMStatusChangeLog]
		territory: DF.Link | None
		total: DF.Currency
		twitter: DF.Data | None
		website: DF.Data | None
	# end: auto-generated types

	NAME_FIELD = "prospect_name"
	OWNER_FIELD = "prospect_owner"
	STATUS_DOCTYPE = "CRM Prospect Status"
	LABEL = "Prospect"
	TRACK_LOST_REASON = True


@frappe.whitelist()
def convert_to_customer(prospect: str):
	"""Create a Customer carrying every detail of the Prospect. The Prospect owner becomes the Customer owner."""
	from crm.fcrm.doctype.record_conversion import convert_record

	return convert_record("CRM Prospect", prospect, "CRM Customer")
