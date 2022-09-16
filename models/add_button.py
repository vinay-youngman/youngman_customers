# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.tools import date_utils

import logging
import json
import requests

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _name = 'crm.lead'
    _inherit = 'crm.lead'

    in_beta = fields.Boolean(default=False, string="Add Customer To Beta")

    def button_function(self):
        self.in_beta = True
        self.partner_id.in_beta = True

