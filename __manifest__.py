# -*- coding: utf-8 -*-
{
    'name': "Contacts & Customers",
    'version': '3.0',
    'category': 'Sales/CRM',
    'summary': 'Manages Contacts/Customers & Their Branches',
    'description': """
        Provides various modifications in Contacts Form.
    """,
    'author': "Ajay",
    'website': "https://www.youngman.co.in/",
    'sequence': -100,

    'depends': ['base','crm', 'base_vat'],

    'data': [
        'security/base_security.xml',
        'security/ir.model.access.csv',
        'views/lead_lost.xml',
        'views/crm_tag_noedit.xml',
        'views/contacts_form.xml',
        'views/send_to_beta.xml'
    ],

    'application': True,
    'installable': True,
    'auto_install': False,
}
