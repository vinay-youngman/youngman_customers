# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

import logging

from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _name = 'crm.lead'
    _inherit = 'crm.lead'

    job_order = fields.Char(string="Job Order")




