# -*- coding: utf-8 -*-
import traceback

from odoo import models, fields, api
from random import randint
import logging
import json
import requests
from odoo import api, fields, models, _

from odoo.modules import get_module_resource

from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class GstVerification(models.Model):
    _name = 'gst.verification'

    @staticmethod
    def get_master_india_access_token():
        url = "https://pro.mastersindia.co/oauth/access_token"
        access_data_file_path = get_module_resource('youngman_customers', 'static/config.json')
        config = open(access_data_file_path, 'r')
        config = config.read()
        access_data = json.loads(config)
        payload = json.dumps({
            "username": access_data["username"],
            "password": access_data["password"],
            "client_id": access_data["client_id"],
            "client_secret": access_data["client_secret"],
            "grant_type": "password"
        })
        headers = {
            'Content-Type': 'application/json',
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        return response.json()['access_token'], access_data["client_id"]

    @staticmethod
    def validate_gstn_from_master_india(gstin_num):
        url = "https://commonapi.mastersindia.co/commonapis/searchgstin?gstin=%s" % (gstin_num)
        _logger.info("Master india api url is %s" % (url))
        acesstoken, clientid = GstVerification.get_master_india_access_token()
        payload = ""
        headers = {
            'client_id': clientid,
            'Content-type': 'application/json',
            'Authorization': 'Bearer %s' % acesstoken
        }
        response = requests.request("GET", url, headers=headers, data=payload)
        return response.json()


class BusinessType(models.Model):
    _name = 'business.type'
    name = fields.Char(string='Business Type')


class PartnerInherit(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'gst.verification', 'business.type']

    business_type = fields.Many2one(comodel_name='business.type', string='Business Type')

    @api.model
    def _get_default_country(self):
        country = self.env['res.country'].search([('code', '=', 'IN')], limit=1)
        return country

    def _default_channel_tag(self):
        return self.env['res.partner.channel.tag'].browse(self._context.get('channel_tag_id'))

    def _default_bd_tag(self):
        return self.env['res.partner.bd.tag'].browse(self._context.get('bd_tag_id'))

    def _add_invoice_addresses(self, branch):
        gstn_data = super(PartnerInherit, self).validate_gstn_from_master_india(branch.gstn)
        _logger.error(gstn_data)
        if (gstn_data['error']):
            error_code = gstn_data["data"]["error"]["error_cd"]
            error_msg = gstn_data["data"]["error"]["message"]
            raise Exception(error_code + ": " + error_msg)

        addresses = []
        addresses.append({
            'is_company': False,
            'type': 'invoice',
            'name': gstn_data["data"]["pradr"]["addr"]["bno"] + gstn_data["data"]["pradr"]["addr"]["bnm"],
            'parent_id': branch.id,
            'street': gstn_data["data"]["pradr"]["addr"]["bno"] + gstn_data["data"]["pradr"]["addr"]["bnm"],
            'street2': gstn_data["data"]["pradr"]["addr"]["st"],
            'city': gstn_data["data"]["pradr"]["addr"]["city"],
            'zip': str(gstn_data["data"]["pradr"]["addr"]["pncd"]) if gstn_data["data"]["pradr"]["addr"][
                                                                          "pncd"] is not None else None
        })
        for addr in gstn_data["data"]["adadr"]:
            addresses.append({
                'is_company': False,
                'type': 'invoice',
                'parent_id': branch.id,
                'name': addr["addr"]["flno"] + ", " + addr["addr"]["bno"] + ", " + addr["addr"]["bnm"],
                'street': addr["addr"]["flno"] + ", " + addr["addr"]["bno"] + ", " + addr["addr"]["bnm"],
                'street2': addr["addr"]["st"] + ", " + addr["addr"]["loc"] + ", " + addr["addr"]["dst"],
                'city': addr["addr"]["city"],
                'zip': str(addr["addr"]["pncd"]) if addr["addr"]["pncd"] is not None else None
            })
        _logger.error("Address = " + str(len(addresses)))
        for address in addresses:
            existing_address = self.env['res.partner'].search(
                [('is_company', '=', False),
                 ('type', '=', 'invoice'),
                 ('parent_id', '=', branch.id),
                 ('name', '=', address['name']),
                 ('street', '=', address['street']),
                 ('street2', '=', address['street2']),
                 ('city', '=', address['city']),
                 ('zip', '=', address['zip'])], limit=1)

            if len(existing_address) == 0:
                data = super(PartnerInherit, self).create([address])
                _logger.info("Saved invoice address: " + str(data.id))
            else:
                _logger.info("Invoice address already exists")

    def add_invoice_address(self):
        self._add_invoice_addresses(self)

    in_beta = fields.Boolean(default=False, string="Exists In Beta", store=True)
    is_customer_branch = fields.Boolean(default=False, string="Is Branch")
    gstn = fields.Char(string="GSTN")
    sap_ref = fields.Char()


    def return_account_manager_domain(self):
        acc_m_team_id = self.env['crm.team'].search([('name', '=', 'ACCOUNT MANAGER')]).id
        domain = self.env['crm.team.member'].search([('crm_team_id', '=', acc_m_team_id)]).user_id.ids
        return [('id', 'in', domain)]

    # def return_account_manager_readonly(self):
    #     uid = self.env.uid
    #     team_id = self.env['crm.team'].search([('name', '=', 'ACCOUNT MANAGER')]).user_id
    #     if uid == team_id:
    #         return False
    #     else:
    #         return True

    def return_account_receivable_domain(self):
        acc_r_team_id = self.env['crm.team'].search([('name', '=', 'ACCOUNT RECEIVABLE')]).id
        domain = self.env['crm.team.member'].search([('crm_team_id', '=', acc_r_team_id)]).user_id.ids
        return [('id', 'in', domain)]

    def return_bde_domain(self):
        bde_team_id = self.env['crm.team'].search([('name', '=', 'BDE')]).id
        domain = self.env['crm.team.member'].search([('crm_team_id', '=', bde_team_id)]).user_id.ids
        return [('id', 'in', domain)]

    account_manager = fields.Many2one(comodel_name='res.users', string='Account Manager', domain=lambda self: self.return_account_manager_domain(), store=True)
    account_receivable = fields.Many2one(comodel_name='res.users', string='Account Receivable', domain=lambda self: self.return_account_receivable_domain(), readonly=True, store=True)
    bde = fields.Many2one(comodel_name='res.users', string='BDE', domain=lambda self: self.return_bde_domain(), store=True)


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

    rental_advance = fields.Boolean(default=True, string="Rental Advance")
    rental_order = fields.Boolean(default=True, string="Rental Order")
    security_cheque = fields.Boolean(default=True, string="Security Cheque")
    branch_contact_name = fields.Char(string="Contact Name")

    country_id = fields.Many2one('res.country', string='Mailing Country', default=_get_default_country,
                                 ondelete='restrict')

    # Mailing Address
    mailing_street = fields.Char(string="Mailing Address")
    mailing_street2 = fields.Char()
    mailing_city = fields.Char()
    mailing_state_id = fields.Many2one("res.country.state", string='Mailing State', ondelete='restrict',
                                       domain="[('country_id', '=', mailing_country_id)]")
    mailing_country_id = fields.Many2one('res.country', string='Mailing Country', default=_get_default_country,
                                         ondelete='restrict')
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
    reqd_email = fields.Boolean(default=False, compute='_email_required', store=False)

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
            if contact.type != 'invoice':
                _logger.error(
                    "updating res_partner user id = " + str(new_user_id.id) + " for user " + str(contact._origin.id))
                self._cr.execute('update res_partner set user_id = %s where id = %s',
                                 (new_user_id.id, contact._origin.id))

    @api.onchange('team_id')
    def _onchange_salesteam(self):
        new_team_id = self.team_id
        linked_contacts = self.child_ids
        _logger.error("called _onchange_team_id")
        for contact in linked_contacts:
            if contact.type != 'invoice':
                _logger.error(
                    "updating res_partner team id = " + str(new_team_id.id) + " for user " + str(contact._origin.id))
                self._cr.execute('update res_partner set team_id = %s where id = %s',
                                 (new_team_id.id, contact._origin.id))

    @api.onchange('property_payment_term_id')
    def _onchange_property_payment_term_id(self):
        new_payment_term = self.property_payment_term_id
        linked_contacts = self.child_ids
        _logger.error("called _onchange_property_payment_term_id")
        for contact in linked_contacts:
            if contact.type != 'invoice':
                _logger.error("updating " + contact.name)
                contact.property_payment_term_id = new_payment_term

    @api.onchange('category_id')
    def _email_required(self):
        tag_list = []
        for record in self.category_id:
            tag_list.append(record.name)
        if "Purchaser" in tag_list:
            self.reqd_email = True
        else:
            self.reqd_email = False

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

    def getARId(self):
        self.env.cr.execute(
            """SELECT crm_team_member.user_id FROM crm_team, crm_team_member WHERE crm_team.name = 'ACCOUNT RECEIVABLE' AND crm_team.id=crm_team_member.crm_team_id and crm_team_member.active=true""")
        members = self.env.cr.fetchall()
        count = {}
        for member_id in members:
            self.env.cr.execute(
                """select count(id) from res_partner where account_receivable=%s and active=true AND is_customer_branch=false AND is_company=true""",
                member_id)
            member_count = self.env.cr.fetchall()
            count[member_id] = member_count[0][0]
        return [id for id in count if all(count[temp] >= count[id] for temp in count)][0]

    def getBDEId(self):
        self.env.cr.execute(
            """SELECT crm_team_member.user_id FROM crm_team, crm_team_member WHERE crm_team.name = 'BDE' AND crm_team.id=crm_team_member.crm_team_id and crm_team_member.active=true""")
        members = self.env.cr.fetchall()
        count = {}
        for member_id in members:
            self.env.cr.execute(
                """select count(id) from res_partner where bde=%s and active=true AND is_customer_branch=true""",
                member_id)
            member_count = self.env.cr.fetchall()
            count[member_id] = member_count[0][0]
        return [id for id in count if all(count[temp] >= count[id] for temp in count)][0]

    # def getAMId(self):
    #     self.env.cr.execute(
    #         """SELECT crm_team_member.user_id FROM crm_team, crm_team_member WHERE crm_team.name = 'ACCOUNT MANAGER' AND crm_team.id=crm_team_member.crm_team_id and crm_team_member.active=true""")
    #     members = self.env.cr.fetchall()
    #     count = {}
    #     for member_id in members:
    #         self.env.cr.execute(
    #             """select count(id) from res_partner where account_manager=%s and active=true AND is_customer_branch=true""",
    #             member_id)
    #         member_count = self.env.cr.fetchall()
    #         count[member_id] = member_count[0][0]
    #     return [id for id in count if all(count[temp] >= count[id] for temp in count)][0]

    def _get_partner_details(self, saved_partner_id, gstn):
        return {
            "is_company": True,
            "active": True,
            "company_type": "company",
            "name": gstn,
            "parent_id": saved_partner_id.id,
            "company_name": gstn,
            "gstn": gstn,
            "type": "contact",
            "street": saved_partner_id.street,
            "street2": saved_partner_id.street2,
            "city": saved_partner_id.city,
            "state_id": saved_partner_id.state_id.id,
            "zip": saved_partner_id.zip,
            "country_id": saved_partner_id.country_id.id,
            "vat": saved_partner_id.vat,
            "is_customer_branch": True,
            "function": False,
            "phone": saved_partner_id.phone,
            "mobile": saved_partner_id.mobile,
            "email": saved_partner_id.email,
            "property_payment_term_id": False,
            # "account_receivable": saved_partner_id.account_receivable.id,
            "account_manager": 70,
            "bde": self.getBDEId(),
            "property_supplier_payment_term_id": False,
            "property_account_position_id": False,
            "property_account_receivable_id": 7,
            "property_account_payable_id": 26,
            "branch_ids": []
        }

    def _get_gstn(self, val):
        if 'gstn' in val and val['gstn'] is not False:
            return val['gstn']

        if 'vat' not in val:
            return False

        if val['vat'] and len(val['vat']) == 15:
            return val['vat']

        if val['vat'] and len(val['vat']) == 10:
            return False

        raise Exception("Vat is not valid")

    @api.model_create_multi
    def create(self, vals):
        _logger.info("evt=CreatePartner msg=Inside create method before super")

        for val in vals:
            if ('is_company' in val and val['is_company'] is False) or (
                    'company_type' in val and val['company_type'] == 'person'):
                saved_partner_id = super(PartnerInherit, self).create([val])
                return saved_partner_id

            gstn = self._get_gstn(val)
            val['vat'] = gstn[slice(2, 12, 1)] if gstn is not False else val['vat']

            if 'branch_ids' in val and len(val['branch_ids']) == 0 and val['is_customer_branch'] == False:
                val['account_receivable'] = self.getARId()
                val['account_manager'] = 70

                saved_partner_id = super(PartnerInherit, self).create([val])
                _logger.info("evt=CreatePartner msg=Creating a default branch for new customer")
                self.env['res.partner'].create(self._get_partner_details(saved_partner_id, gstn))
                return saved_partner_id
            else:
                saved_partner_id = super(PartnerInherit, self).create([val])
                if saved_partner_id.is_customer_branch == True:
                    self._add_invoice_addresses(saved_partner_id)
                _logger.info("evt=CreatePartner msg=Branch already exits. Creating only customer")
                return saved_partner_id

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
