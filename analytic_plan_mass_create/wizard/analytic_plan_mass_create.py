# -*- coding: utf-8 -*-
# Copyright 2017 Eficent Business and IT Consulting Services S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
import time


class AnalyticPlanMassCreate(models.TransientModel):
    _name = "analytic.plan.mass.create"
    _description = "Create multiple analytic plan lines"

    item_ids = fields.One2many(
        'analytic.plan.mass.create.item',
        'wiz_id',
        'Items'
    )
    template_id = fields.Many2one(
        'analytic.plan.mass.create.template',
        'Template',
        required=True,
        ondelete='cascade'
    )

    @api.model
    def _prepare_item(self, account):
        return {
            'account_id': account.id,
            'company_id': account.company_id.id,
            'date': time.strftime('%Y-%m-%d'),
            'labor_cost': 0.0
        }

    @api.model
    def default_get(self, fields):
        res = super(AnalyticPlanMassCreate, self).default_get(fields)
        analytic_obj = self.env['account.analytic.account']
        analytic_account_ids = self._context.get('active_ids', [])
        active_model = self._context.get('active_model')
        if not analytic_account_ids:
            return res
        assert active_model == 'account.analytic.account', \
            'Bad context propagation'
        items = []
        for account in analytic_obj.browse(analytic_account_ids):
            items.append((0, 0, self._prepare_item(account)))
        res['item_ids'] = items
        return res

    @api.model
    def _prepare_analytic_line_plan_common(self, wizard, item):
        return {
            'account_id': item.account_id.id,
            'name': item.account_id.name,
            'date': item.date,
            'currency_id': wizard.template_id.currency_id.id,
            'user_id': self._uid,
            'company_id': item.account_id.company_id.id,
            'version_id': wizard.template_id.version_id.id
        }

    @api.multi
    def _prepare_analytic_line_plan(self, wizard, item, product,
                                    amount_currency, type, common):
        analytic_line_plan_obj = self.env['account.analytic.line.plan']
        line_ids = analytic_line_plan_obj.\
            search([('account_id', '=', item.account_id.id),
                    ('version_id', '=', wizard.template_id.version_id.id)])
        amount = 0.0
        if line_ids:
            line_ids[0].on_change_amount_currency()
            amount = line_ids[0]['amount']
        else:
            amount = item.labor_cost

        if type == 'expense':
            general_account_id = product.product_tmpl_id.\
                property_account_expense_id.id
            if not general_account_id:
                general_account_id =\
                    product.categ_id.property_account_expense_categ_id.id
        else:
            general_account_id = product.product_tmpl_id.\
                property_account_income_id.id
            if not general_account_id:
                general_account_id = product.categ_id.\
                    property_account_income_categ_id.id
        if not general_account_id:
            raise UserError(
                    _('Error !'
                      'There is no expense or income account '
                      'defined for this product: "%s" (id:%d)'
                      ) % (product.name, product.id,))
        if type == 'expense':
            journal_id = product.expense_analytic_plan_journal_id \
                and product.expense_analytic_plan_journal_id.id \
                or False
        else:
            journal_id = product.revenue_analytic_plan_journal_id \
                and product.revenue_analytic_plan_journal_id.id \
                or False
        if not journal_id:
            raise UserError(
                        _('Error !'
                          'There is no planning expense or revenue '
                          'journals defined for this product: "%s" (id:%d)'
                          ) % (product.name, product.id,))
        if type == 'expense':
            amount_currency *= -1
            amount *= -1
        data = {
            'amount_currency': amount_currency,
            'amount': amount,
            'product_id': product.id,
            'product_uom_id':
                wizard.template_id.labor_cost_product_id.uom_id.id,
            'general_account_id': general_account_id,
            'journal_id': journal_id,
        }
        data.update(common)
        return data

    @api.multi
    def create_analytic_plan_lines(self):
        res = []
        wizard = self
        analytic_line_plan_obj = self.env['account.analytic.line.plan']
        for item in wizard.item_ids:
            if item.delete_existing:
                line_ids = analytic_line_plan_obj.\
                    search([('account_id', '=', item.account_id.id),
                            ('version_id', '=',
                             wizard.template_id.version_id.id)])
                for line in line_ids:
                    line.unlink()

            common = self._prepare_analytic_line_plan_common(wizard, item)
            # Create Labor costs
            if item.labor_cost:
                plan_line_data_labor = self._prepare_analytic_line_plan(
                    wizard, item, wizard.template_id.labor_cost_product_id,
                    item.labor_cost, 'expense', common)
                plan_line_id = analytic_line_plan_obj.create(
                    plan_line_data_labor)
                res.append(plan_line_id.id)

            # Create Material costs
            if item.material_cost:
                plan_line_data_material = self._prepare_analytic_line_plan(
                    wizard, item, wizard.template_id.material_cost_product_id,
                    item.material_cost, 'expense', common)

                plan_line_id = analytic_line_plan_obj.create(
                    plan_line_data_material)
                res.append(plan_line_id.id)

            # Create Revenue
            if item.revenue:
                plan_line_data_revenue = \
                    self._prepare_analytic_line_plan(
                        wizard, item,
                        wizard.template_id.revenue_product_id,
                        item.revenue, 'revenue', common)
                plan_line_id = analytic_line_plan_obj.create(
                    plan_line_data_revenue)
                res.append(plan_line_id.id)

        return {
            'domain': "[('id','in', ["+','.join(map(str, res))+"])]",
            'name': _('Analytic Plan Lines'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.analytic.line.plan',
            'view_id': False,
            'context': False,
            'type': 'ir.actions.act_window'
        }


class AnalyticPlanMassCreateItem(models.TransientModel):
    _name = "analytic.plan.mass.create.item"
    _description = "Create multiple analytic plan lines item"

    wiz_id = fields.Many2one(
        'analytic.plan.mass.create',
        'Wizard',
        required=True,
        ondelete='cascade',
        readonly=True
    )
    account_id = fields.Many2one(
        'account.analytic.account',
        'Analytic Account',
        required=True
    )
    date = fields.Date(
        'Date',
        required=True
    )
    material_cost = fields.Float(
        'Planned material cost',
        required=True,
        digits=dp.get_precision('Account'),
        help='Planned material cost, expressed it in positive quantity.')
    labor_cost = fields.Float(
        'Planned labor cost',
        required=True,
        digits=dp.get_precision('Account'),
        help='Planned labor cost, expressed it in positive quantity.',
    )
    revenue = fields.Float(
        'Planned revenue',
        required=True,
        digits=dp.get_precision('Account'),
        help='Planned Revenue'
    )
    delete_existing = fields.Boolean(
        'Delete existing',
        help='''Delete existing planned lines. Will delete all planning lines
            for this analytic account for the version indicated in the
            template, and regardless of the date.'''
    )
