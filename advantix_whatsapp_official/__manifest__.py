{
    'name': 'WhatsApp Integration for Community & Enterprise | Meta Cloud API | WhatsApp Direct Messaging | WhatsApp Sales | WhatsApp Invoices | WhatsApp Chatter | WhatsApp Marketing | Whatsapp For Comunity | Meta For Comunity | Meta Integration',
    'version': '18.0.1.0.0',
    'category': 'Marketing/WhatsApp',
    'summary': 'WhatsApp Integration Meta Cloud API WhatsApp Direct Message WhatsApp Sales WhatsApp Invoice Chatter WhatsApp Notification WhatsApp Template WhatsApp Messaging',
    'description': """
WhatsApp Official Integration for Odoo 19.0
===========================================
Send WhatsApp messages directly from Sales Orders, Invoices, and Partners using Official Meta Cloud API v19.0.

Key Search Features & Capabilities:
- WhatsApp Sales Order notifications
- WhatsApp Invoice / Journal Entry messages
- Direct WhatsApp Chatter Integration
- Custom WhatsApp Template Builder
- Official Meta Cloud API (v19.0)
- WhatsApp Marketing & Messaging
- WhatsApp 1-Click Direct Sender
    """,
    'author': 'Advantix Solutions',
    'website': 'https://advantix-solutions.com',
    'license': 'OPL-1',
    'depends': ['base', 'contacts', 'mail', 'sale', 'sale_management', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/whatsapp_account_views.xml',
        'views/whatsapp_template_views.xml',
        'views/whatsapp_composer_views.xml',
        'views/res_config_settings_views.xml',
        'views/menus.xml',
        'views/partner_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'data/whatsapp_template_data.xml',
    ],
    'images': ['static/description/banner.png'],
    'price': 9.99,
    'currency': 'USD',
    'installable': True,
    'application': True,
    'auto_install': False,
}
