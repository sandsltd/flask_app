from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import os
from flask_migrate import Migrate
import uuid
import string
import random
from werkzeug.security import generate_password_hash
from flask import request, redirect, url_for, flash, render_template
import stripe
from flask import jsonify

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')


app = Flask(__name__)
app.secret_key = 'supersecretkey'
login_manager = LoginManager()
login_manager.init_app(app)


from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return "Hello, World!"



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Fetch the user by email
        user = User.query.filter_by(email=email).first()
        if user:
            print(f"User found: {user.email}")
        else:
            print("User not found")

        if user and check_password_hash(user.password, password):
            print("Password check successful")
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password')
            print("Password check failed")
    
    return render_template('login.html')



@app.route('/dashboard')
@login_required
def dashboard():
    user_events = Event.query.filter_by(user_id=current_user.id).all()
    
    # Pass current_user (which contains user details like unique_id) to the template
    return render_template('dashboard.html', events=user_events, user=current_user)




@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    unique_id = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(120), unique=True, nullable=False)  # Using email as the unique login field
    password = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(120), nullable=False)         # First name
    last_name = db.Column(db.String(120), nullable=False)          # Last name
    phone_number = db.Column(db.String(20), nullable=False)
    business_name = db.Column(db.String(120), nullable=False)
    website_url = db.Column(db.String(200), nullable=True)         # Optional
    vat_number = db.Column(db.String(50), nullable=True)           # Optional
    stripe_connect_id = db.Column(db.String(120), nullable=False)

    # Address fields
    house_name_or_number = db.Column(db.String(255), nullable=False)  # House name/number
    street = db.Column(db.String(255), nullable=False)                 # Street
    locality = db.Column(db.String(255), nullable=True)                # Locality
    town = db.Column(db.String(100), nullable=False)                   # Town
    postcode = db.Column(db.String(20), nullable=False)                # Postcode

    # New fields for rates
    flat_rate = db.Column(db.Float, nullable=True)                    # Flat rate
    promo_rate = db.Column(db.Float, nullable=True)                   # Promotional rate
    promo_rate_date_end = db.Column(db.Date, nullable=True)           # End date for promotional rate

    events = db.relationship('Event', backref='user', lazy=True)



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
    event_image = db.Column(db.String(300), nullable=True)  # Image URL

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)



# Function to generate a random unique ID with 15 characters
def generate_unique_id():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(15))

@app.route('/register', methods=['GET', 'POST'])
def register():
    try:
        if request.method == 'POST':
            print(request.form)  # Log the form data received

            # Extracting form data
            email = request.form['email']
            password = request.form['password']
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            phone_number = request.form['phone_number']
            business_name = request.form['business_name']
            website_url = request.form.get('website_url', '')  # Optional
            vat_number = request.form.get('vat_number', '')      # Optional
            country = request.form.get('country', '')             # Optional
            house_name_or_number = request.form['house_name_or_number']
            street = request.form['street']
            locality = request.form.get('locality', '')          # Optional
            town = request.form['town']
            postcode = request.form['postcode']

            # New fields for rates (if you still need them)
            flat_rate = request.form.get('flat_rate', type=float)  # Optional
            promo_rate = request.form.get('promo_rate', type=float)  # Optional
            promo_rate_date_end = request.form.get('promo_rate_date_end')  # Optional

            # Debug: Log the incoming data
            print(f"Registering user: {email}, {first_name} {last_name}, Phone: {phone_number}")
            print(f"Address: {house_name_or_number}, {street}, {locality}, {town}, {postcode}")

            # Check if the email already exists
            user = User.query.filter_by(email=email).first()
            if user:
                return render_template('register.html', error="Email already in use, please contact us on 0330 043 6608")

            # Generate a unique ID for the user
            unique_id = generate_unique_id()

            # Hash the password for security
            hashed_password = generate_password_hash(password)

            # Create the new user
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
                stripe_connect_id="",  # Initialize with empty string
                house_name_or_number=house_name_or_number,
                street=street,
                locality=locality,
                town=town,
                postcode=postcode,
                flat_rate=flat_rate,
                promo_rate=promo_rate,
                promo_rate_date_end=promo_rate_date_end,
            )

            # Add the new user to the database
            db.session.add(new_user)
            db.session.commit()

            flash('Account created successfully! Please log in.')
            return redirect(url_for('login'))

    except Exception as e:
        print(f"Error during registration: {str(e)}")
        return render_template('register.html', error="An error occurred during registration.")

    return render_template('register.html')


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
        event_image = request.form['event_image']

        # Create a new event, linked to the current logged-in user
        new_event = Event(
            name=name,
            date=date,
            location=location,
            description=description,
            start_time=start_time,
            end_time=end_time,
            ticket_quantity=ticket_quantity,
            ticket_price=ticket_price,
            event_image=event_image,
            user_id=current_user.id
        )

        # Add the new event to the database
        db.session.add(new_event)
        db.session.commit()

        flash('Event created successfully!')
        return redirect(url_for('dashboard'))

    return render_template('create_event.html')


