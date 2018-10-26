# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Custom made by Yotech


import base64
import io
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import Warning
from odoo.tools import pycompat, DEFAULT_SERVER_DATE_FORMAT

from odoo.tools.translate import _

import odoo.addons.decimal_precision as dp
from odoo.tools.float_utils import float_round, float_compare

import string
import math
import time

import logging
_logger = logging.getLogger(__name__)

class AccountFrFec(models.TransientModel):
    _name = "account.fr.fec.quadratus"
    _inherit = "account.fr.fec"

    @api.multi
    def generate_fec_quadratus(self):
        self.ensure_one()
        # We choose to implement the flat file instead of the XML
        # file for 2 reasons :
        # 1) the XSD file impose to have the label on the account.move
        # but Odoo has the label on the account.move.line, so that's a
        # problem !
        # 2) CSV files are easier to read/use for a regular accountant.
        # So it will be easier for the accountant to check the file before
        # sending it to the fiscal administration
        # header = [
        #     'EcritureDate',      #
        #     'EcritureNum',       #
        #     'JournalCode',       #
        #     'CompteNum',         #
        #     'CompAuxLib',        #
        #     'Debit',             #
        #     'Credit',            #
        #     'Ref',               #
        #     'Date Echeance',     #
        #     'Code Quadratus',    #
        #     'Type Document'      #
        #     ]

        header = [
            'Date',                #  0
            'Journal',             #  1
            'CompteAuxiliaire',    #  2
            ' ',                   #  3
            'CompteProduit',       #  4
            'Label',               #  5
            'Debit',               #  6
            'Credit',              #  7
            'NumPiece',            #  8
            'Date Echeance',       #  9
            'TypeDocument'         # 10
            ]

        company = self.env.user.company_id
        if not company.vat:
            raise Warning(
               _("Missing VAT number for company %s") % company.name)
        if company.vat[0:2] != 'FR':
            raise Warning(
                _("FEC is for French companies only !"))

        fecfile = StringIO.StringIO()
        w = csv.writer(fecfile, delimiter=';')
        w.writerow(header)

