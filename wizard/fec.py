# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2013-2015 Akretion (http://www.akretion.com)

from openerp import models, fields, api, _
from openerp.exceptions import Warning
import base64
import StringIO
import csv

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
        header = [
            'EcritureDate',      #
            'EcritureNum',       #
            'JournalCode',       #
            'CompteNum',         #
            'CompAuxLib',        #
            'Debit',             #
            'Credit',            #
            'Ref',               #
            'Date Echeance',     #
            'Code Quadratus',    #
            'Type Document'      #
            ]

        company = self.env.user.company_id
        if not company.vat:
            raise Warning(
                _("Missing VAT number for company %s") % company.name)
        if company.vat[0:2] != 'FR':
            raise Warning(
                _("FEC is for French companies only !"))

        fecfile = StringIO.StringIO()
        w = csv.writer(fecfile, delimiter='|')
        w.writerow(header)

        sql_query = '''
        SELECT
            %s AS EcritureDate,
            '-' AS EcritureNum,
            '-' AS JournalCode,
            MIN(aa.code) AS CompteNum,
            '-' AS CompAuxLib,
            replace(CASE WHEN sum(aml.balance) <= 0 THEN '0,00' ELSE to_char(SUM(aml.balance), '999999999999999D99') END, '.', ',') AS Debit,
            replace(CASE WHEN sum(aml.balance) >= 0 THEN '0,00' ELSE to_char(-SUM(aml.balance), '999999999999999D99') END, '.', ',') AS Credit,
            MIN(aa.id) AS CompteID
        FROM
            account_move_line aml
            LEFT JOIN account_move am ON am.id=aml.move_id
            JOIN account_account aa ON aa.id = aml.account_id
            LEFT JOIN account_account_type aat ON aa.user_type_id = aat.id
        WHERE
            am.date < %s
            AND am.company_id = %s
            AND aat.include_initial_balance = 't'
            AND (aml.debit != 0 OR aml.credit != 0)
            AND am.state = 'posted'
        '''

        sql_query += '''
        GROUP BY aml.account_id
        HAVING sum(aml.balance) != 0
        '''
        formatted_date_from = self.date_from.replace('-', '')
        self._cr.execute(
            sql_query, (formatted_date_from, self.date_from, company.id))

        for row in self._cr.fetchall():
            listrow = list(row)
            account_id = listrow.pop()

            account = self.env['account.account'].browse(account_id)
            if account.user_type_id.id == self.env.ref('account.data_unaffected_earnings').id:
                #add the benefit/loss of previous fiscal year to the first unaffected earnings account found.
                unaffected_earnings_line = True
                current_amount = float(listrow[11].replace(',', '.')) - float(listrow[12].replace(',', '.'))
                unaffected_earnings_amount = float(unaffected_earnings_results[11].replace(',', '.')) - float(unaffected_earnings_results[12].replace(',', '.'))
                listrow_amount = current_amount + unaffected_earnings_amount
                if listrow_amount > 0:
                    listrow[11] = str(listrow_amount)
                    listrow[12] = '0.00'
                else:
                    listrow[11] = '0.00'
                    listrow[12] = str(listrow_amount)
            w.writerow([s.encode("utf-8") for s in listrow])

        # LINES
        sql_query = '''
        SELECT
            TO_CHAR(am.date, 'YYYYMMDD') AS EcritureDate,
            TO_CHAR(aml.move_id, '9999999999999') AS EcritureNum,
            replace(aj.code, '|', '/') AS JournalCode,
            aa.code AS CompteNum,
            COALESCE(replace(rp.name, '|', '/'), '') AS CompAuxLib,
            replace(CASE WHEN aml.debit = 0 THEN '0,00' ELSE to_char(aml.debit, '999999999999999D99') END, '.', ',') AS Debit,
            replace(CASE WHEN aml.credit = 0 THEN '0,00' ELSE to_char(aml.credit, '999999999999999D99') END, '.', ',') AS Credit,
            aa.optimized_export AS optimized_export,
            aj.extern_name AS extern_name,
            am.name AS name,
            TO_CHAR(aml.date_maturity, 'YYYYMMDD') AS date_maturity,
            rp.quadratus_account_number AS quadratus_account_number,
            ai.type AS type
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
            moveid=int(row[1])

            listrow = list(row)
            #_logger.info("row[3] =) " + str(row[3]) )
            #_logger.info("row[2] =) " + str(row[2]) )
            #_logger.info("row[10] =) " + str(row[10]) )
            optimized_export = False
            account_code = False

            if row[3].isdigit():
                account_code = int(row[3])

            if row[7] == True:
                optimized_export = True
            del listrow[7]
            
            # Change JournalName by Extern Name if define
            if row[8] != None :
                listrow[2]= str(row[8])
            # as listrow[7] has been already remove row 8 is infact row 7
            del listrow[7]

            # Account move Name
            # as listrow[7] has been twice already remove row 9 is infact row 7
            listrow[7] = str(row[9])
            
            # Echeance Date
            listrow[8] = str(row[10])
            
            # Quadratus code
            listrow[9] = str(row[11])
            
            # Document Type
            if row[12] == 'out_invoice':
                listrow[10] = "FACTURE"
            elif row[12] == 'in_invoice':
                listrow[10] = "AVOIR"
            else:
                listrow[10]= ""

            if optimized_export:
                listrowprev = listrow
                # Start counter
                if moveid != currentmoveid:
                    start = True
                    creditsum = 0
                    debitsum = 0
                creditsum_string = row[6].replace(',', '.')
                debitsum_string = row[5].replace(',', '.')
                creditsum += float(creditsum_string)
                debitsum += float(debitsum_string)
            else:
                if start:
                    if creditsum != 0:
                        listrowprev[6]=str(creditsum).replace('.', ',')
                    if debitsum != 0:
                        listrowprev[5]=str(debitsum).replace('.', ',')
                    w.writerow([s.encode("utf-8") for s in listrowprev])
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
            # Filename = <siren>FECYYYYMMDD where YYYMMDD is the closing date
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
