from flask import Blueprint, request, redirect, url_for, flash
import stripe
import os
from app import db
from app import Event, Attendee, User
import json

# Create a blueprint for payments
payments_blueprint = Blueprint('payments', __name__)

# Set your Stripe webhook secret
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

# Create Stripe Checkout session
@payments_blueprint.route('/create-checkout-session/<int:event_id>', methods=['POST'])
def create_checkout_session(event_id):
    event = Event.query.get(event_id)

    if not event:
        return {"error": "Event not found"}, 404

    # Get the user who created the event
    user = User.query.get(event.user_id)

    if not user:
        return {"error": "User not found"}, 404

    # Calculate the platform fee (flat_rate as a percentage of total)
    flat_rate = user.flat_rate or 0.01  # Default to 1% if flat_rate is not set
    platform_fee_amount = int(event.ticket_price * flat_rate * 100)  # Convert to pence

    try:
        # Create a Stripe Checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'gbp',
                    'product_data': {
                        'name': event.name,
                    },
                    'unit_amount': int(event.ticket_price * 100),  # Total ticket price in pence
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('payments.success', _external=True),
            cancel_url=url_for('payments.cancel', _external=True),
            payment_intent_data={
                'application_fee_amount': platform_fee_amount,  # Platform fee
                'transfer_data': {
                    'destination': user.stripe_connect_id,  # User's connected Stripe account
                },
            },
        )
        return {"url": checkout_session.url}, 200

    except Exception as e:
        return {"error": str(e)}, 400


# Stripe Webhook
@payments_blueprint.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    print("Webhook received")
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        print(f"Webhook event constructed: {event['type']}")
    except ValueError as e:
        # Invalid payload
        print(f"Invalid payload: {e}")
        return '', 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(f"Invalid signature: {e}")
        return '', 400

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        print("Handling checkout.session.completed event")
        handle_checkout_session(session)
    else:
        print(f"Unhandled event type: {event['type']}")

    return '', 200

# Handle successful Stripe Checkout session
def handle_checkout_session(session):
    print(f"Handling session: {session.id}")
    # Retrieve the attendee ID from the session's metadata
    attendee_id = session.get('metadata', {}).get('attendee_id')
    if not attendee_id:
        print("No attendee ID found in session metadata.")
        return

    # Retrieve the attendee from the database
    attendee = Attendee.query.get(attendee_id)
    if not attendee:
        print(f"No attendee found with ID {attendee_id}.")
        return

    # Retrieve the PaymentIntent to get the charge and billing details
    payment_intent_id = session.get('payment_intent')
    if not payment_intent_id:
        print("No payment intent ID found in session.")
        return

    # Expand the latest_charge when retrieving the PaymentIntent
    payment_intent = stripe.PaymentIntent.retrieve(
        payment_intent_id,
        expand=['latest_charge']
    )

    charge = payment_intent.latest_charge
    if not charge:
        print("No charge found in payment intent.")
        return

    # Update the attendee record
    attendee.billing_details = json.dumps(charge.billing_details)
    attendee.stripe_charge_id = charge.id
    attendee.payment_status = 'succeeded'
    db.session.commit()

    print(f"Attendee {attendee_id} updated with payment details.")


# Success and cancel routes
@payments_blueprint.route('/success')
def success():
    return "Payment successful! Thank you for purchasing a ticket."

@payments_blueprint.route('/cancel')
def cancel():
    return "Payment canceled. You can try again."