# - La colonne A : la date doit être sous le format JJ/MM/AAA (facilement modifiable sous Excel)
# - La colonne B : le journal c'est ok
# - La colonne C : le compte auxiliaire doit avoir 6 chiffres ( impératif sinon on doit rajouter les 0 à la main pour pouvoir être intégrer)
# - La colonne E : les comptes de produits et de tva doivent avoir une longueur de 8 chiffres et le compte client est constitué du 411 + colonne C (soit 9 chiffres)
# - La colonne F : le libellé c'est ok
# - Les colonnes G et H : montant débit et crédit c'est ok
# - La colonnes I : pour le numéro de pièces, il faut enlever FAC et les / car sinon c'est trop long et tout ne rentre pas
# - La colonne J : pour la date d'échéance, le format est le même que le format de la date en JJ/MM/AAAA

    #aj.code AS JournalCode,

        sql_query = '''
        SELECT
            TO_CHAR(am.date, 'DD/MM/YYYY') AS EcritureDate,
            aj.extern_name AS extern_name,
            SUBSTRING(rp.quadratus_account_number from 3 for 8) AS quadratus_account_number,
            aa.code AS CompteIntermed,
            aa.code AS CompteNum,
            COALESCE(replace(rp.name, '|', '/'), '') AS Label,
            aml.debit  AS Debit,
            aml.credit AS Credit,
            am.name AS name,
            TO_CHAR(aml.date_maturity, 'DD/MM/YYYY') AS date_maturity,
            ai.type AS type,
            TO_CHAR(aml.move_id, '9999999999999') AS EcritureNum,
            aa.optimized_export AS optimized_export

        FROM
            account_move_line aml
            LEFT JOIN account_move am ON am.id=aml.move_id
            LEFT JOIN res_partner rp ON rp.id=aml.partner_id
            JOIN account_journal aj ON aj.id = am.journal_id
            JOIN account_account aa ON aa.id = aml.account_id
            LEFT JOIN res_currency rc ON rc.id = aml.currency_id
            LEFT JOIN account_full_reconcile rec ON rec.id = aml.full_reconcile_id
            LEFT JOIN account_invoice ai ON ai.id = aml.invoice_id
        WHERE
            am.date >= %s
            AND am.date <= %s
            AND am.company_id = %s
            AND (aml.debit != 0 OR aml.credit != 0)
            AND am.state = 'posted'
        '''

        sql_query += '''
        ORDER BY
            am.date,
            am.name,
            aml.id
        '''
        self._cr.execute(
            sql_query, (self.date_from, self.date_to, company.id))

        creditsum = 0
        currentmoveid = 0
        start = False
        for row in self._cr.fetchall():
            moveid=int(row[11])

            listrow = list(row)
            #_logger.info("row[3] =) " + str(row[3]) )
            #_logger.info("row[2] =) " + str(row[2]) )
            #_logger.info("row[10] =) " + str(row[10]) )
            optimized_export = False
            account_code = False
            # After Issue 2017 09 06 listrow[1]= str(row[1])
            listrow[1]= row[1]
            listrow[2]=  "" + str(row[2]).ljust(6,'0') + ""

            if row[3].isdigit():
                account_code = int(row[3])

            # La colonne C : le compte auxiliaire doit avoir 6 chiffres
            if row[3] == "41110000":
                listrow[4] = "411" + str(row[2])
            else:
                listrow[4]= str(row[4])

            #listrow[5]= str(row[5]) Label

            #listrow[6]= str(row[6]) Debit
            #listrow[7]= str(row[7]) Credit

            listrow[8] = listrow[8].replace('FACTURE', '')
            listrow[8] = listrow[8].replace('FAC', '')
            listrow[8] = listrow[8].replace('/', '')

            listrow[9]= str(row[9])

            listrow[11]= str(row[11])

            # Change JournalName by Extern Name if define
            #if row[8] != None :
            #    listrow[2]= str(row[8])
            # as listrow[7] has been already remove row 8 is infact row 7

            # Account move Name
            # as listrow[7] has been twice already remove row 9 is infact row 7
            #listrow[7] = str(row[9])

            # Echeance Date
            #listrow[8] = str(row[10])

            # Quadratus code
            #listrow[2] = str(row[11])

            # Document Type
            if row[10] == 'out_invoice':
                listrow[10] = "FACTURE"
            elif row[10] == 'in_invoice':
                listrow[10] = "AVOIR"
            else:
                listrow[10]= ""

            # optimized export or not
            if row[12] == True:
                 optimized_export = True

            del listrow[12]
            del listrow[11]

            if optimized_export:
                listrowprev = listrow
                # Start counter
                if moveid != currentmoveid:
                    start = True
                    debitsum = 0
                    creditsum = 0
                debitsum += row[6]
                creditsum += row[7]
            else:
                if start:
                    if debitsum != 0:
                        listrowprev[6]=str(debitsum).replace('.',',')
                    else:
                        listrowprev[6] = "0,0"
                    if creditsum != 0:
                        listrowprev[7]=str(creditsum).replace('.',',')
                    else:
                        listrowprev[7] = "0,0"
                    if row[1] == 'VE':
                        w.writerow([s.encode("utf-8") for s in listrowprev])


#listrow =) [u'01/02/2017', 'None', 'x000002', u'411100', '41110000', 'SAS M. INNOVATION', '0,00', '              53,92', 'BNK1/2017/0009', '01/02/2017', None, '            64', 'None']


                _logger.info("listrow =) " + str(listrow))
                listrow[6]= str(row[6])
                listrow[7]= str(row[7])
                listrow[6]=listrow[6].replace('.',',')
                listrow[7]=listrow[7].replace('.',',')
                if row[1] == 'VE':
                    w.writerow([s.encode("utf-8") for s in listrow])
                creditsum = 0
                debitsum = 0
                start = False
            currentmoveid=moveid

        siren = company.vat[4:13]
        end_date = self.date_to.replace('-', '')
        suffix = '-NONOFFICIAL'
        fecvalue = fecfile.getvalue()
        self.write({
            'fec_data': base64.encodestring(fecvalue),
            'filename': '%sFEC%s%s.csv' % (siren, end_date, suffix),
            })
        fecfile.close()

        action = {
            'name': 'FEC Quadratus',
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=account.fr.fec.quadratus&id=" + str(self.id) + "&filename_field=filename&field=fec_data&download=true&filename=" + self.filename,
            'target': 'self',
            }
        return action