if __name__ == "__main__":
    app.run(debug=True)


@app.route('/reset_db')
def reset_db():
    try:
        # Drop all tables and recreate them
        db.drop_all()  # This deletes all the tables
        db.create_all()  # This recreates the tables based on the models
        return "Database reset and tables recreated!"
    except Exception as e:
        return f"An error occurred during reset: {str(e)}"

@app.route('/embed/<unique_id>')
def embed_events(unique_id):
    # Find the user by their unique ID
    user = User.query.filter_by(unique_id=unique_id).first()

    if not user:
        return "User not found", 404

    # Get all events for that user
    user_events = Event.query.filter_by(user_id=user.id).all()

    # Generate the HTML for the events including the "Buy Ticket" button
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
            <button onclick="window.location.href='/buy_ticket/{event.id}'">Buy Ticket</button>
        </li><br>
        '''
    events_html += '</ul>'

    # Return the HTML content as a script that writes to the document
    response = f"document.write(`{events_html}`);"
    return response, 200, {'Content-Type': 'application/javascript'}


@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        data = request.get_json()
        event_id = data['event_id']
        user_stripe_connect_id = data['stripe_connect_id']
        ticket_price = data['ticket_price']

        # Create a Stripe Checkout Session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'gbp',
                    'product_data': {
                        'name': f"Ticket for Event {event_id}",
                    },
                    'unit_amount': int(ticket_price * 100),  # Convert to pence
                },
                'quantity': 1,
            }],
            payment_intent_data={
                'application_fee_amount': int(ticket_price * 100 * 0.1),  # 10% platform fee
                'transfer_data': {
                    'destination': user_stripe_connect_id,
                },
            },
            mode='payment',
            success_url='https://your-site.com/success',
            cancel_url='https://your-site.com/cancel',
        )

        return jsonify({'id': session.id})
    
    except Exception as e:
        return jsonify(error=str(e)), 403


@app.route('/buy_ticket/<int:event_id>', methods=['POST'])
@login_required
def buy_ticket(event_id):
    try:
        # Fetch the event from the database
        event = Event.query.get(event_id)
        if not event:
            return "Event not found", 404

        # Fetch the user's Stripe Connect account ID from the database
        user = User.query.get(event.user_id)
        if not user or not user.stripe_connect_id:
            return "Seller not registered with Stripe", 400

        # Create a Stripe Checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'gbp',
                    'product_data': {
                        'name': event.name,
                    },
                    'unit_amount': int(event.ticket_price * 100),  # Convert to pence
                },
                'quantity': 1,
            }],
            payment_intent_data={
                'application_fee_amount': int(event.ticket_price * 100 * 0.1),  # 10% platform fee
                'transfer_data': {
                    'destination': user.stripe_connect_id,  # Client's Stripe Connect ID
                },
            },
            mode='payment',
            success_url=url_for('success', _external=True),
            cancel_url=url_for('cancel', _external=True),
        )

        # Redirect the user to the Stripe Checkout page
        return redirect(checkout_session.url, code=303)

    except Exception as e:
        print(f"Error during checkout: {str(e)}")
        return str(e), 500


@app.route('/success')
def success():
    return "Payment was successful!"

@app.route('/cancel')
def cancel():
    return "Payment was cancelled."
