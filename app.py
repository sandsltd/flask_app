from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import os
from flask_migrate import Migrate
import uuid
import string
import random
import stripe
from flask_cors import CORS
import json
from flask import request, redirect, url_for, render_template, flash
from urllib.parse import urlparse
from datetime import datetime
import json



app = Flask(__name__)

# Enable CORS for all routes and origins
CORS(app)  # This will allow all origins by default, but you can restrict it if needed.

# Set your Stripe secret key from the environment variable
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

app.secret_key = 'supersecretkey'
login_manager = LoginManager()
login_manager.init_app(app)

STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    unique_id = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    business_name = db.Column(db.String(120), nullable=False)
    website_url = db.Column(db.String(200), nullable=True)  # Optional
    vat_number = db.Column(db.String(50), nullable=True)  # Optional
    stripe_connect_id = db.Column(db.String(120), nullable=False)

    # Address fields
    house_name_or_number = db.Column(db.String(255), nullable=False)
    street = db.Column(db.String(255), nullable=False)
    locality = db.Column(db.String(255), nullable=True)
    town = db.Column(db.String(100), nullable=False)
    postcode = db.Column(db.String(20), nullable=False)

    terms = db.Column(db.String(255), nullable=True)  # Changed from False to True

    # Default flat_rate set to 0.01
    flat_rate = db.Column(db.Float, nullable=True, default=0.01)  # Flat rate with default value

    # Optional promotional fields
    promo_rate = db.Column(db.Float, nullable=True)  # Promotional rate
    promo_rate_date_end = db.Column(db.Date, nullable=True)

    events = db.relationship('Event', backref='user', lazy=True)


