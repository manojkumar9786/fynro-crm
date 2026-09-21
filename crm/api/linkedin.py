import hashlib
import hmac
import json

import frappe
import requests
from werkzeug.wrappers import Response

def setup_doctype():
    doctype_name = 'LinkedIn Integration Settings'
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
                    'label': 'Verify Token / Challenge Secret'
                },
                {
                    'fieldname': 'client_id',
                    'fieldtype': 'Data',
                    'label': 'Client ID'
                },
                {
                    'fieldname': 'client_secret',
                    'fieldtype': 'Password',
                    'label': 'Client Secret'
                },
                {
                    'fieldname': 'access_token',
                    'fieldtype': 'Password',
                    'label': 'Access Token'
                }
            ]
        })
        doc.insert(ignore_permissions=True)
        print('Created LinkedIn Integration Settings')
    else:
        print('LinkedIn Integration Settings already exists')

    custom_fields = [
        {
            'fieldname': 'linkedin_lead_id',
            'fieldtype': 'Data',
            'label': 'LinkedIn Lead ID',
            'insert_after': 'facebook_form_id',
            'unique': 1
        },
        {
            'fieldname': 'linkedin_form_id',
            'fieldtype': 'Data',
            'label': 'LinkedIn Form ID',
            'insert_after': 'linkedin_lead_id'
        }
    ]

    for field in custom_fields:
        if not frappe.db.exists('Custom Field', f"CRM Lead-{field['fieldname']}"):
            frappe.get_doc({
                'doctype': 'Custom Field',
                'dt': 'CRM Lead',
                'fieldname': field['fieldname'],
                'fieldtype': field['fieldtype'],
                'label': field['label'],
                'insert_after': field['insert_after'],
                'unique': field.get('unique', 0)
            }).insert(ignore_permissions=True)
            print(f"Created custom field {field['fieldname']}")
    
    frappe.db.commit()

def _get_client_secret():
    settings = frappe.get_single('LinkedIn Integration Settings')
    return settings.get_password('client_secret', raise_exception=False)


@frappe.whitelist(allow_guest=True)
def webhook():
    if frappe.request.method == 'GET':
        challenge_code = frappe.request.args.get('challengeCode')
        client_secret = _get_client_secret()
        if not challenge_code or not client_secret:
            return Response('Verification failed', status=403, mimetype='text/plain')
        challenge_response = hmac.new(
            client_secret.encode(), challenge_code.encode(), hashlib.sha256
        ).hexdigest()
        return Response(
            json.dumps({'challengeCode': challenge_code, 'challengeResponse': challenge_response}),
            status=200,
            mimetype='application/json',
        )
            
    if frappe.request.method == 'POST':
        raw = frappe.request.get_data()
        client_secret = _get_client_secret()
        if not client_secret:
            frappe.log_error(title='LinkedIn Webhook Error', message='Client Secret is not set; request rejected')
            return Response('Not configured', status=403, mimetype='text/plain')
        expected = 'hmacsha256=' + hmac.new(client_secret.encode(), raw, hashlib.sha256).hexdigest()
        received = frappe.request.headers.get('X-LI-Signature', '')
        if not hmac.compare_digest(received, expected):
            frappe.log_error(title='LinkedIn Webhook Error', message='Invalid X-LI-Signature')
            return Response('Invalid signature', status=403, mimetype='text/plain')
        data = raw.decode('utf-8', errors='replace')
        try:
            payload = json.loads(data)
        except Exception:
            return Response('OK', status=200)
        
        if isinstance(payload, list):
            for lead in payload:
                lead_id = lead.get('leadId') or lead.get('id')
                form_id = lead.get('formId')
                if lead_id:
                    frappe.enqueue('crm.api.linkedin.process_lead', lead_id=lead_id, payload=lead, now=False)
        elif isinstance(payload, dict):
            lead_id = payload.get('leadId') or payload.get('id')
            if lead_id:
                frappe.enqueue('crm.api.linkedin.process_lead', lead_id=lead_id, payload=payload, now=False)
            elif payload.get('elements'):
                for lead in payload.get('elements', []):
                    lead_id = lead.get('leadId') or lead.get('id')
                    if lead_id:
                        frappe.enqueue('crm.api.linkedin.process_lead', lead_id=lead_id, payload=lead, now=False)
        return Response('OK', status=200)

def process_lead(lead_id, payload=None):
    if not payload:
        payload = {}
        
    settings = frappe.get_doc('LinkedIn Integration Settings') 
    access_token = settings.get_password('access_token', raise_exception=False)
    
    lead_info = {
        'first_name': 'LinkedIn Lead',
        'linkedin_lead_id': lead_id,
        'linkedin_form_id': payload.get('formId')
    }
    
    status = (
        'New' if frappe.db.exists('CRM Lead Status', 'New')
        else frappe.get_all('CRM Lead Status', {'type': 'Open'}, pluck='name', order_by='position asc', limit=1)[0]
    )
    lead_info['status'] = status
    
    form_resp = payload.get('formResponse', {})
    answers = form_resp.get('answers', [])
    if not answers:
        answers = payload.get('answers', [])
        
    if not answers and access_token:
        import urllib.parse
        encoded_id = urllib.parse.quote(lead_id)
        url = f'https://api.linkedin.com/rest/leadFormResponses/{encoded_id}'
        headers = {
            'Authorization': f'Bearer {access_token}',
            'X-Restli-Protocol-Version': '2.0.0',
            'LinkedIn-Version': '202302'
        }
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            api_data = resp.json()
            answers = api_data.get('formResponse', {}).get('answers', [])
        else:
            frappe.log_error(title='LinkedIn API Error', message=resp.text)
            
    for ans in answers:
        question = str(ans.get('questionName', '')).lower()
        val = ans.get('textResponse', '')
        
        if not val:
            continue
            
        if 'email' in question:
            lead_info['email'] = val
        elif 'first' in question or 'name' in question and 'last' not in question:
            lead_info['first_name'] = val
        elif 'last' in question:
            lead_info['last_name'] = val
        elif 'phone' in question or 'mobile' in question or 'contact' in question:
            lead_info['mobile_no'] = val
        elif 'company' in question or 'organization' in question:
            lead_info['organization'] = val
        elif 'job title' in question or 'position' in question:
            lead_info['job_title'] = val
            
    if frappe.db.exists('CRM Lead', {'linkedin_lead_id': lead_id}):
        return
        
    if not frappe.db.exists('CRM Lead Source', 'LinkedIn'):
        frappe.get_doc({'doctype': 'CRM Lead Source', 'source_name': 'LinkedIn'}).insert(ignore_permissions=True)
    lead_info['source'] = 'LinkedIn'
        
    doc = frappe.get_doc({
        'doctype': 'CRM Lead',
        **lead_info
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
