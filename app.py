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
    billing_details = db.Column(db.Text, nullable=True)
    stripe_charge_id = db.Column(db.String(255), nullable=True)
    payment_status = db.Column(db.String(50), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    full_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(50), nullable=False)
    ticket_price_at_purchase = db.Column(db.Float, nullable=False)
    # Remove ticket_answers field
    # tickets_purchased field should already be removed as per previous changes

    # Relationship to tickets
    tickets = db.relationship('Ticket', back_populates='attendee', lazy=True)



class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attendee_id = db.Column(db.Integer, db.ForeignKey('attendee.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    ticket_answers = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    attendee = db.relationship('Attendee', back_populates='tickets')
    event = db.relationship('Event', backref=db.backref('tickets', lazy=True))



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
    filter_value = request.args.get('filter', 'all')

    user_events = Event.query.filter_by(user_id=current_user.id)

    # Convert string dates to datetime for comparison
    def str_to_date(date_str):
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')  # Adjust the format if your date strings differ
        except ValueError:
            return None

    if filter_value == 'upcoming':
        user_events = [event for event in user_events if str_to_date(event.date) and str_to_date(event.date) >= datetime.now()]
    elif filter_value == 'past':
        user_events = [event for event in user_events if str_to_date(event.date) and str_to_date(event.date) < datetime.now()]

    total_tickets_sold = 0
    total_revenue = 0

    event_data = []
    for event in user_events:
        attendees = Attendee.query.filter_by(event_id=event.id).all()
        tickets_sold = sum([len(attendee.tickets) for attendee in attendees])
        tickets_remaining = event.ticket_quantity - tickets_sold
        
        # Calculate revenue based on the ticket price at purchase
        event_revenue = sum([len(attendee.tickets) * attendee.ticket_price_at_purchase for attendee in attendees])

        total_tickets_sold += tickets_sold
        total_revenue += event_revenue

        event_status = "Upcoming" if str_to_date(event.date) >= datetime.now() else "Past"

        event_data.append({
            'name': event.name,
            'date': event.date,
            'location': event.location,
            'tickets_sold': tickets_sold,
            'ticket_quantity': event.ticket_quantity,
            'tickets_remaining': tickets_remaining,
            'total_revenue': event_revenue,
            'status': event_status,
            'id': event.id
        })

    return render_template('dashboard.html', 
                           events=event_data, 
                           total_revenue=total_revenue, 
                           total_tickets_sold=total_tickets_sold, 
                           user=current_user)


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
        # Collect form data
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        number_of_tickets = int(request.form.get('number_of_tickets', 1))

        # Validate required fields
        if not all([full_name, email, phone_number]):
            flash('Please fill in all required fields.')
            return redirect(url_for('purchase', event_id=event_id))

        if number_of_tickets > event.ticket_quantity:
            flash('Requested number of tickets exceeds available tickets.')
            return redirect(url_for('purchase', event_id=event_id))

        # Validate terms acceptance
        if not request.form.get('accept_organizer_terms'):
            flash('You must accept the event organizer\'s Terms and Conditions.')
            return redirect(url_for('purchase', event_id=event_id))
        if not request.form.get('accept_platform_terms'):
            flash('You must accept the platform\'s Terms and Conditions.')
            return redirect(url_for('purchase', event_id=event_id))

        # Create an attendee record without tickets_purchased
        attendee = Attendee(
            event_id=event_id,
            payment_status='pending',
            full_name=full_name,
            email=email,
            phone_number=phone_number,
            ticket_price_at_purchase=event.ticket_price,
            created_at=datetime.utcnow()
        )
        db.session.add(attendee)
        db.session.commit()

        # Store the attendee ID
        attendee_id = attendee.id

        # Collect answers and create individual tickets
        for i in range(number_of_tickets):
            ticket_answers = {}
            for q_index, question in enumerate(all_questions):
                answer_key = f'ticket_{i}_question_{q_index}'
                answer = request.form.get(answer_key)
                if not answer:
                    flash(f'Please answer all questions for Ticket {i + 1}.')
                    return redirect(url_for('purchase', event_id=event_id))
                ticket_answers[question] = answer

            # Create a Ticket record
            ticket = Ticket(
                attendee_id=attendee.id,
                event_id=event_id,
                ticket_answers=json.dumps(ticket_answers),
                created_at=datetime.utcnow()
            )
            db.session.add(ticket)

        db.session.commit()

        # Calculate the ticket price in pence
        ticket_price_pence = int(event.ticket_price * 100)
        total_ticket_price_pence = ticket_price_pence * number_of_tickets

        # Calculate platform fee (2% of ticket price)
        platform_fee_pence = int(total_ticket_price_pence * 0.02)

        # Calculate Stripe fee (2.9% of total amount + 30p per ticket)
        stripe_fee_pence = int((total_ticket_price_pence + platform_fee_pence) * 0.029) + (30 * number_of_tickets)

        # Total booking fee
        booking_fee_pence = platform_fee_pence + stripe_fee_pence

        # Total amount to charge the customer
        total_amount_pence = total_ticket_price_pence + booking_fee_pence

        try:
            # Create a Stripe Checkout session with two line items
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': 'gbp',
                            'product_data': {
                                'name': event.name,
                            },
                            'unit_amount': ticket_price_pence,
                        },
                        'quantity': number_of_tickets,
                    },
                    {
                        'price_data': {
                            'currency': 'gbp',
                            'product_data': {
                                'name': 'Booking Fee',
                                },
                                'unit_amount': booking_fee_pence // number_of_tickets,
                            },
                            'quantity': number_of_tickets,
                        }
                    ],
                    mode='payment',
                    success_url=url_for('success', attendee_id=attendee_id, _external=True),
                    cancel_url=url_for('cancel', attendee_id=attendee_id, _external=True),
                    metadata={
                        'attendee_id': attendee_id
                    },
                    payment_intent_data={
                        'application_fee_amount': platform_fee_pence,
                        'on_behalf_of': user.stripe_connect_id,
                        'transfer_data': {
                            'destination': user.stripe_connect_id,
                        },
                    },
                    billing_address_collection='required',
                    customer_email=email
                )

            return redirect(checkout_session.url)

        except Exception as e:
            print(f"Error creating checkout session: {str(e)}")
            flash('An error occurred while processing your payment.')
            return redirect(url_for('purchase', event_id=event_id))

    else:
        # GET request: render the purchase page
        platform_terms_link = 'https://your-platform-domain.com/terms-and-conditions'
        organizer_terms_link = user.terms or '#'

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
    attendee = Attendee.query.get(attendee_id)
    if not attendee:
        print(f"No attendee found with ID {attendee_id}.")
        return

    # Retrieve the PaymentIntent
    payment_intent_id = session.get('payment_intent')
    payment_intent = stripe.PaymentIntent.retrieve(
        payment_intent_id,
        expand=['latest_charge']
    )
    charge = payment_intent.latest_charge

    # Serialize billing_details to JSON string
    attendee.billing_details = json.dumps(charge.billing_details)
    attendee.stripe_charge_id = charge.id
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

    # Fetch attendees with successful payments
    attendees = Attendee.query.filter_by(event_id=event_id, payment_status='succeeded').all()

    # Prepare data to pass to the template without modifying the model
    attendee_data = []
    for attendee in attendees:
        # Deserialize billing_details JSON string back to a dictionary
        billing_details = json.loads(attendee.billing_details) if attendee.billing_details else {}

        # Deserialize ticket_answers for each ticket
        tickets = []
        for ticket in attendee.tickets:
            ticket_answers = json.loads(ticket.ticket_answers) if ticket.ticket_answers else {}
            tickets.append(ticket_answers)

        attendee_data.append({
            'id': attendee.id,
            'full_name': attendee.full_name,
            'email': attendee.email,
            'phone_number': attendee.phone_number,
            'ticket_price_at_purchase': attendee.ticket_price_at_purchase,
            'created_at': attendee.created_at,
            'billing_details': billing_details,
            'tickets': tickets,
        })

    return render_template('view_attendees.html', event=event, attendees=attendee_data)




