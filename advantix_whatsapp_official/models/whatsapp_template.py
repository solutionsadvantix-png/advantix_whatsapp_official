import re
import json
import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class WhatsAppTemplate(models.Model):
    _name = 'whatsapp.template'
    _description = 'WhatsApp Message Template'

    name = fields.Char(string='Template API Name', required=True, help="Lower_case_with_underscores only")
    display_name = fields.Char(string='Display Name', required=True)
    account_id = fields.Many2one('whatsapp.account', string='WhatsApp Account', required=False)

    language_code = fields.Selection([
        ('en_US', 'English (US)'),
        ('ar', 'Arabic'),
        ('fr_FR', 'French'),
    ], string='Language', default='en_US', required=True)

    category = fields.Selection([
        ('UTILITY', 'Utility'),
        ('MARKETING', 'Marketing'),
        ('AUTHENTICATION', 'Authentication'),
    ], string='Category', default='UTILITY', required=True)

    body_text = fields.Text(string='Template Body', required=True,
                            help="Example: Hello {{object.partner_id.name}}, order {{object.name}}")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_review', 'In Review'),
        ('approved', 'Approved'),
        ('failed', 'Failed'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', readonly=True)

    model_id = fields.Many2one('ir.model', string='Applies to Model', ondelete='cascade')
    model = fields.Char(related='model_id.model', index=True, store=True)

    def _get_real_sample_value(self, field_path):
        """
        Smart Extractor: Jib real sample value min awwal record bi-l-database (e.g. sale.order)
        """
        if not self.model:
            return "Sample"

        try:
            # Search for the first sample record in target model
            sample_record = self.env[self.model].search([], limit=1)
            if not sample_record:
                return "Sample"

            # Clean field path min 'object.' prefix
            clean_path = field_path.strip()
            if clean_path.startswith("object."):
                clean_path = clean_path.replace("object.", "", 1)

            # Resolve nested path (e.g., partner_id.name)
            val = sample_record
            for path_part in clean_path.split('.'):
                if hasattr(val, path_part):
                    val = getattr(val, path_part)
                else:
                    val = False
                    break

            if val:
                # Handle Many2one or display_name
                if hasattr(val, 'display_name'):
                    return str(val.display_name)
                return str(val)
        except Exception:
            pass

        return "Sample"

    def _format_body_for_meta(self, text):
        if not text:
            return "", []

        # 1. تنظيف المسافات قبل علامات الترقيم (مثل " ! " أو " . ")
        clean_text = re.sub(r'\s+([!.,?])', r'\1', text.strip())

        # 2. استخراج المتغيرات
        pattern = r'\{\{(.*?)\}\}'
        matches = re.findall(pattern, clean_text)

        meta_text = clean_text
        real_samples = []

        for idx, raw_expr in enumerate(matches, start=1):
            raw_target = f"{{{{{raw_expr}}}}}"
            meta_text = meta_text.replace(raw_target, f"{{{{{idx}}}}}", 1)

            # استخراج العيّنة الحقيقية من الموديل
            sample_val = self._get_real_sample_value(raw_expr)
            real_samples.append(sample_val)

        # 3. حماية نهاية النص من الـ Variable أو علامات الترقيم المنفصلة
        meta_text = meta_text.strip()
        if re.search(r'\}\}[^a-zA-Z0-9]*$', meta_text):
            # إذا انتهى بـ variable أو علامة ترقيم بدون أحرف بعدها، نضيف نقطة ملتصقة
            meta_text = re.sub(r'\}\}[^a-zA-Z0-9]*$', '}}.', meta_text)

        return meta_text, real_samples

    def action_send_to_meta(self):
        self.ensure_one()

        account = self.account_id or self.env['whatsapp.account'].search([], limit=1)
        if not account or not account.access_token or not account.whatsapp_business_account_id:
            raise UserError(_("Please configure WhatsApp Access Token and WABA ID first."))

        waba_id = account.whatsapp_business_account_id
        token = account.access_token

        url = f"https://graph.facebook.com/v19.0/{waba_id}/message_templates"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # 1. تنظيف أي علامات ترقيم لصيقة للأقواس
        clean_body = re.sub(r':\s*\{\{', ' {{', self.body_text)

        # 2. تحويل الـ Jinja إلى {{1}}, {{2}} واستخراج العينات الحقيقية
        meta_body_text, real_samples = self._format_body_for_meta(clean_body)

        body_component = {
            "type": "BODY",
            "text": meta_body_text
        }

        # 3. إعداد الـ Example
        if real_samples:
            body_component["example"] = {
                "body_text": [real_samples]
            }

        clean_name = re.sub(r'[^a-z0-9_]', '', self.name.lower().strip().replace(" ", "_"))

        payload = {
            "name": clean_name,
            "category": self.category or "UTILITY",
            "language": self.language_code or "en_US",
            "components": [body_component]
        }

        try:
            res = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
            res_data = res.json()

            if res.status_code == 200:
                self.write({'state': 'in_review'})
            else:
                # استخراج التفاصيل الدقيقة جداً للخطأ القادم من Meta
                error_obj = res_data.get('error', {})
                error_user_msg = error_obj.get('error_user_msg')
                error_user_title = error_obj.get('error_user_title')
                error_data = error_obj.get('error_data', {}).get('details')
                msg = error_obj.get('message', 'Invalid Parameter')

                full_error = error_user_msg or error_data or error_user_title or msg

                self.write({'state': 'failed'})
                # إظهار الـ Response الكامل للـ Payload لمعرفة الحقل المطلوب
                raise UserError(_("Meta Raw Error: %s | Sent Payload: %s") % (full_error, json.dumps(payload)))
        except UserError:
            raise
        except Exception as e:
            self.write({'state': 'failed'})
            raise UserError(_("Connection Error: %s") % str(e))