from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    whatsapp_account_id = fields.Many2one(
        'whatsapp.account',
        string='Default WhatsApp Account',
        config_parameter='advantix_whatsapp.default_account_id',
        help='The main WhatsApp account used across the system.'
    )

    whatsapp_auto_post_chatter = fields.Boolean(
        string='Log Messages in Chatter',
        config_parameter='advantix_whatsapp.auto_post_chatter',
        default=True,
        help='Automatically log sent and received WhatsApp messages in customer chatters.'
    )

    whatsapp_notify_on_fail = fields.Boolean(
        string='Notify on Failure',
        config_parameter='advantix_whatsapp.notify_on_fail',
        default=True,
        help='Send a system notification to users if a WhatsApp message fails to send.'
    )