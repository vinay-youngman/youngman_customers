# -*- coding: utf-8 -*-
# from odoo import http


# class Youngman(http.Controller):
#     @http.route('/youngman/youngman', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/youngman/youngman/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('youngman.listing', {
#             'root': '/youngman/youngman',
#             'objects': http.request.env['youngman.youngman'].search([]),
#         })

#     @http.route('/youngman/youngman/objects/<model("youngman.youngman"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('youngman.object', {
#             'object': obj
#         })
