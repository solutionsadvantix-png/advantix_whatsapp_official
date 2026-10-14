import json
import logging
from odoo import http, _
from odoo.http import request

_LOGGER = logging.getLogger(__name__)

class WhatsAppWebhookController(http.Controller):

    @http.route('/whatsapp/webhook', type='http', auth='public', methods=['GET'], csrf=False)
    def verify_webhook(self, **kwargs):
        """ Meta Verification endpoint """
        mode = kwargs.get('hub.mode')
        token = kwargs.get('hub.verify_token')
        challenge = kwargs.get('hub.challenge')

        account = request.env['whatsapp.account'].sudo().search([('webhook_verify_token', '=', token)], limit=1)
        if mode == 'subscribe' and account:
            return challenge
        return request.make_response("Forbidden", status=403)

    @http.route('/whatsapp/webhook', type='json', auth='public', methods=['POST'], csrf=False)
    def receive_webhook(self, **kwargs):
        """ Processing incoming messages from Meta """
        data = json.loads(request.httprequest.data.decode('utf-8'))
        _LOGGER.info("Incoming WhatsApp Payload: %s", data)

        try:
            entry = data.get('entry', [])[0]
            changes = entry.get('changes', [])[0]
            value = changes.get('value', {})
            messages = value.get('messages', [])

            if messages:
                msg = messages[0]
                from_number = msg.get('from')
                msg_body = msg.get('text', {}).get('body', '')

                # البحث عن الزبون حسب رقم التلفون
                partner = request.env['res.partner'].sudo().search([
                    '|', ('phone', 'ilike', from_number), ('mobile', 'ilike', from_number)
                ], limit=1)

                if partner:
                    partner.message_post(
                        body=_("<b>WhatsApp Received:</b> %s") % msg_body,
                        message_type='comment'
                    )
        except Exception as e:
            _LOGGER.error("Error processing Webhook: %s", str(e))

        return {'status': 'success'}