# Event model
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    start_time = db.Column(db.String(50), nullable=False)
    end_time = db.Column(db.String(50), nullable=False)
    ticket_quantity = db.Column(db.Integer, nullable=False)
    ticket_price = db.Column(db.Float, nullable=False)
    event_image = db.Column(db.String(300), nullable=True)  # Optional event image URL

    # Custom questions
    custom_question_1 = db.Column(db.String(255), nullable=True)
    custom_question_2 = db.Column(db.String(255), nullable=True)
    custom_question_3 = db.Column(db.String(255), nullable=True)
    custom_question_4 = db.Column(db.String(255), nullable=True)
    custom_question_5 = db.Column(db.String(255), nullable=True)
    custom_question_6 = db.Column(db.String(255), nullable=True)
    custom_question_7 = db.Column(db.String(255), nullable=True)
    custom_question_8 = db.Column(db.String(255), nullable=True)
    custom_question_9 = db.Column(db.String(255), nullable=True)
    custom_question_10 = db.Column(db.String(255), nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Attendee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    ticket_answers = db.Column(db.Text, nullable=False)
    billing_details = db.Column(db.Text, nullable=True)
    stripe_charge_id = db.Column(db.String(255), nullable=True)
    payment_status = db.Column(db.String(50), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to the Event model
    event = db.relationship('Event', backref=db.backref('attendees', lazy=True))


class DefaultQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question = db.Column(db.String(255), nullable=False)

# Generate a random unique ID with 15 characters
def generate_unique_id():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(15))

# User Loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes for login, logout, registration
@app.route('/')
def home():
    return "Hello, World!"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user_events = Event.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', events=user_events, user=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    try:
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            phone_number = request.form['phone_number']
            business_name = request.form['business_name']
            website_url = request.form.get('website_url', '')  # Optional
            vat_number = request.form.get('vat_number', '')  # Optional
            house_name_or_number = request.form['house_name_or_number']
            street = request.form['street']
            locality = request.form.get('locality', '')  # Optional
            town = request.form['town']
            postcode = request.form['postcode']
            
            # Extract the Stripe Connect Account ID from the form
            stripe_connect_id = request.form['stripe_connect_id']

            flat_rate = request.form.get('flat_rate', type=float)  # Optional
            promo_rate = request.form.get('promo_rate', type=float)  # Optional
            promo_rate_date_end = request.form.get('promo_rate_date_end')  # Optional

            user = User.query.filter_by(email=email).first()
            if user:
                return render_template('register.html', error="Email already in use")

            unique_id = generate_unique_id()
            hashed_password = generate_password_hash(password)

            new_user = User(
                unique_id=unique_id,
                email=email,
                password=hashed_password,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                business_name=business_name,
                website_url=website_url,
                vat_number=vat_number,
                stripe_connect_id=stripe_connect_id,  # Save the Stripe Connect ID from the form
                house_name_or_number=house_name_or_number,
                street=street,
                locality=locality,
                town=town,
                postcode=postcode,
                flat_rate=flat_rate,
                promo_rate=promo_rate,
                promo_rate_date_end=promo_rate_date_end,
            )

            db.session.add(new_user)
            db.session.commit()

            flash('Account created successfully! Please log in.')
            return redirect(url_for('login'))

    except Exception as e:
        print(f"Error during registration: {str(e)}")
        return render_template('register.html', error="An error occurred during registration.")

    return render_template('register.html')


# Event creation route
@app.route('/create_event', methods=['GET', 'POST'])
@login_required
def create_event():
    if request.method == 'POST':
        name = request.form['name']
        date = request.form['date']
        location = request.form['location']
        description = request.form['description']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        ticket_quantity = request.form['ticket_quantity']
        ticket_price = request.form['ticket_price']

        # Capture custom questions for the event
        custom_question_1 = request.form.get('custom_question_1')
        custom_question_2 = request.form.get('custom_question_2')
        custom_question_3 = request.form.get('custom_question_3')
        custom_question_4 = request.form.get('custom_question_4')
        custom_question_5 = request.form.get('custom_question_5')
        custom_question_6 = request.form.get('custom_question_6')
        custom_question_7 = request.form.get('custom_question_7')
        custom_question_8 = request.form.get('custom_question_8')
        custom_question_9 = request.form.get('custom_question_9')
        custom_question_10 = request.form.get('custom_question_10')

        # Fetch default questions from the database
        default_questions = DefaultQuestion.query.filter_by(user_id=current_user.id).all()

        # We can now add these default questions to the custom ones
        default_question_texts = [dq.question for dq in default_questions]

        # Create the new event
        new_event = Event(
            name=name,
            date=date,
            location=location,
            description=description,
            start_time=start_time,
            end_time=end_time,
            ticket_quantity=ticket_quantity,
            ticket_price=ticket_price,
            custom_question_1=custom_question_1 or (default_question_texts[0] if len(default_question_texts) > 0 else None),
            custom_question_2=custom_question_2 or (default_question_texts[1] if len(default_question_texts) > 1 else None),
            custom_question_3=custom_question_3 or (default_question_texts[2] if len(default_question_texts) > 2 else None),
            custom_question_4=custom_question_4 or (default_question_texts[3] if len(default_question_texts) > 3 else None),
            custom_question_5=custom_question_5 or (default_question_texts[4] if len(default_question_texts) > 4 else None),
            custom_question_6=custom_question_6 or (default_question_texts[5] if len(default_question_texts) > 5 else None),
            custom_question_7=custom_question_7 or (default_question_texts[6] if len(default_question_texts) > 6 else None),
            custom_question_8=custom_question_8 or (default_question_texts[7] if len(default_question_texts) > 7 else None),
            custom_question_9=custom_question_9 or (default_question_texts[8] if len(default_question_texts) > 8 else None),
            custom_question_10=custom_question_10 or (default_question_texts[9] if len(default_question_texts) > 9 else None),
            user_id=current_user.id
        )

        db.session.add(new_event)
        db.session.commit()

        flash('Event created successfully!')
        return redirect(url_for('dashboard'))

    # Pass the default questions to the form so they can be displayed
    default_questions = DefaultQuestion.query.filter_by(user_id=current_user.id).all()
    return render_template('create_event.html', default_questions=default_questions)



# Reset database
@app.route('/reset_db')
def reset_db():
    try:
        db.drop_all()
        db.create_all()
        return "Database reset and tables recreated!"
    except Exception as e:
        return f"An error occurred during reset: {str(e)}"

@app.route('/embed/<unique_id>')
def embed_events(unique_id):
    user = User.query.filter_by(unique_id=unique_id).first()

    if not user:
        return "User not found", 404

    user_events = Event.query.filter_by(user_id=user.id).all()

    events_html = '<ul>'
    for event in user_events:
        events_html += f'''
        <li>
            <strong>{event.name}</strong><br>
            Date: {event.date}<br>
            Location: {event.location}<br>
            Description: {event.description}<br>
            Time: {event.start_time} - {event.end_time}<br>
            Ticket Quantity: {event.ticket_quantity}<br>
            Ticket Price: £{event.ticket_price}<br>
            <button onclick="window.location.href='https://flask-app-2gp0.onrender.com/purchase/{event.id}'">Buy Ticket</button>
        </li><br>
        '''
    events_html += '</ul>'

    response = f"document.write(`{events_html}`);"
    return response, 200, {'Content-Type': 'application/javascript'}


# Stripe Checkout session creation
@app.route('/create-checkout-session/<int:event_id>', methods=['POST'])
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
            success_url=url_for('success', _external=True),
            cancel_url=url_for('cancel', _external=True),
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



# Success and cancel routes
@app.route('/success')
def success():
    return "Payment successful! Thank you for purchasing a ticket."

@app.route('/cancel')
def cancel():
    return "Payment canceled. You can try again."

if __name__ == "__main__":
    app.run(debug=True)

@app.route('/manage-default-questions', methods=['GET', 'POST'])
@login_required
def manage_default_questions():
    if request.method == 'POST':
        questions = request.form.getlist('questions[]')  # Get all questions from the form
        terms_link = request.form.get('terms_link')  # Get the terms and conditions link

        # First, delete existing default questions for this user
        DefaultQuestion.query.filter_by(user_id=current_user.id).delete()

        # Then, add the new questions
        for question in questions:
            if question.strip():  # Avoid adding empty questions
                new_question = DefaultQuestion(user_id=current_user.id, question=question)
                db.session.add(new_question)
        
        # Update the user's terms and conditions link
        current_user.terms = terms_link

        db.session.commit()
        flash('Default questions and Terms and Conditions updated successfully!')

    # Retrieve current default questions for the user
    default_questions = DefaultQuestion.query.filter_by(user_id=current_user.id).all()
    return render_template('manage_default_questions.html', questions=default_questions, user=current_user)


@app.route('/purchase/<int:event_id>', methods=['GET', 'POST'])
def purchase(event_id):
    event = Event.query.get(event_id)
    if not event:
        return "Event not found", 404

    user = User.query.get(event.user_id)
    if not user:
        return "Event organizer not found", 404

    # Fetch default and custom questions
    default_questions = DefaultQuestion.query.filter_by(user_id=user.id).all()
    default_question_texts = [dq.question for dq in default_questions]

    custom_questions = []
    for i in range(1, 11):
        question = getattr(event, f'custom_question_{i}')
        if question:
            custom_questions.append(question)

    all_questions = default_question_texts + custom_questions

    if request.method == 'POST':
        # Process the form data
        number_of_tickets = int(request.form['number_of_tickets'])
        
        if number_of_tickets > event.ticket_quantity:
            flash('Requested number of tickets exceeds available tickets.')
            return redirect(url_for('purchase', event_id=event_id))
        
        # Validate that the terms checkboxes are checked
        if not request.form.get('accept_organizer_terms'):
            flash('You must accept the event organizer\'s Terms and Conditions.')
            return redirect(url_for('purchase', event_id=event_id))
        if not request.form.get('accept_platform_terms'):
            flash('You must accept the platform\'s Terms and Conditions.')
            return redirect(url_for('purchase', event_id=event_id))
        
        # Collect answers for each ticket
        tickets = []
        for i in range(number_of_tickets):
            ticket_answers = {}
            for q_index, question in enumerate(all_questions):
                answer_key = f'ticket_{i}_question_{q_index}'
                answer = request.form.get(answer_key)
                if not answer:
                    flash(f'Please answer all questions for Ticket {i + 1}.')
                    return redirect(url_for('purchase', event_id=event_id))
                ticket_answers[question] = answer
            tickets.append(ticket_answers)

        # Create an attendee record with payment_status 'pending'
        attendee = Attendee(
            event_id=event_id,
            ticket_answers=json.dumps(tickets),
            payment_status='pending'
        )
        db.session.add(attendee)
        db.session.commit()

        # Store the attendee ID to pass to Stripe
        attendee_id = attendee.id

        # Calculate total amount
        total_amount = event.ticket_price * number_of_tickets

        # Calculate platform fee
        flat_rate = user.flat_rate or 0.01  # Default to 1% if not set
        platform_fee_amount = int(total_amount * flat_rate * 100)  # Convert to pence

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'gbp',
                        'product_data': {
                            'name': event.name,
                        },
                        'unit_amount': int(event.ticket_price * 100),
                    },
                    'quantity': number_of_tickets,
                }],
                mode='payment',
                success_url=url_for('success', attendee_id=attendee_id, _external=True),
                cancel_url=url_for('cancel', attendee_id=attendee_id, _external=True),
                metadata={
                    'attendee_id': attendee_id
                },
                payment_intent_data={
                    'application_fee_amount': platform_fee_amount,
                    'transfer_data': {
                        'destination': user.stripe_connect_id,
                    },
                    # You can remove 'metadata' from here if it's not needed
                },
                billing_address_collection='required',
                customer_email=request.form.get('email')  # Ensure you collect email in your form
            )

            return redirect(checkout_session.url)

        except Exception as e:
            print(f"Error creating checkout session: {str(e)}")
            flash('An error occurred while processing your payment.')
            return redirect(url_for('purchase', event_id=event_id))

    else:
        # GET request: render the purchase page
        # Ensure you pass organizer_terms_link and platform_terms_link
        platform_terms_link = 'https://your-platform-domain.com/terms-and-conditions'
        organizer_terms_link = user.terms or '#'

        # Ensure the URL is absolute
        from urllib.parse import urlparse

        def ensure_absolute_url(url):
            if url:
                parsed_url = urlparse(url)
                if not parsed_url.scheme:
                    return 'https://' + url
                else:
                    return url
            else:
                return '#'

        organizer_terms_link = ensure_absolute_url(organizer_terms_link)

        return render_template(
            'purchase.html',
            event=event,
            questions=all_questions,
            organizer_terms_link=organizer_terms_link,
            platform_terms_link=platform_terms_link
        )
    
