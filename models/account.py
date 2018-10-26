# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Custom made by Yotech 

from odoo.tools.translate import _



import odoo.addons.decimal_precision as dp
from odoo.tools.float_utils import float_round, float_compare
from odoo import api, fields, models, _


import string
import math
import time

import logging
_logger = logging.getLogger(__name__)

#----------------------------------------------------------
# Accounts
#----------------------------------------------------------

class AccountAccount(models.Model):
    _inherit = "account.account"

    optimized_export = fields.Boolean(index=True, default=False)
    extern_code = fields.Char(string='External Code', required=True, translate=False)

class AccountJournal(models.Model):
    _inherit = "account.journal"

    extern_name = fields.Char(string='External Name', required=True, translate=False)
