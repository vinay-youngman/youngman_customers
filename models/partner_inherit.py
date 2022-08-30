# -*- coding: utf-8 -*-

from odoo import models, fields, api
from random import randint
import logging
from odoo import api, fields, models, _

from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PartnerInherit(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    @api.model
    def _get_default_country(self):
        country = self.env['res.country'].search([('code', '=', 'IN')], limit=1)
        return country

    def _default_channel_tag(self):
        return self.env['res.partner.channel.tag'].browse(self._context.get('channel_tag_id'))

    def _default_bd_tag(self):
        return self.env['res.partner.bd.tag'].browse(self._context.get('bd_tag_id'))

    in_beta = fields.Boolean(default=False, string="In Beta")

    is_customer_branch = fields.Boolean(default=False, string="Is Branch")

    gstn = fields.Char(string="GSTN")
    sap_ref = fields.Char()

    credit_rating = fields.Selection([
        ('0', 'A'),
        ('1', 'B'),
        ('2', 'C'),
    ], string='Credit Rating', default='2')

    cpl_status = fields.Selection([
        ('0', 'LEGAL'),
        ('1', 'BLOCKED'),
        ('2', 'UNBLOCKED'),
    ], string='CPL Status')

    bill_submission = fields.Many2one('res.partner.bill.sub', string='Bill Submission', required=True)
    rental_advance = fields.Boolean(default=True, string="Rental Advance")
    rental_order = fields.Boolean(default=True, string="Rental Order")
    security_cheque = fields.Boolean(default=True, string="Security Cheque")
    user_recievable_id = fields.Integer()

    country_id = fields.Many2one('res.country', string='Mailing Country', default=_get_default_country, ondelete='restrict')

    # Mailing Address
    mailing_street = fields.Char(string="Mailing Address")
    mailing_street2 = fields.Char()
    mailing_city = fields.Char()
    mailing_state_id = fields.Many2one("res.country.state", string='Mailing State', ondelete='restrict',
                                       domain="[('country_id', '=', mailing_country_id)]")
    mailing_country_id = fields.Many2one('res.country', string='Mailing Country', default=_get_default_country, ondelete='restrict')
    mailing_zip = fields.Char(string='Mailing Pincode', change_default=True)

    child_ids = fields.One2many('res.partner', 'parent_id', string='Contact',
                                domain=[('active', '=', True), ('is_company', '=', False), ('is_customer_branch', '=',
                                                                                            False)])  # force "active_test" domain to bypass _search() override
    branch_ids = fields.One2many('res.partner', 'parent_id', string='Branches',
                                 domain=[('active', '=', True), ('is_company', '=', True),
                                         ('is_customer_branch', '=', True)])

    channel_tag_ids = fields.Many2many('res.partner.channel.tag', column1='partner_id',
                                       column2='channel_tag_id', string='Channel Tags', default=_default_channel_tag)
    bd_tag_ids = fields.Many2many('res.partner.bd.tag', column1='partner_id',
                                  column2='bd_tag_id', string='BD Tags', default=_default_channel_tag)

    bd_tag_user_ids = fields.One2many('contact.team.users', 'contact_id', string='Contact Team Users',
                                      help="Users having this BD Tag as team name")

    same_addr = fields.Boolean(default=False)

    @api.onchange('same_addr')
    def _onchange_same_addr(self):
        if self.same_addr:
            self.mailing_street = self.street
            self.mailing_street2 = self.street2
            self.mailing_city = self.city
            self.mailing_state_id = self.state_id
            self.mailing_zip = self.zip

    @api.onchange('bd_tag_ids')
    def _onchange_bd_tag_ids(self):
        _logger.error("called _onchange_bd_tag_ids")
        _logger.error(str(self.id) + " has " + str(len(self.bd_tag_user_ids)))
        if (self._origin.id):
            self._cr.execute('delete from contact_team_users where contact_id = %s', [self._origin.id])
            _logger.error(str(self.id) + " has " + str(len(self.bd_tag_user_ids)))

            for bd_tag in self.bd_tag_ids:
                users = self.env['res.users'].sudo().search(
                    ['|', ('sale_team_id.name', 'ilike', bd_tag.name), ('groups_id.name', '=', 'User: All Documents')])
                _logger.error("For tag name " + str(bd_tag.name) + " " + str(len(users)) + " type " + str(
                    type(self.bd_tag_user_ids)))
                for user in users:
                    self._cr.execute(
                        'insert into contact_team_users (user_name, user_id, contact_id) values(%s, %s, %s)',
                        (user.name, user.id, self._origin.id))

    @api.onchange('user_id')
    def _onchange_salesperson(self):
        new_user_id = self.user_id
        linked_contacts = self.child_ids
        _logger.error("called _onchange_user_id")
        for contact in linked_contacts:
            _logger.error(
                "updating res_partner user id = " + str(new_user_id.id) + " for user " + str(contact._origin.id))
            self._cr.execute('update res_partner set user_id = %s where id = %s', (new_user_id.id, contact._origin.id))

    @api.onchange('team_id')
    def _onchange_salesteam(self):
        new_team_id = self.team_id
        linked_contacts = self.child_ids
        _logger.error("called _onchange_team_id")
        for contact in linked_contacts:
            _logger.error(
                "updating res_partner team id = " + str(new_team_id.id) + " for user " + str(contact._origin.id))
            self._cr.execute('update res_partner set team_id = %s where id = %s', (new_team_id.id, contact._origin.id))

    @api.onchange('property_payment_term_id')
    def _onchange_property_payment_term_id(self):
        new_payment_term = self.property_payment_term_id
        linked_contacts = self.child_ids
        _logger.error("called _onchange_property_payment_term_id")
        for contact in linked_contacts:
            _logger.error("updating " + contact.name)
            contact.property_payment_term_id = new_payment_term

    @api.model
    def view_header_get(self, view_id, view_type):
        if self.env.context.get('channel_tag_id'):
            return _(
                'Partners: %(channel)s',
                channel=self.env['res.partner.channel.tag'].browse(self.env.context['channel_tag_id']).name,
            )
        if self.env.context.get('bd_tag_id'):
            return _(
                'Partners: %(bd_tag_id)s',
                bd_tag_id=self.env['res.partner.bd.tag'].browse(self.env.context['bd_tag_id']).name,
            )
        return super().view_header_get(view_id, view_type)

    def check_vat(self, cr, uid, ids, context=None):
        user_company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        if user_company.vat_check_vies:
            check_func = self.vies_vat_check
        else:
            check_func = self.simple_vat_check
        for partner in self.browse(cr, uid, ids, context=context):
            if not partner.vat:
                continue
            if partner.country_id.code and partner.vat.startswith(partner.country_id.code):

                vat_country, vat_number = self._split_vat(partner.vat)
            elif partner.country_id.code:
                vat_number = partner.vat
                vat_country = partner.country_id.code
            else:  # if no country code ->
                # just raise error that country is required?
                pass
            if not check_func(cr, uid, vat_country, vat_number, context=context):
                return False
            return True

class ContactTeamUsers(models.Model):
    _description = 'Contact Team Users'
    _name = 'contact.team.users'

    user_name = fields.Char(string="User Name")
    user_id = fields.Integer(string="User Id")
    contact_id = fields.Many2one('res.partner', string="Contact")


class PartnerChannelTag(models.Model):
    _description = 'Partner Channel'
    _name = 'res.partner.channel.tag'
    _order = 'name'
    _parent_store = True

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char(string='Channel Name', required=True, translate=True)
    color = fields.Integer(string='Color', default=_get_default_color)
    parent_id = fields.Many2one('res.partner.channel.tag', string='Parent Channel', index=True, ondelete='cascade')
    child_ids = fields.One2many('res.partner.channel.tag', 'parent_id', string='Child Channels')
    active = fields.Boolean(default=True, help="The active field allows you to hide the channel without removing it.")
    parent_path = fields.Char(index=True)
    partner_ids = fields.Many2many('res.partner', column1='channel_tag_id', column2='partner_id', string='Partners')

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('You can not create recursive tags.'))

    def name_get(self):
        """ Return the channels' display name, including their direct
            parent by default.

            If ``context['partner_channel_display']`` is ``'short'``, the short
            version of the channel name (without the direct parent) is used.
            The default is the long version.
        """
        if self._context.get('partner_channel_display') == 'short':
            return super(PartnerChannelTag, self).name_get()

        res = []
        for channel in self:
            names = []
            current = channel
            while current:
                names.append(current.name)
                current = current.parent_id
            res.append((channel.id, ' / '.join(reversed(names))))
        return res

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            # Be sure name_search is symetric to name_get
            name = name.split(' / ')[-1]
            args = [('name', operator, name)] + args
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)


