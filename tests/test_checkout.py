"""Checkout regressions. All data and Stripe responses are isolated test fixtures."""

import importlib
import contextlib
import io
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch


with patch.dict(os.environ, {
    'DATABASE_URL': 'sqlite://',
    'SECRET_KEY': 'checkout-regression-test-only',
    'STRIPE_SECRET_KEY': 'sk_test_not_a_real_key',
    'AWS_REGION': 'eu-west-2',
    'AWS_ACCESS_KEY_ID': 'testing',
    'AWS_SECRET_ACCESS_KEY': 'testing',
}), patch('dotenv.load_dotenv', return_value=False):
    application = importlib.import_module('app')


class CheckoutTests(unittest.TestCase):
    def setUp(self):
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.app = application.app
        self.app.config.update(TESTING=True)
        self.context = self.app.app_context()
        self.context.push()
        self.assertEqual(application.db.engine.url.drivername, 'sqlite')
        application.db.create_all()
        organiser = application.User(
            id=4, business_name='Test Organiser', first_name='Test', last_name='Only',
            email='organiser@example.invalid', password='not-used',
            phone_number='00000000000', house_name_or_number='0', street='Test',
            town='Test', postcode='TEST', stripe_connect_id='acct_checkout_fixture',
        )
        event = application.Event(
            id=127, user_id=4, name='Soundbath with Cacao', date='2026-11-08',
            location='Test venue', description='Checkout regression fixture',
            start_time='19:00', end_time='21:00', enforce_individual_ticket_limits=True,
        )
        ticket = application.TicketType(
            id=161, event_id=127, name='Standard', price=30, quantity=12,
        )
        application.db.session.add_all([organiser, event, ticket])
        application.db.session.commit()
        self.client = self.app.test_client()
        self.form = {
            'full_name': 'Checkout Test', 'email': 'checkout@example.invalid',
            'phone_number': '00000000000', 'quantity_161': '1',
            'accept_platform_terms': 'on',
        }

    def tearDown(self):
        application.db.session.remove()
        application.db.drop_all()
        application.db.engine.dispose()
        self.context.pop()
        self.output.__exit__(None, None, None)

    def test_paid_booking_reaches_checkout_with_card_payments_and_correct_amounts(self):
        def create_checkout(**params):
            # Reproduce Stripe's current rejection rather than allowing any kwargs.
            if 'payment_method_types' in params:
                raise application.stripe.InvalidRequestError(
                    'The payment_method_types parameter is no longer supported.',
                    param='payment_method_types',
                )
            return SimpleNamespace(id='cs_fixture', url='https://checkout.stripe.com/test-fixture')

        with patch.object(application.stripe.checkout.Session, 'create', side_effect=create_checkout) as create:
            response = self.client.post('/purchase/127', data=self.form)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, 'https://checkout.stripe.com/test-fixture')
        params = create.call_args.kwargs
        self.assertEqual(params['allowed_payment_method_types'], ['card'])
        self.assertEqual(params['mode'], 'payment')
        self.assertEqual(params['billing_address_collection'], 'required')
        self.assertEqual(params['customer_email'], self.form['email'])
        items = params['line_items']
        total = sum(item['price_data']['unit_amount'] * item['quantity'] for item in items)
        self.assertEqual(total, 3092)
        payment = params['payment_intent_data']
        self.assertEqual(payment['application_fee_amount'], 92)
        self.assertEqual(payment['on_behalf_of'], 'acct_checkout_fixture')
        self.assertEqual(payment['transfer_data']['destination'], 'acct_checkout_fixture')
        attendees = application.Attendee.query.all()
        self.assertEqual(len(attendees), 1)
        self.assertEqual(attendees[0].payment_status, 'pending')

    def test_payment_processor_failure_displays_an_error_on_the_details_page(self):
        error = application.stripe.InvalidRequestError('Internal processor detail', param='test')
        with patch.object(application.stripe.checkout.Session, 'create', side_effect=error):
            response = self.client.post('/purchase/127', data=self.form, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b'An error occurred with the payment processor. Please try again.' in response.data)
        self.assertTrue(b'role="alert"' in response.data)
        self.assertFalse(b'Internal processor detail' in response.data)

    def test_missing_terms_displays_validation_and_does_not_start_payment(self):
        self.form.pop('accept_platform_terms')
        with patch.object(application.stripe.checkout.Session, 'create') as create:
            response = self.client.post('/purchase/127', data=self.form, follow_redirects=True)
        create.assert_not_called()
        self.assertTrue(b'Terms and Conditions.' in response.data)
        self.assertTrue(b'role="alert"' in response.data)
        self.assertEqual(application.Attendee.query.count(), 0)

    def test_free_booking_still_skips_stripe(self):
        application.db.session.get(application.TicketType, 161).price = 0
        application.db.session.commit()
        with patch.object(application.stripe.checkout.Session, 'create') as create, \
                patch.object(application, 'send_confirmation_email_to_attendee'), \
                patch.object(application, 'send_confirmation_email_to_organizer'):
            response = self.client.post('/purchase/127', data=self.form)
        create.assert_not_called()
        self.assertEqual(response.status_code, 302)
        self.assertIn('/success', response.location)
        self.assertEqual(application.Attendee.query.one().payment_status, 'succeeded')


if __name__ == '__main__':
    unittest.main()
