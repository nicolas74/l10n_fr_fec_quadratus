# -*- coding: utf-8 -*-

import time
import math

from openerp.osv import expression
from openerp.tools.float_utils import float_round as round
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.exceptions import UserError, ValidationError
from openerp import api, fields, models, _

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