@app.route('/delete_event/<int:event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash('Event deleted successfully!')
    return redirect(url_for('dashboard'))


@app.route('/edit_event/<int:event_id>', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)

    if request.method == 'POST':
        event.name = request.form['name']
        event.date = request.form['date']
        event.location = request.form['location']
        event.ticket_quantity = request.form['ticket_quantity']
        event.ticket_price = request.form['ticket_price']
        db.session.commit()
        flash('Event updated successfully!')
        return redirect(url_for('dashboard'))

    return render_template('edit_event.html', event=event)

@app.route('/event/<int:event_id>/attendee/<int:attendee_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_attendee(event_id, attendee_id):
    event = Event.query.get_or_404(event_id)
    attendee = Attendee.query.get_or_404(attendee_id)

    # Ensure the current user is the organizer of the event
    if event.user_id != current_user.id:
        flash("You don't have permission to edit this attendee.")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # Update attendee information
        attendee.full_name = request.form.get('full_name')
        attendee.email = request.form.get('email')
        attendee.phone_number = request.form.get('phone_number')

        # Retrieve the desired number of tickets
        new_ticket_count = int(request.form.get('tickets_purchased', len(attendee.tickets)))
        current_ticket_count = len(attendee.tickets)
        difference = new_ticket_count - current_ticket_count

        # Fetch all questions for the event
        user = event.user
        default_questions = DefaultQuestion.query.filter_by(user_id=user.id).all()
        default_question_texts = [dq.question for dq in default_questions]

        custom_questions = []
        for i in range(1, 11):
            question = getattr(event, f'custom_question_{i}')
            if question:
                custom_questions.append(question)

        all_questions = default_question_texts + custom_questions

        if difference > 0:
            # Add new tickets
            for i in range(difference):
                ticket_answers = {}
                for q_index, question in enumerate(all_questions):
                    answer_key = f'ticket_{current_ticket_count + i}_question_{q_index}'
                    answer = request.form.get(answer_key)
                    if not answer:
                        flash(f'Please answer all questions for Ticket {current_ticket_count + i + 1}.')
                        return redirect(url_for('edit_attendee', event_id=event_id, attendee_id=attendee_id))
                    ticket_answers[question] = answer

                new_ticket = Ticket(
                    attendee_id=attendee.id,
                    event_id=event_id,
                    ticket_answers=json.dumps(ticket_answers),
                    created_at=datetime.utcnow()
                )
                db.session.add(new_ticket)

        elif difference < 0:
            # Remove tickets
            tickets_to_remove = attendee.tickets[difference:]  # Remove the last N tickets
            for ticket in tickets_to_remove:
                db.session.delete(ticket)

        # Update existing ticket answers
        for i, ticket in enumerate(attendee.tickets):
            ticket_answers = {}
            for q_index, question in enumerate(all_questions):
                answer_key = f'ticket_{i}_question_{q_index}'
                answer = request.form.get(answer_key)
                if not answer:
                    flash(f'Please answer all questions for Ticket {i + 1}.')
                    return redirect(url_for('edit_attendee', event_id=event_id, attendee_id=attendee_id))
                ticket_answers[question] = answer
            ticket.ticket_answers = json.dumps(ticket_answers)

        db.session.commit()
        flash('Attendee information updated successfully!')
        return redirect(url_for('view_attendees', event_id=event_id))

    # Pre-fill the form with the attendee's current information
    attendee_data = {
        'full_name': attendee.full_name,
        'email': attendee.email,
        'phone_number': attendee.phone_number,
        'tickets_purchased': len(attendee.tickets),
    }

    # Fetch default and custom questions
    user = event.user
    default_questions = DefaultQuestion.query.filter_by(user_id=user.id).all()
    default_question_texts = [dq.question for dq in default_questions]

    custom_questions = []
    for i in range(1, 11):
        question = getattr(event, f'custom_question_{i}')
        if question:
            custom_questions.append(question)

    all_questions = default_question_texts + custom_questions

    return render_template('edit_attendee.html', event=event, attendee=attendee, attendee_data=attendee_data, questions=all_questions)


@app.route('/event/<int:event_id>/attendee/<int:attendee_id>/delete', methods=['POST'])
@login_required
def delete_attendee(event_id, attendee_id):
    event = Event.query.get_or_404(event_id)
    attendee = Attendee.query.get_or_404(attendee_id)

    # Ensure the current user is the organizer of the event
    if event.user_id != current_user.id:
        flash("You don't have permission to delete this attendee.")
        return redirect(url_for('dashboard'))

    db.session.delete(attendee)
    db.session.commit()
    flash('Attendee deleted successfully!')
    return redirect(url_for('view_attendees', event_id=event_id))

@app.route('/event/<int:event_id>/ticket/<int:ticket_id>/delete', methods=['POST'])
@login_required
def delete_ticket(event_id, ticket_id):
    event = Event.query.get_or_404(event_id)
    ticket = Ticket.query.get_or_404(ticket_id)

    # Ensure the current user is the organizer of the event
    if event.user_id != current_user.id:
        flash("You don't have permission to delete this ticket.")
        return redirect(url_for('view_attendees', event_id=event_id))

    # Delete the ticket
    db.session.delete(ticket)
    db.session.commit()

    flash('Ticket deleted successfully!')
    return redirect(url_for('view_attendees', event_id=event_id))
