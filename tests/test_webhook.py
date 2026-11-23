"""Exercise signed webhooks with real Stripe SDK resource objects and SQLite."""

import contextlib
import hashlib
import hmac
import io
import json
import os
import time
import unittest
from unittest.mock import patch

from test_checkout import application


class WebhookTests(unittest.TestCase):
    def setUp(self):
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.app = application.app
        self.app.config.update(TESTING=True)
        self.context = self.app.app_context()
        self.context.push()
        self.assertEqual(application.db.engine.url.drivername, 'sqlite')
        application.db.create_all()
        user = application.User(
            id=6, business_name='Quiz Organiser', first_name='Test', last_name='Only',
            email='organiser@example.invalid', password='unused', phone_number='00000000000',
            house_name_or_number='0', street='Test', town='Test', postcode='TEST',
        )
        event = application.Event(
            id=129, user_id=6, name='Quiz', date='2026-12-05', location='Test venue',
            description='Fixture', start_time='18:30', end_time='22:00',
            enforce_individual_ticket_limits=True,
        )
        ticket = application.TicketType(id=163, event_id=129, name='Quiz Player', price=12, quantity=100)
        application.db.session.add_all([user, event, ticket])
        for index in range(2):
            application.db.session.add(application.Attendee(
                event_id=129, ticket_type_id=163, session_id='local_checkout_fixture',
                full_name='Test Buyer', email='buyer@example.invalid', phone_number='00000000000',
                ticket_answers='{}', tickets_purchased=1, ticket_price_at_purchase=12,
                payment_status='pending', ticket_number='EXISTING' if index == 0 else None,
            ))
        application.db.session.commit()
        self.client = self.app.test_client()
        self.session = {
            'id': 'cs_fixture', 'object': 'checkout.session', 'payment_status': 'paid',
            'payment_intent': 'pi_fixture', 'metadata': {'session_id': 'local_checkout_fixture'},
        }
        self.intent = application.stripe.PaymentIntent.construct_from({
            'id': 'pi_fixture', 'object': 'payment_intent', 'status': 'succeeded',
            'latest_charge': {'id': 'ch_fixture', 'object': 'charge', 'paid': True,
                              'billing_details': {'name': 'Test Buyer', 'address': {'line1': 'Test', 'city': 'Test'}}},
        }, 'sk_test_fixture')
        self.secret = 'whsec_fixture_not_a_real_secret'
        self.environment = patch.dict(os.environ, {'STRIPE_WEBHOOK_SECRET': self.secret})
        self.environment.start()

    def tearDown(self):
        application.db.session.remove()
        application.db.drop_all()
        application.db.engine.dispose()
        self.context.pop()
        self.environment.stop()
        self.output.__exit__(None, None, None)

    def deliver(self, valid_signature=True):
        payload = json.dumps({'id': 'evt_fixture', 'object': 'event',
                              'type': 'checkout.session.completed', 'data': {'object': self.session}}).encode()
        timestamp = str(int(time.time()))
        signature = hmac.new(self.secret.encode(), timestamp.encode() + b'.' + payload, hashlib.sha256).hexdigest()
        if not valid_signature:
            signature = 'invalid'
        return self.client.post('/stripe-webhook', data=payload, headers={
            'Content-Type': 'application/json', 'Stripe-Signature': f't={timestamp},v1={signature}',
        })

    def test_signed_payment_updates_tickets_and_renders_both_notifications(self):
        with patch.object(application.stripe.PaymentIntent, 'retrieve', return_value=self.intent) as retrieve, \
                patch.object(application.mail, 'send') as send:
            response = self.deliver()
        self.assertEqual(response.status_code, 200)
        retrieve.assert_called_once_with('pi_fixture', expand=['latest_charge'])
        attendees = application.Attendee.query.order_by(application.Attendee.id).all()
        self.assertEqual([a.payment_status for a in attendees], ['succeeded', 'succeeded'])
        self.assertTrue(all(a.stripe_charge_id == 'ch_fixture' for a in attendees))
        self.assertTrue(all(json.loads(a.billing_details)['address']['city'] == 'Test' for a in attendees))
        self.assertEqual(attendees[0].ticket_number, 'EXISTING')
        self.assertTrue(attendees[1].ticket_number)
        self.assertEqual(send.call_count, 2)
        subjects = [call.args[0].subject for call in send.call_args_list]
        self.assertTrue(any('Your Ticket Confirmation' in s for s in subjects))
        self.assertTrue(any('New Ticket Purchase' in s for s in subjects))
        with patch.object(application.qrcode, 'make', wraps=application.qrcode.make):
            success = self.client.get('/success?session_id=local_checkout_fixture')
        self.assertEqual(success.status_code, 200)

    def test_stripe_retry_does_not_repeat_notifications_or_change_ticket_numbers(self):
        with patch.object(application.stripe.PaymentIntent, 'retrieve', return_value=self.intent), \
                patch.object(application.mail, 'send') as send:
            self.assertEqual(self.deliver().status_code, 200)
            numbers = [a.ticket_number for a in application.Attendee.query.order_by(application.Attendee.id)]
            self.assertEqual(self.deliver().status_code, 200)
        self.assertEqual(send.call_count, 2)
        self.assertEqual(numbers, [a.ticket_number for a in application.Attendee.query.order_by(application.Attendee.id)])

    def test_unpaid_checkout_never_confirms_tickets(self):
        self.session['payment_status'] = 'unpaid'
        with patch.object(application.stripe.PaymentIntent, 'retrieve') as retrieve, \
                patch.object(application.mail, 'send') as send:
            self.assertEqual(self.deliver().status_code, 200)
        retrieve.assert_not_called()
        send.assert_not_called()
        self.assertTrue(all(a.payment_status == 'pending' for a in application.Attendee.query.all()))

    def test_invalid_signature_does_not_process_a_booking(self):
        with patch.object(application.stripe.PaymentIntent, 'retrieve') as retrieve:
            self.assertEqual(self.deliver(valid_signature=False).status_code, 400)
        retrieve.assert_not_called()

    def test_unsuccessful_payment_intent_does_not_confirm_tickets(self):
        self.intent.status = 'requires_payment_method'
        self.intent.latest_charge.paid = False
        with patch.object(application.stripe.PaymentIntent, 'retrieve', return_value=self.intent), \
                patch.object(application.mail, 'send') as send:
            self.assertEqual(self.deliver().status_code, 200)
        send.assert_not_called()
        self.assertTrue(all(a.payment_status == 'pending' for a in application.Attendee.query.all()))

    def test_paid_checkout_without_charge_billing_uses_customer_details(self):
        self.intent.latest_charge.billing_details = None
        self.session['customer_details'] = {'name': 'Test Buyer', 'address': {'city': 'Test'}}
        with patch.object(application.stripe.PaymentIntent, 'retrieve', return_value=self.intent), \
                patch.object(application.mail, 'send') as send:
            self.assertEqual(self.deliver().status_code, 200)
        self.assertEqual(send.call_count, 2)
        self.assertTrue(all(a.payment_status == 'succeeded' for a in application.Attendee.query.all()))

    def test_unknown_local_reference_is_safely_acknowledged(self):
        self.session['metadata']['session_id'] = 'not_a_booking'
        with patch.object(application.stripe.PaymentIntent, 'retrieve') as retrieve:
            self.assertEqual(self.deliver().status_code, 200)
        retrieve.assert_not_called()


if __name__ == '__main__':
    unittest.main()
