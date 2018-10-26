# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2017 Yotech (http://www.yotech.pro)

{
    'name': 'France - FEC - Quadratus',
    'version': '1.0',
    'category': 'Localization',
    'summary': "Fichier d'Échange Informatisé (FEC) for Quadratus",
    'author': "Yotech",
    'website': 'http://www.yotech.pro',
    'depends': ['l10n_fr','l10n_fr_fec','account'],
    'data': [
        'wizard/fec_view.xml',
        'views/account.xml',
    ],
    'installable': True,
    'auto_install': True,
}
