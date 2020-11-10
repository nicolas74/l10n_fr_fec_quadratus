# -*- coding: utf-8 -*-


from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)

#----------------------------------------------------------
# Partner
#----------------------------------------------------------

class res_partner(models.Model):
    _inherit = "res.partner"

    quadratus_account_number = fields.Char(string='Quadratus account number')