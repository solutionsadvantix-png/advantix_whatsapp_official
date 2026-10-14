from odoo import models, fields, api
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_send_whatsapp(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send WhatsApp Message',
            'res_model': 'whatsapp.composer',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': 'sale.order',
                'default_res_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_phone': self.partner_id.phone or self.partner_id.mobile,
            }
        }