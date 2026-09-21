import hashlib
import hmac
import json
import re

import frappe
import requests
from werkzeug.wrappers import Response

def setup_doctype():
    doctype_name = 'Facebook Integration Settings'
    if not frappe.db.exists('DocType', doctype_name):
        doc = frappe.get_doc({
            'doctype': 'DocType',
            'name': doctype_name,
            'module': 'FCRM',
            'custom': 1,
            'issingle': 1,
            'fields': [
                {
                    'fieldname': 'verify_token',
                    'fieldtype': 'Data',
                    'label': 'Verify Token (for Webhook)'
                },
                {
                    'fieldname': 'page_access_token',
                    'fieldtype': 'Password',
                    'label': 'Page Access Token'
                },
                {
                    'fieldname': 'app_secret',
                    'fieldtype': 'Password',
                    'label': 'App Secret (for webhook signature check)'
                }
            ]
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print('Created Facebook Integration Settings Document.')
    else:
        print('Facebook Integration Settings already exists.')

@frappe.whitelist(allow_guest=True)
def webhook():
    # Webhook Verification (GET request)
    if frappe.request.method == 'GET':
        hub_mode = frappe.request.args.get('hub.mode')
        hub_challenge = frappe.request.args.get('hub.challenge')
        hub_verify_token = frappe.request.args.get('hub.verify_token')
        
        settings = frappe.get_single('Facebook Integration Settings')
        
        expected_token = settings.verify_token
        if (
            hub_mode == 'subscribe'
            and expected_token
            and hub_verify_token
            and hmac.compare_digest(str(hub_verify_token), str(expected_token))
        ):
            return Response(hub_challenge, status=200, mimetype='text/plain')
        else:
            return Response('Verification failed', status=403, mimetype='text/plain')
            
    # Webhook Event (POST request)
    if frappe.request.method == 'POST':
        frappe.log_error("test")
        raw = frappe.request.get_data()
        settings = frappe.get_single('Facebook Integration Settings')
        app_secret = settings.get_password('app_secret', raise_exception=False)
        if app_secret:
            received = frappe.request.headers.get('X-Hub-Signature-256', '')
            expected = 'sha256=' + hmac.new(app_secret.encode(), raw, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(received, expected):
                frappe.log_error(title='FB Webhook Error', message='Invalid X-Hub-Signature-256')
                return Response('Invalid signature', status=403, mimetype='text/plain')
        else:
            frappe.log_error(
                title='FB Webhook Warning',
                message='App Secret is not set in Facebook Integration Settings; webhook payloads are not verified',
            )
        data = raw.decode('utf-8', errors='replace')
        try:
            payload = json.loads(data)
        except Exception:
            return Response('OK', status=200)
        
        if payload.get('object') == 'page':
            for entry in payload.get('entry', []):
                for change in entry.get('changes', []):
                    if change.get('field') == 'leadgen':
                        value = change.get('value', {})
                        leadgen_id = value.get('leadgen_id')
                        form_id = value.get('form_id')
                        if leadgen_id:
                            frappe.enqueue('crm.api.facebook.process_lead', leadgen_id=leadgen_id, form_id=form_id, now=False)
        
        return Response('OK', status=200)

def process_lead(leadgen_id, form_id):
    settings = frappe.get_doc('Facebook Integration Settings')
    access_token = settings.get_password('page_access_token', raise_exception=False)
    
    if not access_token:
        frappe.log_error(title='FB Integration Error', message='Page Access Token not set in settings')
        return
        
    # The token goes in `params` (not a local URL string) so it never shows up in error-log tracebacks
    response = requests.get(
        f'https://graph.facebook.com/v23.0/{leadgen_id}',
        params={'access_token': access_token},
        timeout=30,
    )
    
    if response.status_code == 200:
        lead_data = response.json()
        field_data = lead_data.get('field_data', [])
        
        # Get a default status
        status = (
            'New' if frappe.db.exists('CRM Lead Status', 'New')
            else frappe.get_all('CRM Lead Status', {'type': 'Open'}, pluck='name', order_by='position asc', limit=1)[0]
        )
        
        lead_info = {
            'first_name': 'FB Lead',
            'status': status,
            'source': 'Facebook',
            'facebook_lead_id': leadgen_id,
            'facebook_form_id': form_id
        }
        
        for field in field_data:
            name = field.get('name')
            values = field.get('values', [])
            val = values[0] if values else ''
            # Frappe strips HTML-like text from Data fields (Facebook's test leads send values such as
            # "<test lead: dummy data for full_name>"), which would leave mandatory fields empty.
            val = re.sub(r'<[^>]*>', '', str(val)).strip()
            
            if name == 'email':
                lead_info['email'] = val
            elif name in ['first_name', 'full_name']:
                lead_info['first_name'] = val
            elif name == 'last_name':
                lead_info['last_name'] = val
            elif name == 'phone_number':
                lead_info['mobile_no'] = val
            elif name == 'company_name':
                lead_info['organization'] = val
        
        # First Name is mandatory on CRM Lead: fall back to the email's local part
        if not lead_info.get('first_name') or lead_info['first_name'] == 'FB Lead':
            email = lead_info.get('email')
            lead_info['first_name'] = email.split('@')[0] if email else 'Facebook Lead'

        # Check if already exists
        if frappe.db.exists('CRM Lead', {'facebook_lead_id': leadgen_id}):
            return
            
        doc = frappe.get_doc({
            'doctype': 'CRM Lead',
            **lead_info
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
    else:
        frappe.log_error(title='FB Graph API Error', message=response.text)

