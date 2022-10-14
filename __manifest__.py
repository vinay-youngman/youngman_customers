# -*- coding: utf-8 -*-
{
    'name': "youngman_customers",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Ajay",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '2.0',

    # any module necessary for this one to work correctly
    'depends': ['base','crm', 'base_vat', 'jobsites'],

    # always loaded
    'data': [
        'security/base_security.xml',
        'security/ir.model.access.csv',
        'views/lead_lost_no_tag.xml',
        'views/crm_no_tag.xml',
        'views/partner_no_tag.xml',
        'views/partner_readonly.xml',
        'views/send_to_beta.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