@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    print("Webhook received")
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
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

    # Expand the charges when retrieving the PaymentIntent
    payment_intent = stripe.PaymentIntent.retrieve(
        payment_intent_id,
        expand=['charges']
    )
    charges = payment_intent.charges.data
    if not charges:
        print("No charges found in payment intent.")
        return

    charge = charges[0]  # Assuming one charge per payment intent

    # Update the attendee record
    attendee.billing_details = json.dumps(charge.get('billing_details', {}))
    attendee.stripe_charge_id = charge.get('id')
    attendee.payment_status = 'succeeded'
    db.session.commit()

    print(f"Attendee {attendee_id} updated with payment details.")



@app.route('/event/<int:event_id>/attendees')
@login_required
def view_attendees(event_id):
    event = Event.query.get(event_id)
    if not event or event.user_id != current_user.id:
        flash("Event not found or you don't have permission to view it.")
        return redirect(url_for('dashboard'))

    attendees = Attendee.query.filter_by(event_id=event_id, payment_status='succeeded').all()

    # Parse the JSON fields
    for attendee in attendees:
        # Parse ticket_answers JSON
        if attendee.ticket_answers:
            attendee.ticket_answers = json.loads(attendee.ticket_answers)
        else:
            attendee.ticket_answers = []

        # Parse billing_details JSON
        if attendee.billing_details:
            attendee.billing_details = json.loads(attendee.billing_details)
        else:
            attendee.billing_details = {}

    return render_template('view_attendees.html', event=event, attendees=attendees)