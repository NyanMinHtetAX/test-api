from odoo import http
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.osv import expression

class OdooRestGet(http.Controller):

    @http.route('/api/get/currency', type='json', auth='none', methods=['POST'], csrf=False)
    def get_currencies(self, **kwargs):
        """
        Get Currency
        """
        params = request.get_json_data()
        uid = request.session.uid
        if not uid:
            return {'success': False, 'error': 'Invalid cookie.'}
        domain = params.get('domain', '[]')
        additional_fields = params.get('additional_fields', [])
        if not uid:
            return {'success': False,'error': 'Invalid cookie.'}
        try:
            domain = eval(domain)
        except Exception as e:
            return {'error': 'Invalid domain.'}
        first_time = params.get('first_time', False)
        if first_time:
            currencies = request.env['res.currency'].sudo().with_company(params['company_id']).search(domain)
        else:
            domain = expression.AND([domain, [('write_date', '>=', params['write_date'])]])
            currencies = request.env['res.currency'].sudo().with_company(params['company_id']).search(domain)
        records = []
        for currency in currencies:
            vals = {
                'id': currency.id,
                'name': currency.name,
                'symbol': currency.symbol,
                'currency_unit_label': currency.currency_unit_label or '',
                'write_date': currency.write_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            }
            for additional_field in additional_fields:
                vals[additional_field] = getattr(currency, additional_field)
            rates = []
            for rate in currency.rate_ids:
                rate_vals = {
                    'id': rate.id,
                    'date': rate.name,
                    'rate': rate.inverse_company_rate,
                }
                rates.append(rate_vals)
            vals['rates'] = rates
            records.append(vals)
        return {'succes': True, 'return_list': records}

    @http.route('/api/products', type='json', auth='public', methods=['GET'], csrf=False)
    def get_products(self, **kwargs):
        """
        Get all products
        """
        uid = request.session.uid
        if not uid:
            return {'success': False, 'error': 'Invalid cookie.'}

        product_templates = request.env['product.template'].search_read(
            domain=[['detailed_type', '=', 'product']],
            fields=['id', 'display_name', 'list_price']
        )

        # Fetch product variants
        product_product = request.env['product.product'].search_read(
            domain=[['detailed_type', '=', 'product']],
            fields=['id', 'display_name', 'list_price']
        )
        response = {
            'success': True,
            'product_templates': [{'id': pt['id'], 'name': pt['display_name'], 'list_price': pt['list_price']} for pt in product_templates],
            'product_product': [{'id': pv['id'], 'name': pv['display_name'], 'list_price': pv['list_price']} for pv in product_product],
        }

        return response

    @http.route('/api/sale-order', type='json', auth='public', methods=['GET'], csrf=False)
    def get_sale_order(self, **kwargs):
        """
        Get Sale Order
        """
        params = request.get_json_data()
        uid = request.session.uid
        if not uid:
            return {'success': False, 'error': 'Invalid cookie.'}
        order_id = params.get('order_id')
        sale_order = request.env['sale.order'].sudo().search([('id', '=', order_id)])
        records = []
        for order in sale_order:
            order_lines = []
            for line in order.order_line:
                order_lines.append({
                    'name': line.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'price_unit': line.price_unit,
                })
            records.append({
                'partner_id': order.partner_id.id,
                'partner_invoice_id': order.partner_invoice_id.id,
                'partner_shipping_id': order.partner_shipping_id.id,
                'date_order': order.date_order.strftime('%Y-%m-%d %H:%M:%S') if order.date_order else '',
                'pricelist_id': order.pricelist_id.id,
                'currency_id': order.currency_id.id,
                'payment_term_id': order.payment_term_id.id,
                'warehouse_id': order.warehouse_id.id,
                'user_id': order.user_id.id,
                'team_id': order.team_id.id,
                'order_lines': order_lines,
                'order_id': order.id,
                'write_date': order.write_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            })
        return {'success': True, 'orders': records}

class OdooRestCreate(http.Controller):

    @http.route('/api/create/sale_order', type='json', auth='public', methods=['POST'], csrf=False)
    def create_sale_order(self, **kwargs):
        """
        Create a sale order
        """
        params = request.get_json_data()
        uid = request.session.uid
        if not uid:
            return {'success': False, 'error': 'Invalid cookie.'}

        values = {
            'partner_id': params['partner_id'],
            'date_order': params.get('date_order', False),
            'currency_id': params.get('currency_id', False),
        }
        available_fields = request.env['sale.order'].fields_get()
        available_line_fields = request.env['sale.order.line'].fields_get()

        for field in params:
            if field in available_fields:
                values[field] = params[field]
        company_id = request.env['res.users'].sudo().browse(uid).company_id.id

        order_lines = []
        for product in params['order_lines']:
            line = {
                'product_id': product['product_tmpl_id'],
                'product_uom_qty': product['product_uom_qty'],
                'price_unit': product['price_unit'],
                'company_id': company_id,
            }
            for field in product:
                if field in available_line_fields:
                    line[field] = product[field]
            order_lines.append((0, 0, line))
        values['order_line'] = order_lines
        order = request.env['sale.order'].with_company(company_id).sudo().create(values)

        return {'success': True, 'order_id': order.id}
