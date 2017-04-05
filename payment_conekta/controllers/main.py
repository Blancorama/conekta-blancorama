# -*- coding: utf-8 -*-
# © 2016 Jarsa Sistemas, S.A. de C.V.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

from openerp import http, _
from openerp.http import request
from datetime import datetime
from time import mktime
_logger = logging.getLogger(__name__)
try:
    import conekta
except (ImportError, IOError) as err:
    _logger.debug(err)


class ConektaController(http.Controller):

    def conekta_validate_data(self, data):
        res = False
        tx_obj = request.env['payment.transaction']
        res = tx_obj.sudo().form_feedback(data, 'conekta')
        return res

    def create_params(self, acquirer):
        so_id = request.session['sale_order_id']
        so = request.env['sale.order'].sudo().search([('id', '=', so_id)])
        params = {}
        params['description'] = _('%s Order %s' % (so.company_id.name,
                                                   so.name))
        params['amount'] = int(so.amount_total * 100)
        params['currency'] = so.currency_id.name
        params['reference_id'] = so.name
        if acquirer == 'conekta':
            params['card'] = request.session['conekta_token']
        if acquirer == 'conekta_oxxo':
            params['cash'] = {'type': 'oxxo'}
            # TODO: ADD expires_at
        details = params['details'] = {}
        details['name'] = so.partner_id.name
        details['phone'] = so.partner_id.phone
        details['email'] = so.partner_id.email
        customer = details['customer'] = {}
        if request.session['uid'] is not None:
            # TODO: "offline_payments" and "score"
            create_at = so.partner_id.create_date
            create_date = mktime(datetime.strptime(
                create_at, '%Y-%m-%d %H:%M:%S').timetuple())
            write_at = so.partner_id.write_date
            updated_date = mktime(datetime.strptime(
                write_at, '%Y-%m-%d %H:%M:%S').timetuple())
            customer['logged_in'] = True
            customer['successful_purchases'] = so.partner_id.sale_order_count
            customer['created_at'] = str(create_date)
            customer['updated_at'] = str(updated_date)
        else:
            customer['logged_in'] = False
        line_items = details['line_items'] = []
        for order_line in so.order_line:
            item = {}
            line_items.append(item)
            item['name'] = order_line.product_id.name
            item['description'] = (order_line.product_id.description_sale or "")
            item['unit_price'] = int(order_line.price_unit * 100)
            item['quantity'] = order_line.product_uom_qty
            item['sku'] = order_line.product_id.default_code
            item['category'] = order_line.product_id.categ_id.name
        

        billing_address = details['billing_address'] = {}
        billing_address['street1'] = so.partner_invoice_id.street2
        billing_address['street2'] = so.partner_invoice_id.street2
        billing_address['city'] = so.partner_invoice_id.city
        billing_address['state'] = (so.partner_invoice_id.state_id.code or "")
        billing_address['zip'] = so.partner_invoice_id.zip
        billing_address['country'] = so.partner_invoice_id.country_id.code
        billing_address['tax_id'] = so.partner_invoice_id.vat
        billing_address['company_name'] = (so.partner_invoice_id.parent_name or
                                           so.partner_invoice_id.name)
        billing_address['phone'] = so.partner_invoice_id.phone
        billing_address['email'] = so.partner_invoice_id.email

        shipping_address = details['shipping_address'] = {}
        shipping_address['street1'] = so.partner_shipping_id.street2
        shipping_address['street2'] = so.partner_shipping_id.street2
        shipping_address['city'] = so.partner_shipping_id.city
        shipping_address['state'] = (so.partner_shipping_id.state_id.code or "")
        shipping_address['zip'] = so.partner_shipping_id.zip
        shipping_address['country'] = so.partner_shipping_id.country_id.code
        shipping_address['tax_id'] = so.partner_shipping_id.vat
        shipping_address['company_name'] = (so.partner_shipping_id.parent_name or
                                           so.partner_shipping_id.name)
        shipping_address['phone'] = so.partner_shipping_id.phone
        shipping_address['email'] = so.partner_shipping_id.email

        shipment = details['shipment'] = {}
        shipment['carrier'] = 'Estafeta' #so.carrier_id.name
        shipment['service'] = "Internacional"
        shipment['price'] = '120' #so.carrier_id.fixed_price
        shipment['tracking_id'] = "XXYYZZ-9990000"
        shipment['address'] = shipping_address

        return params

    @http.route('/payment/conekta/charge', type='json',
                auth='public', website=True)
    def charge_create(self, token):
        request.session['conekta_token'] = token
        payment_acquirer = request.env['payment.acquirer']
        conekta_acq = payment_acquirer.sudo().search(
            [('provider', '=', 'conekta')])
        # conekta.api_key = conekta_acq.conekta_private_key
        conekta.api_key = 'key_8dtZqHSeqQWXDBYD9r7osg'
        params = self.create_params('conekta')
        try:

            response = conekta.Charge.create(params)
            
        except conekta.ConektaError as error:
            return error.message['message_to_purchaser']
        self.conekta_validate_data(response)
        return True