import requests
import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class WhatsAppAccount(models.Model):
    _name = 'whatsapp.account'
    _description = 'WhatsApp Account'

    name = fields.Char(string='Account Name', required=True)
    phone_number_id = fields.Char(string='Phone Number ID', required=True)
    whatsapp_business_account_id = fields.Char(string='Business Account ID', required=True)
    access_token = fields.Char(string='Access Token', required=True)
    webhook_verify_token = fields.Char(string='Webhook Verify Token')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('connected', 'Connected')
    ], default='draft', string='Status')

    def action_test_connection(self):
        self.ensure_one()
        if not self.phone_number_id or not self.access_token:
            raise UserError(_("Please enter both Phone Number ID and Access Token."))

        url = f"https://graph.facebook.com/v19.0/{self.phone_number_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                self.state = 'connected'
                # Auto-sync templates right after successful connection!
                if self.whatsapp_business_account_id:
                    self.action_sync_templates_from_meta()

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Success!"),
                        'message': _("WhatsApp API Connected & Templates Synced Successfully!"),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                error_data = response.json().get('error', {})
                error_msg = error_data.get('message', 'Unknown Error')
                raise UserError(_("Meta API Connection Failed:\n%s") % error_msg)

        except requests.exceptions.RequestException as e:
            raise UserError(_("Could not connect to Meta Servers:\n%s") % str(e))

    def action_sync_templates_from_meta(self):
        """ Fetch all existing templates from Meta WABA account and create/update them in Odoo. """
        self.ensure_one()
        if not self.access_token or not self.whatsapp_business_account_id:
            raise UserError(_("Please provide Access Token and WhatsApp Business Account ID (WABA ID)."))

        url = f"https://graph.facebook.com/v19.0/{self.whatsapp_business_account_id}/message_templates"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        params = {
            "limit": 100
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            res_data = response.json()

            if response.status_code != 200:
                error_msg = res_data.get('error', {}).get('message', 'Unknown Error')
                raise UserError(_("Failed to fetch templates from Meta API:\n%s") % error_msg)

            templates_data = res_data.get('data', [])
            template_obj = self.env['whatsapp.template']
            created_count = 0
            updated_count = 0

            for t_data in templates_data:
                template_name = t_data.get('name')
                language = t_data.get('language')
                meta_status = t_data.get('status', '').lower()  # APPROVED, REJECTED, PENDING...

                # Extract Body text from Meta components
                body_text = ""
                for component in t_data.get('components', []):
                    if component.get('type') == 'BODY':
                        body_text = component.get('text', '')
                        break

                # Search if template already exists b-Odoo
                existing = template_obj.search([('name', '=', template_name)], limit=1)

                vals = {
                    'name': template_name,
                    'display_name': template_name.replace('_', ' ').title(),
                    'language_code': language or 'en_US',
                    'body_text': body_text,
                    'state': meta_status if meta_status in ['approved', 'rejected', 'pending'] else 'approved',
                    'account_id': self.id,
                }

                if existing:
                    existing.write(vals)
                    updated_count += 1
                else:
                    template_obj.create(vals)
                    created_count += 1

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Sync Complete!"),
                    'message': _("Synced %s templates (%s created, %s updated).") % (len(templates_data), created_count, updated_count),
                    'sticky': False,
                    'type': 'success',
                }
            }

        except requests.exceptions.RequestException as e:
            raise UserError(_("Meta API Communication Error:\n%s") % str(e))

    def action_create_custom_template_in_meta(self):
        self.ensure_one()
        if not self.access_token or not self.whatsapp_business_account_id:
            raise UserError(_("Please provide Access Token and WhatsApp Business Account ID (WABA ID)."))

        url = f"https://graph.facebook.com/v19.0/{self.whatsapp_business_account_id}/message_templates"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "name": "custom_message",
            "category": "UTILITY",
            "allow_category_change": True,
            "language": "en_US",
            "components": [
                {
                    "type": "BODY",
                    "text": "Hello {{1}}, {{2}}",
                    "example": {
                        "body_text": [
                            ["Customer Name", "This is your order details."]
                        ]
                    }
                }
            ]
        }

        response = requests.post(url, headers=headers, data=json.dumps(payload))
        res_data = response.json()

        if response.status_code == 200:
            template_obj = self.env['whatsapp.template']
            existing = template_obj.search([('name', '=', 'custom_message')], limit=1)
            if not existing:
                template_obj.create({
                    'name': 'custom_message',
                    'display_name': 'Custom Flexible Message',
                    'language_code': 'en_US',
                    'body_text': 'Hello {{1}}, {{2}}',
                    'status': 'approved',
                    'wa_account_id': self.id,
                })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Success!"),
                    'message': _("Template 'custom_message' created successfully in Meta and approved!"),
                    'sticky': False,
                    'type': 'success',
                }
            }
        else:
            error_msg = res_data.get('error', {}).get('message', 'Unknown Error')
            if "already exists" in error_msg.lower():
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Already Exists"),
                        'message': _("Template 'custom_message' already exists in Meta."),
                        'sticky': False,
                        'type': 'warning',
                    }
                }
            raise UserError(_("Meta API Error (%s): %s") % (response.status_code, error_msg))