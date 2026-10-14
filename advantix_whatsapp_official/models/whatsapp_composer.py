import json
import re
import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class WhatsAppComposer(models.TransientModel):
    _name = 'whatsapp.composer'
    _description = 'WhatsApp Message Composer'

    account_id = fields.Many2one('whatsapp.account', string='WhatsApp Account', required=True)
    partner_id = fields.Many2one('res.partner', string='Recipient')
    phone = fields.Char(string='Phone Number', required=True)
    template_id = fields.Many2one('whatsapp.template', string='Template')
    body = fields.Text(string='Message Body', required=True)
    res_id = fields.Integer(string='Record ID')
    res_model = fields.Char(string='Record Model')

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            # نقل النص المباشر من القالب إلى الـ body
            body_text = self.template_id.body_text or ''

            # في حال وجود معالجة للمتغيرات (Render Dynamic Variables)
            if self.res_model and self.res_id:
                record = self.env[self.res_model].browse(self.res_id)
                # إذا كان القالب مخصص لنفس الموديل المفتوح أو للـ partner
                if record.exists():
                    # هنا يمكنك إضافة كود استبدال المتغيرات إذا كنتِ تستخدمين Jinja2 أو format
                    # body_text = self.env['mail.render.mixin']._render_template(body_text, self.res_model, [self.res_id])[self.res_id]
                    pass

            self.body = body_text
        else:
            self.body = False

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.phone =  self.partner_id.phone or ''

    def _render_template_parameters(self, record, body_text):
        """
        استخراج آمن وديناميكي للقيم الحقيقية من أي موديل (Sale, Invoice, Partner, etc.)
        """
        if not body_text or not record:
            return []

        pattern = r'\{\{(.*?)\}\}'
        matches = re.findall(pattern, body_text)
        params = []

        for raw_expr in matches:
            clean_path = raw_expr.strip()
            if clean_path.startswith("object."):
                clean_path = clean_path.replace("object.", "", 1)

            # تتبع المسار بشكل متسلسل وآمن
            val = record
            try:
                for path_part in clean_path.split('.'):
                    if val and hasattr(val, path_part):
                        val = getattr(val, path_part)
                    else:
                        val = False
                        break
            except Exception:
                val = False

            # تحديد القيمة النصية المناسبة حسب نوع البيانات
            if val is not False and val is not None:
                if hasattr(val, 'display_name'):
                    param_val = str(val.display_name or '')
                else:
                    param_val = str(val)
            else:
                param_val = "-"

            params.append({
                "type": "text",
                "text": param_val
            })

        return params
    # def action_send_whatsapp(self):
    #     self.ensure_one()
    #     template = self.template_id
    #     account = template.account_id or self.env['whatsapp.account'].search([], limit=1)
    #
    #     if not account or not account.access_token or not account.phone_number_id:
    #         raise UserError(_("Please configure WhatsApp Phone Number ID and Access Token."))
    #
    #     # 1. جلب الـ Record الحالي (مثلاً Sale Order S00006)
    #     record = self.env[self.res_model].browse(self.res_id) if self.res_model and self.res_id else False
    #
    #     # 2. بناء المتغيرات الـ 3 المجلوبة ديناميكياً من الـ Record
    #     parameters = []
    #     if record:
    #         parameters = self._render_template_parameters(record, template.body_text)
    #
    #     # 3. إعداد الـ Payload المبعوث لـ /messages endpoint
    #     clean_phone = re.sub(r'[^0-9]', '', self.phone or '')
    #
    #     components = []
    #     if parameters:
    #         components.append({
    #             "type": "body",
    #             "parameters": parameters
    #         })
    #
    #     payload = {
    #         "messaging_product": "whatsapp",
    #         "to": clean_phone,
    #         "type": "template",
    #         "template": {
    #             "name": template.name,
    #             "language": {
    #                 "code": template.language_code or "en_US"
    #             }
    #         }
    #     }
    #
    #     # إضافة الـ components فقط إذا كان التمبلت بيحتوي على متغيّرات
    #     if components:
    #         payload["template"]["components"] = components
    #
    #     url = f"https://graph.facebook.com/v19.0/{account.phone_number_id}/messages"
    #     headers = {
    #         "Authorization": f"Bearer {account.access_token}",
    #         "Content-Type": "application/json"
    #     }
    #
    #     try:
    #         res = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
    #         res_data = res.json()
    #
    #         if res.status_code == 200:
    #             if record and hasattr(record, 'message_post'):
    #                 rendered_body = template.body_text
    #                 for idx, param in enumerate(parameters, start=1):
    #                     rendered_body = rendered_body.replace(f"{{{{{idx}}}}}", param.get('text', ''))
    #
    #                 record.message_post(
    #                     body=f"<b>WhatsApp Message Sent to {self.phone}</b><br/>{rendered_body}",
    #                     subject=_("WhatsApp Message Sent"),
    #                     message_type="comment",
    #                     subtype_xmlid="mail.mt_note"
    #                 )
    #
    #             return {'type': 'ir.actions.act_window_close'}
    #         else:
    #             error_obj = res_data.get('error', {})
    #             msg = error_obj.get('message') or json.dumps(res_data)
    #             raise UserError(_("WhatsApp API Error (%s): %s") % (res.status_code, msg))
    #     except UserError:
    #         raise
    #     except Exception as e:
    #         raise UserError(_("Connection Error: %s") % str(e))
    def action_send_whatsapp(self):
        self.ensure_one()
        template = self.template_id
        account = template.account_id or self.env['whatsapp.account'].search([], limit=1)

        if not account or not account.access_token or not account.phone_number_id:
            raise UserError(_("Please configure WhatsApp Phone Number ID and Access Token."))

        # 1. التقاط الـ active_model و active_id من الـ context بشكل مؤكد 100%
        active_model = self.env.context.get('active_model') or self.res_model
        active_id = self.env.context.get('active_id') or self.res_id

        if not active_model or not active_id:
            raise UserError(_("Active record context is missing. Please try again from the document view."))

        record = self.env[active_model].browse(active_id)

        # 2. بناء المتغيرات ديناميكياً حسب الموديل الحالي (سواء Sale Order أو Account Move)
        parameters = []
        if record:
            parameters = self._render_template_parameters(record, template.body_text)

        # 3. إعداد الـ Payload للإرسال
        clean_phone = re.sub(r'[^0-9]', '', self.phone or '')

        components = []
        if parameters:
            components.append({
                "type": "body",
                "parameters": parameters
            })

        payload = {
            "messaging_product": "whatsapp",
            "to": clean_phone,
            "type": "template",
            "template": {
                "name": template.name,
                "language": {
                    "code": template.language_code or "en_US"
                }
            }
        }

        if components:
            payload["template"]["components"] = components

        url = f"https://graph.facebook.com/v19.0/{account.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {account.access_token}",
            "Content-Type": "application/json"
        }

        try:
            res = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
            res_data = res.json()

            if res.status_code == 200:
                # تسجيل الرسالة في الـ Chatter للموديل الحالي أياً كان (Sale أو Invoice)
                if record and hasattr(record, 'message_post'):
                    rendered_body = template.body_text
                    for idx, param in enumerate(parameters, start=1):
                        rendered_body = rendered_body.replace(f"{{{{{idx}}}}}", param.get('text', ''))

                    record.message_post(
                        body=f"<b>WhatsApp Message Sent to {self.phone}</b><br/>{rendered_body}",
                        subject=_("WhatsApp Message Sent"),
                        message_type="comment",
                        subtype_xmlid="mail.mt_note"
                    )

                return {'type': 'ir.actions.act_window_close'}
            else:
                error_obj = res_data.get('error', {})
                msg = error_obj.get('message') or json.dumps(res_data)
                raise UserError(_("WhatsApp API Error (%s): %s") % (res.status_code, msg))
        except UserError:
            raise
        except Exception as e:
            raise UserError(_("Connection Error: %s") % str(e))