class PartnerBdTag(models.Model):
    _description = 'Partner Channel'
    _name = 'res.partner.bd.tag'
    _order = 'name'
    _parent_store = True

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char(string='BD Tag Name', required=True, translate=True)
    color = fields.Integer(string='Color', default=_get_default_color)
    parent_id = fields.Many2one('res.partner.bd.tag', string='Parent Bd tag', index=True, ondelete='cascade')
    child_ids = fields.One2many('res.partner.bd.tag', 'parent_id', string='Child Bd tags')
    active = fields.Boolean(default=True, help="The active field allows you to hide the bdtag without removing it.")
    parent_path = fields.Char(index=True)
    partner_ids = fields.Many2many('res.partner', column1='bd_tag_id', column2='partner_id', string='Partners')

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('You can not create recursive tags.'))

    def name_get(self):
        """ Return the channels' display name, including their direct
            parent by default.

            If ``context['partner_channel_display']`` is ``'short'``, the short
            version of the bdtag name (without the direct parent) is used.
            The default is the long version.
        """
        if self._context.get('partner_bdtag_display') == 'short':
            return super(PartnerBdTag, self).name_get()

        res = []
        for bdtag in self:
            names = []
            current = bdtag
            while current:
                names.append(current.name)
                current = current.parent_id
            res.append((bdtag.id, ' / '.join(reversed(names))))
        return res

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            # Be sure name_search is symetric to name_get
            name = name.split(' / ')[-1]
            args = [('name', operator, name)] + args
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)

class PartnerBillSubmission(models.Model):
    _name = 'res.partner.bill.sub'
    _description = 'Bill Submission'

    name = fields.Char(string='Bill Submission', required=True)
