from __future__ import print_function

from odoo import models, api
import logging
_logger = logging.getLogger(__name__)


class MyOpLeadsSync(models.TransientModel):
    _name = 'cron.invoice.address.sync'

    @api.model
    def invoice_address_sync(self):
        customer_branches = self.env['res.partner'].sudo().search([('is_customer_branch', '=', True)])

        for customer_branch in customer_branches:
            try:
                customer_branch.sync_customer_details_from_mastersindia()
            except Exception as e:
                _logger.error("evt='INVOICE_ADDRESS_SYNC' res_partner_id="+str(customer_branch.id)+" msg=%s", e)
