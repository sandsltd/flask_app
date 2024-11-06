from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
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
import pandas as pd
from io import BytesIO
from flask import make_response
import re
from uuid import uuid4
from apscheduler.schedulers.background import BackgroundScheduler
import math
from flask_mail import Mail, Message
import urllib.parse
from flask import Response
from markupsafe import escape
from markupsafe import Markup
from itsdangerous import URLSafeTimedSerializer
from flask import current_app




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
# Configuration for Flask-Mail
app.config['MAIL_SERVER'] = 'mail.ticketrush.io'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')  # Your email here (from Render)
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')  # Your password here (from Render)
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')  # Default sender email
# Configure upload limits and paths
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 5 MB limit
app.config['UPLOAD_FOLDER'] = '/path/to/uploads'  # Temporary storage for file uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


mail = Mail(app)

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
    stripe_connect_id = db.Column(db.String(120), nullable=True)
    onboarding_status = db.Column(db.String(20), default="pending")  # Onboarding status
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # Add created_at timestamp
    first_login = db.Column(db.String(1), nullable=True)

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

    # Token generation for password reset
    def get_reset_token(self, expires_sec=3600):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps(self.id, salt='password-reset-salt')

    # Token verification for password reset
    @staticmethod
    def verify_reset_token(token, expires_sec=3600):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token, salt='password-reset-salt', max_age=expires_sec)
        except:
            return None
        return User.query.get(user_id)





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
    session_id = db.Column(db.String(255), nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)
    ticket_answers = db.Column(db.Text, nullable=False)
    billing_details = db.Column(db.Text, nullable=True)
    stripe_charge_id = db.Column(db.String(255), nullable=True)
    payment_status = db.Column(db.String(50), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    full_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(50), nullable=False)
    tickets_purchased = db.Column(db.Integer, nullable=False)
    ticket_price_at_purchase = db.Column(db.Float, nullable=False)

    # Relationship to the Event model
    event = db.relationship('Event', backref=db.backref('attendees', passive_deletes=True))



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

@app.route('/')
def home():
    return redirect(url_for('login'))

from datetime import datetime, timedelta

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Find the user by email
        user = User.query.filter_by(email=email).first()

        if user:
            # Check if the provided password is correct
            if check_password_hash(user.password, password):
                # Check if the user has completed Stripe onboarding
                if user.onboarding_status == "complete":
                    # Check if this is the user's first login
                    if user.first_login == "N":
                        user.first_login = "Y"  # Update to indicate first login completed
                        db.session.commit()
                        # Flash the welcome message with links, using Markup to render HTML
                        flash(
                            Markup(
                                "Welcome to TicketRush! 🎉 <br> "
                                "We’re excited to have you here! It looks like it’s your first time logging in, so we recommend starting with our "
                                "<a href='https://ticketrush.io/tutorials' target='_blank'>First-Time User Guide</a> "
                                "to get the most out of TicketRush. <br><br>"
                                "Before creating your first event, take a moment to personalise your "
                                "<a href='https://bookings.ticketrush.io/manage-default-questions'>Account Settings</a> so your events are customised just the way you like. <br><br>"
                            ),
                            "success"
                        )

                    # Log the user in
                    login_user(user)
                    flash('Logged in successfully!', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    # Show message if onboarding is incomplete
                    flash('It looks like you have recently attempted to register but not completed the Stripe setup. Please complete the process before logging in.', 'warning')
                    return render_template('login.html')  # Stay on the login page
            else:
                flash('Invalid email or password', 'danger')
        else:
            flash('Email not found. Please register first.', 'warning')

    return render_template('login.html')




@app.route('/dashboard')
@login_required
def dashboard():
    filter_value = request.args.get('filter', 'upcoming')  # Set 'upcoming' as the default filter
    user_events = Event.query.filter_by(user_id=current_user.id).all()

    # Helper function to convert string dates to datetime for comparison
    def str_to_date(date_str):
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')  # Adjust the format if your date strings differ
        except ValueError:
            return None

    # Filter and sort events based on the filter value
    if filter_value == 'upcoming':
        user_events = [event for event in user_events if str_to_date(event.date) and str_to_date(event.date) >= datetime.now()]
    elif filter_value == 'past':
        user_events = [event for event in user_events if str_to_date(event.date) and str_to_date(event.date) < datetime.now()]
    
    # Sort events by date
    user_events.sort(key=lambda event: str_to_date(event.date) or datetime.max)

    total_tickets_sold = 0
    total_revenue = 0

    event_data = []
    for event in user_events:
        succeeded_attendees = Attendee.query.filter_by(event_id=event.id, payment_status='succeeded').all()
        tickets_sold = sum([attendee.tickets_purchased for attendee in succeeded_attendees])
        tickets_remaining = event.ticket_quantity - tickets_sold
        event_revenue = sum([attendee.tickets_purchased * attendee.ticket_price_at_purchase for attendee in succeeded_attendees])

        total_tickets_sold += tickets_sold
        total_revenue += event_revenue

        event_date = str_to_date(event.date) if event.date else None
        event_status = "Upcoming" if event_date and event_date >= datetime.now() else "Past"

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
            # Collect user data from the form
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

            # Check if user already exists with the same email
            existing_user = User.query.filter_by(email=email).first()

            if existing_user:
                if existing_user.onboarding_status == "pending":
                    # If a pending user is found, delete their old entry
                    db.session.delete(existing_user)
                    db.session.commit()
                    flash('Previous registration found with incomplete onboarding. Re-registering...', 'info')
                else:
                    # If the user exists and completed onboarding, don't allow re-registration
                    return render_template('register.html', error="Email already in use and completed onboarding.")
            
            # If no user or the old pending user has been deleted, proceed with creating a new one
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
                house_name_or_number=house_name_or_number,
                street=street,
                locality=locality,
                town=town,
                postcode=postcode,
                stripe_connect_id=None,
                onboarding_status="pending",
                created_at=datetime.utcnow(),
                first_login="N"  # Set first_login to "N" upon registration
            )

            db.session.add(new_user)
            db.session.commit()

            # Create the user's Stripe Connect account
            stripe_account = stripe.Account.create(
                type="standard",
                country="GB",
                email=email,
            )

            # Create the Account Link for onboarding
            account_link = stripe.AccountLink.create(
                account=stripe_account.id,
                refresh_url=url_for('stripe_onboarding_refresh', _external=True),
                return_url=url_for('stripe_onboarding_complete', account=stripe_account.id, user_id=new_user.id, _external=True),
                type='account_onboarding',
            )

            # Redirect the user to complete Stripe onboarding
            return redirect(account_link.url)

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



"""
@app.route('/reset_db')
def reset_db():
    try:
        db.drop_all()
        db.create_all()
        return "Database reset and tables recreated!"
    except Exception as e:
        return f"An error occurred during reset: {str(e)}"

"""

from markupsafe import escape

from datetime import datetime

@app.route('/embed/<unique_id>')
def embed_events(unique_id):
    user = User.query.filter_by(unique_id=unique_id).first()

    if not user:
        return "User not found", 404

    user_events = Event.query.filter_by(user_id=user.id).all()

    # Filter out past events based on the current date
    current_date = datetime.now().date()
    future_events = [event for event in user_events if datetime.strptime(event.date, '%Y-%m-%d').date() >= current_date]

    # Sort events by date, with the next upcoming event first
    future_events = sorted(future_events, key=lambda event: datetime.strptime(event.date, '%Y-%m-%d'))

    # Begin constructing the HTML
    events_html = '''
    <style>
    /* Embedded Events Styles */
    #ticketrush-embed * {
        box-sizing: border-box;
        font-family: Arial, sans-serif;
    }

    #ticketrush-embed {
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
    }

    #ticketrush-embed .section-title {
        font-size: 28px;
        color: #333333;
        text-align: center;
        margin-bottom: 40px;
        font-weight: bold;
    }

    #ticketrush-embed .event-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        background-color: #ffffff;
        margin-bottom: 30px;
        transition: box-shadow 0.2s ease;
    }

    #ticketrush-embed .event-card:hover {
        box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.1);
    }

    #ticketrush-embed .event-content {
        padding: 20px;
    }

    #ticketrush-embed .event-title {
        font-size: 22px;
        color: #333333;
        margin-bottom: 15px;
        font-weight: bold;
    }

    #ticketrush-embed .event-details {
        font-size: 16px;
        color: #555555;
        margin-bottom: 15px;
    }

    #ticketrush-embed .event-description {
        font-size: 14px;
        color: #666666;
        margin-bottom: 20px;
    }

    #ticketrush-embed .event-button {
        display: inline-block;
        padding: 12px 24px;
        background-color: #808080;
        color: #ffffff;
        text-decoration: none;
        border-radius: 5px;
        transition: background-color 0.3s ease;
        font-size: 16px;
    }

    #ticketrush-embed .event-button:hover {
        background-color: #0056b3;
    }

    #ticketrush-embed .sold-out {
        color: #FF0000;
        font-weight: bold;
        font-size: 16px;
    }

    #ticketrush-embed .ticket-status {
        margin-bottom: 20px;
    }

    #ticketrush-embed .powered-by {
        text-align: center;
        margin-top: 50px;
        font-size: 14px;
        color: #888888;
    }

    #ticketrush-embed .powered-by a {
        color: #888888;
        text-decoration: none;
        font-weight: bold;
    }

    .more-info-btn {
        color: #0056b3;
        cursor: pointer;
        text-decoration: underline;
        font-size: 14px;
    }

    .more-info-btn:hover {
        color: #003366;
    }

    .share-buttons {
        display: flex;
        align-items: center;
        margin: 10px 0;
    }

    .share-buttons img {
        width: 24px;
        height: 24px;
        margin-right: 8px;
        cursor: pointer;
    }

    @media (min-width: 768px) {
        #ticketrush-embed .event-list {
            display: flex;
            flex-wrap: wrap;
            gap: 30px;
        }

        #ticketrush-embed .event-card {
            width: calc(50% - 15px);
        }
    }
    </style>

    <script>
    function toggleDescription(id) {
        var shortDesc = document.getElementById("short-desc-" + id);
        var fullDesc = document.getElementById("full-desc-" + id);
        var btnText = document.getElementById("more-info-btn-" + id);

        if (shortDesc.style.display === "none") {
            shortDesc.style.display = "inline";
            fullDesc.style.display = "none";
            btnText.innerHTML = "View More Information";
        } else {
            shortDesc.style.display = "none";
            fullDesc.style.display = "inline";
            btnText.innerHTML = "Show Less";
        }
    }
    </script>

    <div id="ticketrush-embed">
    '''

    if not future_events:
        events_html += '<p style="text-align: center; font-size: 18px; color: #555555;">No upcoming events available.</p>'
    else:
        events_html += '<h2 class="section-title">Upcoming Events</h2>'
        events_html += '<div class="event-list">'
        for event in future_events:
            # Calculate tickets sold
            succeeded_attendees = Attendee.query.filter_by(event_id=event.id, payment_status='succeeded').all()
            tickets_sold = sum([attendee.tickets_purchased for attendee in succeeded_attendees])

            # Calculate tickets available
            tickets_available = event.ticket_quantity - tickets_sold

            # Format the event date to 'Monday 12th October 2024'
            event_date = datetime.strptime(event.date, '%Y-%m-%d')
            formatted_date = event_date.strftime('%A %d %B %Y')

            # Format the ticket price
            ticket_price = "Free" if event.ticket_price == 0 else f"£{event.ticket_price:.2f}"

            # Escape special characters and prepare descriptions
            event_name = escape(event.name)
            event_location = escape(event.location)
            short_description = escape(event.description[:150] + '...') if len(event.description) > 150 else escape(event.description)
            full_description = escape(event.description)

            # Build the event card HTML
            events_html += f'''
            <div class="event-card">
                <div class="event-content">
                    <h3 class="event-title">{event_name}</h3>
                    <p class="event-details">
                        <strong>Date:</strong> {formatted_date}<br>
                        <strong>Time:</strong> {event.start_time} - {event.end_time}<br>
                        <strong>Location:</strong> {event_location}<br>
                        <strong>Price:</strong> {ticket_price}
                    </p>
                    <p class="event-description">
                        <span id="short-desc-{event.id}">{short_description}</span>
                        <span id="full-desc-{event.id}" style="display: none;">{full_description}</span>
                        <span class="more-info-btn" id="more-info-btn-{event.id}" onclick="toggleDescription('{event.id}')">View More Information</span>
                    </p>
                    
                    <!-- Share Buttons -->
                    <div class="share-buttons">
                        <a href="https://www.facebook.com/sharer/sharer.php?u=https://bookings.ticketrush.io/purchase/{event.id}" target="_blank">
                            <img src="https://ticketrush.io/wp-content/uploads/2024/11/facebook-129.png" alt="Share on Facebook">
                        </a>
                        <a href="https://www.instagram.com/?url=https://bookings.ticketrush.io/purchase/{event.id}" target="_blank">
                            <img src="https://ticketrush.io/wp-content/uploads/2024/11/transparent-social-media-instagram-icon-with-centered-image-symbol65ff3fa8a91258.78351108.webp" alt="Share on Instagram">
                        </a>
                        <a href="https://twitter.com/intent/tweet?url=https://bookings.ticketrush.io/purchase/{event.id}" target="_blank">
                            <img src="https://ticketrush.io/wp-content/uploads/2024/11/transparent-x-icon-black-and-white-x-in-the-1710888893456.webp" alt="Share on Twitter">
                        </a>
                        <a href="mailto:?subject=Check out this event!&body=https://bookings.ticketrush.io/purchase/{event.id}" target="_blank">
                            <img src="https://ticketrush.io/wp-content/uploads/2024/11/pngtree-email-vector-icon-png-image_3876244.jpg" alt="Share via Email">
                        </a>
                    </div>
            '''

            # Show ticket status
            if tickets_available > 0:
                events_html += f'''
                    <p class="ticket-status">
                        <span style="color: #28a745; font-weight: bold;">Tickets Available: {tickets_available}</span>
                    </p>
                    <a href="https://bookings.ticketrush.io/purchase/{event.id}" target="_blank" class="event-button">Book Tickets</a>
                '''
            else:
                events_html += '''
                    <p class="ticket-status sold-out">Sold Out</p>
                '''

            events_html += '''
                </div>
            </div>
            '''

        events_html += '</div>'

    # Add the "Powered by TicketRush" footer with link
    events_html += '''
    <div class="powered-by">
        Powered by <a href="https://www.ticketrush.io" target="_blank">TicketRush</a>
    </div>
    </div>
    '''

    response = f"document.write(`{events_html}`);"
    return response, 200, {'Content-Type': 'application/javascript'}

@app.route('/cancel')
def cancel():
    return "Payment canceled. You can try again."

if __name__ == "__main__":
    app.run(debug=True)

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
import re

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
import re

@app.route('/manage-default-questions', methods=['GET', 'POST'])
@login_required
def manage_default_questions():
    user = User.query.get(current_user.id)

    if request.method == 'POST':
        # Collect form data
        first_name = request.form.get('first_name').strip()
        last_name = request.form.get('last_name').strip()
        phone_number = request.form.get('phone_number').strip()
        business_name = request.form.get('business_name').strip()
        website_url = request.form.get('website_url', '').strip()
        vat_number = request.form.get('vat_number', '').strip()
        house_name_or_number = request.form.get('house_name_or_number').strip()
        street = request.form.get('street').strip()
        locality = request.form.get('locality', '').strip()
        town = request.form.get('town').strip()
        postcode = request.form.get('postcode').strip()
        terms_link = request.form.get('terms_link', '').strip()

        # Update user information
        user.first_name = first_name
        user.last_name = last_name
        user.phone_number = phone_number
        user.business_name = business_name
        user.vat_number = vat_number
        user.house_name_or_number = house_name_or_number
        user.street = street
        user.locality = locality
        user.town = town
        user.postcode = postcode

        # Process website URL
        if website_url:
            if not re.match(r'^https?://', website_url):
                website_url = 'https://' + website_url
            user.website_url = website_url
        else:
            user.website_url = None

        # Process terms link
        if terms_link.lower() == 'none' or not terms_link:
            user.terms = 'none'
        else:
            # Add https:// if missing
            if not re.match(r'^https?://', terms_link):
                terms_link = 'https://' + terms_link
            user.terms = terms_link

        # Process default questions
        questions = request.form.getlist('questions[]')
        existing_questions = DefaultQuestion.query.filter_by(user_id=user.id).all()

        # Update existing questions
        for i, question_text in enumerate(questions):
            question_text = question_text.strip()
            if i < len(existing_questions):
                existing_questions[i].question = question_text
            else:
                # Add new questions if any
                if question_text:
                    new_question = DefaultQuestion(user_id=user.id, question=question_text)
                    db.session.add(new_question)

        # Remove extra questions if fewer are submitted
        if len(questions) < len(existing_questions):
            for q in existing_questions[len(questions):]:
                db.session.delete(q)

        # Commit changes to the database
        db.session.commit()

        # Flash success message and redirect to dashboard
        flash('Account settings successfully updated.')
        return redirect(url_for('dashboard'))

    # GET request
    # Render the settings page
    questions = DefaultQuestion.query.filter_by(user_id=user.id).all()
    return render_template('manage_default_questions.html', user=user, questions=questions)




def calculate_total_charge_and_booking_fee(n_tickets, ticket_price_gbp):
    # Constants
    platform_fee_per_ticket_pence = 30  # Platform fee: 30p per ticket
    stripe_percent_fee = 0.014          # Stripe percentage fee (1.4%)
    stripe_fixed_fee_pence = 20         # Fixed Stripe fee per transaction (20p)

    # Calculate the ticket price in pence
    total_ticket_price_pence = int(n_tickets * ticket_price_gbp * 100)

    # Calculate the platform fee (30p per ticket)
    total_platform_fee_pence = platform_fee_per_ticket_pence * n_tickets

    # Calculate the subtotal (ticket price + platform fee)
    subtotal_before_stripe = total_ticket_price_pence + total_platform_fee_pence

    # Calculate the Stripe fee (1.4% of subtotal + 20p)
    stripe_fee_pence = int(subtotal_before_stripe * stripe_percent_fee) + stripe_fixed_fee_pence

    # Calculate total charge to the buyer, including Stripe fee
    total_charge_pence = subtotal_before_stripe + stripe_fee_pence

    # Round up and return the total charge to the buyer and platform fee
    return int(math.ceil(total_charge_pence)), int(math.ceil(total_platform_fee_pence))


@app.route('/purchase/<int:event_id>', methods=['GET', 'POST'])
def purchase(event_id):
    # Fetch the event and organizer
    event = Event.query.get(event_id)
    if not event:
        return "Event not found", 404
    organizer = User.query.get(event.user_id)
    if not organizer:
        return "Event organizer not found", 404

    # Collect questions
    default_questions = DefaultQuestion.query.filter_by(user_id=organizer.id).order_by(DefaultQuestion.id).all()
    default_question_texts = [dq.question for dq in default_questions]
    custom_questions = [getattr(event, f'custom_question_{i}') for i in range(1, 11) if getattr(event, f'custom_question_{i}', None)]
    all_questions = default_question_texts + [q for q in custom_questions if q not in default_question_texts]

    if request.method == 'POST':
        session_id = str(uuid4())
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        number_of_tickets = int(request.form.get('number_of_tickets', 1))

        if not all([full_name, email, phone_number]):
            flash('Please fill in all required fields.')
            return redirect(url_for('purchase', event_id=event_id))

        if number_of_tickets > event.ticket_quantity:
            flash('Requested number of tickets exceeds available tickets.')
            return redirect(url_for('purchase', event_id=event_id))

        if organizer.terms and organizer.terms.lower() != 'none':
            if not request.form.get('accept_organizer_terms'):
                flash('You must accept the event organizer\'s Terms and Conditions.')
                return redirect(url_for('purchase', event_id=event_id))

        if not request.form.get('accept_platform_terms'):
            flash('You must accept the platform\'s Terms and Conditions.')
            return redirect(url_for('purchase', event_id=event_id))

        # Loop to create an `Attendee` entry for each ticket
        attendees = []
        for i in range(number_of_tickets):
            ticket_answers = {}
            for q_index, question in enumerate(all_questions):
                answer_key = f'ticket_{i}_question_{q_index}'
                answer = request.form.get(answer_key)
                if not answer:
                    flash(f'Please answer all questions for Ticket {i + 1}.')
                    return redirect(url_for('purchase', event_id=event_id))
                ticket_answers[question] = answer

            attendee = Attendee(
                event_id=event_id,
                ticket_answers=json.dumps(ticket_answers),
                payment_status='pending',
                full_name=full_name,
                email=email,
                phone_number=phone_number,
                tickets_purchased=1,
                ticket_price_at_purchase=event.ticket_price,
                session_id=session_id,
                created_at=datetime.utcnow()
            )
            db.session.add(attendee)
            attendees.append(attendee)

        db.session.commit()

        if event.ticket_price == 0:
            for attendee in attendees:
                attendee.payment_status = 'succeeded'
            db.session.commit()
            billing_details = {'name': full_name, 'email': email, 'phone': phone_number, 'address': {}}
            send_confirmation_email_to_attendee(attendees[0], billing_details)
            send_confirmation_email_to_organizer(organizer, attendees, billing_details, event)
            flash('Your free ticket(s) have been booked successfully!')
            return redirect(url_for('success', session_id=session_id))

        else:
            # Calculate fees and total amount in pence
            ticket_total = number_of_tickets * event.ticket_price * 100  # Ticket price in pence
            platform_fee_pence = 30 * number_of_tickets  # Platform fee (30p per ticket)
            transaction_fee_pence = 20  # Flat 20p transaction fee
            stripe_fee_pence = int((ticket_total + platform_fee_pence) * 0.029) + transaction_fee_pence
            booking_fee_pence = platform_fee_pence + stripe_fee_pence
            total_charge_pence = ticket_total + booking_fee_pence

            # Adjust platform fee to cover Stripe’s processing cut
            adjusted_platform_fee = int(platform_fee_pence / 0.971)  # Adjusted to counter 2.9% Stripe fee

            # Stripe checkout session
            try:
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[
                        {
                            'price_data': {
                                'currency': 'gbp',
                                'product_data': {'name': event.name},
                                'unit_amount': int(event.ticket_price * 100),
                            },
                            'quantity': number_of_tickets,
                        },
                        {
                            'price_data': {
                                'currency': 'gbp',
                                'product_data': {
                                    'name': 'Booking Fee',
                                    'description': ' ',
                                },
                                'unit_amount': booking_fee_pence,
                            },
                            'quantity': 1,
                        }
                    ],
                    mode='payment',
                    success_url=url_for('success', session_id=session_id, _external=True),
                    cancel_url=url_for('cancel', _external=True),
                    metadata={'session_id': session_id},
                    payment_intent_data={
                        'application_fee_amount': adjusted_platform_fee,  # Adjusted platform fee to cover Stripe’s cut
                        'on_behalf_of': organizer.stripe_connect_id,  # Display organizer's branding
                        'transfer_data': {
                            'destination': organizer.stripe_connect_id,
                        },
                    },
                    billing_address_collection='required',
                    customer_email=email
                )

                return redirect(checkout_session.url)

            except Exception as e:
                app.logger.error(f"Error creating checkout session: {str(e)}")
                flash('An error occurred while processing your payment.')
                return redirect(url_for('purchase', event_id=event_id))

    else:
        platform_terms_link = 'https://your-platform-domain.com/terms-and-conditions'
        organizer_terms_link = organizer.terms if organizer.terms and organizer.terms.lower() != 'none' else None

        return render_template(
            'purchase.html',
            event=event,
            organizer=organizer,
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




# Route to generate ICS file
@app.route('/download_ics/<int:event_id>')
def download_ics(event_id):
    event = Event.query.get_or_404(event_id)
    organizer = User.query.get(event.user_id)

    # Prepare ICS file content
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Your Company//NONSGML Event//EN
BEGIN:VEVENT
UID:{event.id}@your-platform.com
DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}
DTSTART:{event.date.replace('-', '')}T{event.start_time.replace(':', '')}00Z
DTEND:{event.date.replace('-', '')}T{event.end_time.replace(':', '')}00Z
SUMMARY:{event.name}
DESCRIPTION:{event.description}
LOCATION:{event.location}
END:VEVENT
END:VCALENDAR
"""

    # Return the ICS file as a download
    return Response(ics_content, mimetype='text/calendar', headers={
        'Content-Disposition': f'attachment; filename={event.name}.ics'
    })


def send_confirmation_email_to_attendee(attendees, billing_details):
    try:
        # Ensure attendees list is not empty
        if not attendees:
            print("No attendees provided to send confirmation email.")
            return

        # Use the first attendee to gather common details
        first_attendee = attendees[0]

        # Fetch event and organizer (user) details
        event = Event.query.get(first_attendee.event_id)
        organizer = User.query.get(event.user_id)

        # Calculate the total tickets and total price
        total_tickets = sum(attendee.tickets_purchased for attendee in attendees)
        total_price = sum(attendee.ticket_price_at_purchase * attendee.tickets_purchased for attendee in attendees)

        # Generate "Add to Calendar" links (Google Calendar and iOS .ics file)
        start_time = event.start_time.replace(':', '')  # Assuming time is 'HH:MM'
        end_time = event.end_time.replace(':', '')  # End time in the same format
        event_date = event.date.replace('-', '')  # Assuming date is 'YYYY-MM-DD'

        # Google Calendar link
        google_calendar_url = (
            f"https://www.google.com/calendar/render?"
            f"action=TEMPLATE&text={urllib.parse.quote(event.name)}"
            f"&dates={event_date}T{start_time}Z/{event_date}T{end_time}Z"
            f"&details=Event+at+{urllib.parse.quote(event.location)}"
            f"&location={urllib.parse.quote(event.location)}"
            f"&sf=true&output=xml"
        )

        # iOS/ICS Calendar file link
        ics_file_url = url_for('download_ics', event_id=event.id, _external=True)

        # Prepare the organizer details section
        organizer_details = f"""
        <p>
            <strong>Business:</strong> {organizer.business_name}<br>
            <strong>Website:</strong> <a href="{organizer.website_url or '#'}" style="color: #ff0000;">{organizer.website_url or 'No website provided'}</a><br>
        """

        if organizer.terms and organizer.terms.lower() != 'none':
            organizer_details += f"""
            <strong>Organiser's Terms (Please Read):</strong> <a href="{organizer.terms}" style="color: #ff0000;">{organizer.terms}</a>
            """

        organizer_details += "</p>"

        # Prepare the email body with inline CSS and logo
        body = f"""
        <html>
        <body style="background-color: #ffffff; color: #000000; font-family: Arial, sans-serif; padding: 20px;">
            <!-- Include Logo -->
            <div style="text-align: center; margin-bottom: 20px;">
                <img src="http://ticketrush.io/wp-content/uploads/2024/10/TicketRush-Logo.png" alt="Ticket Rush Logo" style="max-width: 200px;">
            </div>

            <h2 style="color: #ff0000;">Hello {first_attendee.full_name},</h2>

            <p>Thank you for purchasing tickets for the event <strong>'{event.name}'</strong>. Below are your details:</p>

            <hr style="border: 1px solid #ff0000;">
            
            <h3 style="color: #ff0000;">Event Information:</h3>
            <p>
                <strong>Event:</strong> {event.name}<br>
                <strong>Date:</strong> {event.date}<br>
                <strong>Time:</strong> {event.start_time} - {event.end_time}<br>
                <strong>Location:</strong> {event.location}
            </p>
            
            <h3 style="color: #ff0000;">Your Details:</h3>
            <p>
                <strong>Full Name:</strong> {first_attendee.full_name}<br>
                <strong>Email:</strong> {first_attendee.email}<br>
                <strong>Phone Number:</strong> {first_attendee.phone_number}<br>
                <strong>Ticket Quantity:</strong> {total_tickets}<br>
                <strong>Amount Paid:</strong> £{total_price:.2f}<br>
                <strong>Billing Address:</strong> {billing_details.get('address', {}).get('line1')}, {billing_details.get('address', {}).get('city')}
            </p>
            
            <hr style="border: 1px solid #ff0000;">
            
            <h3 style="color: #ff0000;">Add to Calendar:</h3>
            <div style="margin-bottom: 20px;">
                <a href="{ics_file_url}" style="display: inline-block; background-color: #ff0000; color: #ffffff; padding: 10px 15px; text-decoration: none; border-radius: 5px;">Click here to add to Apple/iOS or other Calendar</a>
            </div>
            
            <hr style="border: 1px solid #ff0000;">
            
            <h3 style="color: #ff0000;">Organiser Details:</h3>
            {organizer_details}

            <hr style="border: 1px solid #ff0000;">

            <!-- New Need Help Section -->
            <h3 style="color: #ff0000;">Need Help?</h3>
            <p>
                If you have any issues or questions about the event, please reach out directly to  
                {organizer.business_name}, at <a href="mailto:{organizer.email}" style="color: #ff0000;">{organizer.email}</a>.
            </p>

            <hr style="border: 1px solid #ff0000;">

            <p style="color: #ff0000;"><strong>Powered by TicketRush</strong></p>
        </body>
        </html>
        """

        # Create and send the email using Flask-Mail
        msg = Message(
            subject=f"Your Ticket Confirmation for {event.name}",
            recipients=[first_attendee.email],
            body=body,
            html=body  # Render the email as HTML to support links and styling
        )
        mail.send(msg)
        print(f"Confirmation email sent to attendee {first_attendee.email}.")

    except Exception as e:
        print(f"Failed to send confirmation email to attendee. Error: {str(e)}")







def send_confirmation_email_to_organizer(organizer, attendees, billing_details, event):
    try:
        # Collect attendee details, including custom/default questions and answers
        attendee_info = ""
        for attendee in attendees:
            # Load custom questions and answers
            answers = json.loads(attendee.ticket_answers) if attendee.ticket_answers else {}
            question_answer_pairs = "".join([f"<strong>{question}:</strong> {answer}<br>" for question, answer in answers.items()])

            # Add attendee details to the email
            attendee_info += f"""
            <p>
                <strong>Name:</strong> {attendee.full_name}<br>
                <strong>Email:</strong> {attendee.email}<br>
                <strong>Phone:</strong> {attendee.phone_number}<br>
                <strong>Ticket Quantity:</strong> {attendee.tickets_purchased}<br>
                <strong>Total Amount Paid:</strong> £{attendee.ticket_price_at_purchase * attendee.tickets_purchased:.2f}<br>
                {question_answer_pairs}
            </p>
            <hr style="border: 1px solid #ff0000;">
            """

        # Prepare the subject line
        subject = f"New Ticket Purchase for Your Event '{event.name}'"

        # Placeholder for the dashboard link
        dashboard_link = "https://bookings.ticketrush.io/login"  # Replace with actual dashboard link

        # Prepare the email body with the same inline CSS and logo as the attendee email
        body = f"""
        <html>
        <body style="background-color: #ffffff; color: #000000; font-family: Arial, sans-serif; padding: 20px;">
            <!-- Include Logo -->
            <div style="text-align: center; margin-bottom: 20px;">
                <img src="http://ticketrush.io/wp-content/uploads/2024/10/TicketRush-Logo.png" alt="Ticket Rush Logo" style="max-width: 200px;">
            </div>

            <h2 style="color: #ff0000;">Hello {organizer.first_name},</h2>

            <p>You've received new ticket purchases for your event <strong>'{event.name}'</strong>. Here are the details:</p>

            <hr style="border: 1px solid #ff0000;">
            
            <h3 style="color: #ff0000;">Event Information:</h3>
            <p>
                <strong>Event:</strong> {event.name}<br>
                <strong>Date:</strong> {event.date}<br>
                <strong>Time:</strong> {event.start_time} - {event.end_time}<br>
                <strong>Location:</strong> {event.location}
            </p>

            <h3 style="color: #ff0000;">Attendee Details:</h3>
            {attendee_info}

            <hr style="border: 1px solid #ff0000;">
            
            <h3 style="color: #ff0000;">View This Booking:</h3>
            <div style="margin-bottom: 20px;">
                <a href="{dashboard_link}" style="display: inline-block; background-color: #ff0000; color: #ffffff; padding: 10px 15px; text-decoration: none; border-radius: 5px;">View in Your Dashboard</a>
            </div>
            
            <hr style="border: 1px solid #ff0000;">
            
            <!-- Support Section -->
            <h3 style="color: #ff0000;">Need Help?</h3>
            <p>
                If you have any questions or need assistance, feel free to reach out to TicketRush support at 
                <a href="mailto:support@ticketrush.co.uk" style="color: #ff0000;">support@ticketrush.co.uk</a>.
            </p>

            <hr style="border: 1px solid #ff0000;">
            
            <p style="color: #ff0000;"><strong>Powered by TicketRush</strong></p>
        </body>
        </html>
        """

        # Create and send the email using Flask-Mail
        msg = Message(
            subject=subject,
            recipients=[organizer.email],
            body=body,
            html=body  # Render the email as HTML to support links and styling
        )
        mail.send(msg)
        print(f"Confirmation email sent to organizer {organizer.email}.")

    except Exception as e:
        print(f"Failed to send confirmation email to organizer {organizer.email}. Error: {str(e)}")


        # Create and send the email using Flask-Mail
        msg = Message(
            subject=subject,
            recipients=[organizer.email],
            body=body,
            html=body  # Render the email as HTML to support links and styling
        )
        mail.send(msg)
        print(f"Confirmation email sent to organizer {organizer.email}.")

    except Exception as e:
        print(f"Failed to send confirmation email to organizer {organizer.email}. Error: {str(e)}")


def handle_checkout_session(session):
    session_id = session.get('metadata', {}).get('session_id')
    if not session_id:
        print("No session ID found in metadata.")
        return

    # Retrieve all attendees for this session ID
    attendees = Attendee.query.filter_by(session_id=session_id).all()  # Ensuring we have a list of attendees

    if not attendees:
        print(f"No attendees found for session ID {session_id}.")
        return

    # Retrieve the PaymentIntent and charge details
    payment_intent_id = session.get('payment_intent')
    payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id, expand=['latest_charge'])
    charge = payment_intent.latest_charge

    # Extract billing details
    billing_details = charge.billing_details
    if billing_details is None:
        print("No billing details found for this session.")
        return

    # Update all attendee rows with billing details and payment status
    for attendee in attendees:
        attendee.billing_details = json.dumps(billing_details)
        attendee.stripe_charge_id = charge.id
        attendee.payment_status = 'succeeded'
    
    db.session.commit()  # Commit all updates after the loop

    print(f"Updated {len(attendees)} attendees with payment details.")

    # Send confirmation email to the attendees (pass the list of attendees)
    send_confirmation_email_to_attendee(attendees, billing_details)

    # Retrieve the event organizer (seller) details
    event = Event.query.get(attendees[0].event_id)  # Use the first attendee's event_id to get the event
    organizer = User.query.get(event.user_id)
    
    if organizer:
        # Send email to the event organizer
        send_confirmation_email_to_organizer(organizer, attendees, billing_details, event)




@app.route('/view_attendees/<int:event_id>')
@login_required
def view_attendees(event_id):
    event = Event.query.get_or_404(event_id)

    # Ensure the user has permission to view the attendees
    if event.user_id != current_user.id:
        flash("You don't have permission to view the attendees for this event.")
        return redirect(url_for('dashboard'))

    # Fetch default and custom questions
    user = User.query.get(event.user_id)
    default_questions = DefaultQuestion.query.filter_by(user_id=user.id).all()
    default_question_texts = [dq.question for dq in default_questions]

    custom_questions = []
    for i in range(1, 11):  # Loop through 10 possible custom questions
        question = getattr(event, f'custom_question_{i}')
        if question:
            custom_questions.append(question)

    all_questions = default_question_texts + custom_questions

    # Fetch attendees and parse ticket_answers and billing_details JSON
    attendees = Attendee.query.filter_by(event_id=event_id).all()
    for attendee in attendees:
        if attendee.ticket_answers:
            try:
                attendee.ticket_answers = json.loads(attendee.ticket_answers)
            except json.JSONDecodeError:
                attendee.ticket_answers = {}
        else:
            attendee.ticket_answers = {}

        if attendee.billing_details:
            try:
                attendee.billing_details = json.loads(attendee.billing_details)
            except json.JSONDecodeError:
                attendee.billing_details = {}
        else:
            attendee.billing_details = {}

    # Calculate tickets sold
    tickets_sold = sum([attendee.tickets_purchased for attendee in attendees])

    # Total ticket quantity for the event
    total_quantity = event.ticket_quantity

    # Tickets available
    tickets_available = total_quantity - tickets_sold

    # Format the event date as dd-mm-yyyy
    event_date = datetime.strptime(event.date, '%Y-%m-%d').strftime('%d-%m-%Y')

    return render_template(
        'view_attendees.html',
        event=event,
        attendees=attendees,
        questions=all_questions,
        tickets_sold=tickets_sold,
        tickets_available=tickets_available,
        total_quantity=total_quantity,
        event_date=event_date
    )


@app.route('/delete_event/<int:event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)

    # Check if current user owns the event before deleting (for extra security)
    if event.user_id != current_user.id:
        flash("You do not have permission to delete this event.", "error")
        return redirect(url_for('dashboard'))

    db.session.delete(event)
    db.session.commit()
    flash('Event and all associated attendees deleted successfully!')
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

        # Update custom questions conditionally
        for i in range(1, 11):
            question_key = f'custom_question_{i}'
            question_value = request.form.get(question_key)
            # Only update if there’s content; clear if left blank
            setattr(event, question_key, question_value if question_value else None)

        db.session.commit()
        flash('Event updated successfully!')
        return redirect(url_for('dashboard'))

    # Prepare custom questions with empty strings as default values if None
    custom_questions = {f'custom_question_{i}': getattr(event, f'custom_question_{i}', '') or '' for i in range(1, 11)}

    return render_template('edit_event.html', event=event, custom_questions=custom_questions)






@app.route('/delete_attendee/<int:attendee_id>', methods=['POST'])
@login_required
def delete_attendee(attendee_id):
    attendee = Attendee.query.get_or_404(attendee_id)

    # Ensure the user has permission to delete the attendee
    event = Event.query.get(attendee.event_id)
    if event.user_id != current_user.id:
        flash("You don't have permission to delete this attendee.")
        return redirect(url_for('dashboard'))

    # Delete the attendee
    db.session.delete(attendee)
    db.session.commit()

    flash('Attendee deleted successfully, and ticket availability updated!')
    return redirect(url_for('view_attendees', event_id=event.id))


@app.route('/edit_attendee/<int:attendee_id>', methods=['GET', 'POST'])
@login_required
def edit_attendee(attendee_id):
    attendee = Attendee.query.get_or_404(attendee_id)

    # Ensure the user has permission to edit the attendee
    event = Event.query.get(attendee.event_id)
    if event.user_id != current_user.id:
        flash("You don't have permission to edit this attendee.")
        return redirect(url_for('dashboard'))

    # Load ticket answers
    ticket_answers = json.loads(attendee.ticket_answers) if attendee.ticket_answers else {}

    if request.method == 'POST':
        # Update attendee details
        attendee.full_name = request.form['full_name']
        attendee.email = request.form['email']
        attendee.phone_number = request.form['phone_number']

        # Update ticket answers
        updated_ticket_answers = {}
        for question in ticket_answers:
            answer_key = f'answer_{question}'
            updated_ticket_answers[question] = request.form.get(answer_key, '')

        # Save the updated ticket answers as JSON
        attendee.ticket_answers = json.dumps(updated_ticket_answers)

        # Commit changes
        db.session.commit()
        flash('Attendee details and ticket answers updated successfully!')
        return redirect(url_for('view_attendees', event_id=event.id))

    return render_template('edit_attendee.html', attendee=attendee, ticket_answers=ticket_answers)

@app.route('/add_attendee/<int:event_id>', methods=['GET', 'POST'])
@login_required
def add_attendee(event_id):
    event = Event.query.get_or_404(event_id)

    # Ensure the user has permission to add attendees to the event
    if event.user_id != current_user.id:
        flash("You don't have permission to add attendees to this event.")
        return redirect(url_for('dashboard'))

    # Fetch default and custom questions
    user = User.query.get(event.user_id)
    default_questions = DefaultQuestion.query.filter_by(user_id=user.id).all()
    default_question_texts = [dq.question for dq in default_questions]

    custom_questions = []
    for i in range(1, 11):  # Loop through 10 possible custom questions
        question = getattr(event, f'custom_question_{i}')
        if question:
            custom_questions.append(question)

    all_questions = default_question_texts + custom_questions

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        number_of_tickets = int(request.form.get('number_of_tickets'))

        # Check if the number of tickets requested exceeds tickets available
        attendees = Attendee.query.filter_by(event_id=event_id).all()
        tickets_sold = sum([attendee.tickets_purchased for attendee in attendees])
        tickets_available = event.ticket_quantity - tickets_sold
        if number_of_tickets > tickets_available:
            flash(f"Cannot add {number_of_tickets} tickets. Only {tickets_available} tickets are available.")
            return redirect(url_for('add_attendee', event_id=event_id))

        # Collect answers to ticket questions
        ticket_answers = {}
        for idx, question in enumerate(all_questions, start=1):
            answer = request.form.get(f'answer_{idx}')
            ticket_answers[question] = answer

        # Collect billing details if provided
        billing_details = {
            "name": request.form.get('billing_name'),
            "email": request.form.get('billing_email'),
            "phone": request.form.get('billing_phone'),
            "address": {
                "line1": request.form.get('billing_address_line1'),
                "line2": request.form.get('billing_address_line2'),
                "city": request.form.get('billing_city'),
                "state": request.form.get('billing_state'),
                "postal_code": request.form.get('billing_postal_code'),
                "country": request.form.get('billing_country'),
            }
        }

        # Remove empty fields from billing details
        billing_details = {k: v for k, v in billing_details.items() if v}
        billing_details['address'] = {k: v for k, v in billing_details['address'].items() if v}

        if not billing_details['address']:
            del billing_details['address']

        if not billing_details:
            billing_details = None

        # Create a new Attendee object
        attendee = Attendee(
            event_id=event_id,
            full_name=full_name,
            email=email,
            phone_number=phone_number,
            tickets_purchased=number_of_tickets,
            ticket_price_at_purchase=event.ticket_price,
            payment_status='succeeded',
            session_id='N/A',  # Since there's no payment session
            ticket_answers=json.dumps(ticket_answers),
            billing_details=json.dumps(billing_details) if billing_details else None
        )

        db.session.add(attendee)
        db.session.commit()

        # Flash a success message without sending emails
        flash("Attendee added successfully without sending emails.")

        return redirect(url_for('view_attendees', event_id=event_id))

    return render_template('add_attendee.html', event=event, questions=all_questions)


def send_email_to_organizer(attendee):
    try:
        event = Event.query.get(attendee.event_id)
        organizer = User.query.get(event.user_id)

        # Prepare email content
        subject = f"New Attendee Added to Your Event: {event.name}"
        body = f"""
        Hello {organizer.business_name},

        A new attendee has been added to your event '{event.name}'.

        Attendee Details:
        Full Name: {attendee.full_name}
        Email: {attendee.email}
        Phone Number: {attendee.phone_number}
        Tickets Purchased: {attendee.tickets_purchased}

        You can view all attendees here: {url_for('view_attendees', event_id=event.id, _external=True)}

        Best regards,
        TicketRush Team
        """

        msg = Message(
            subject=subject,
            recipients=[organizer.email],
            body=body
        )
        mail.send(msg)
        print(f"Notification email sent to organizer {organizer.email}.")
    except Exception as e:
        print(f"Failed to send email to organizer {organizer.email}. Error: {str(e)}")



@app.route('/export_attendees/<int:event_id>')
@login_required
def export_attendees(event_id):
    event = Event.query.get_or_404(event_id)

    # Ensure the user has permission to export the attendees
    if event.user_id != current_user.id:
        flash("You don't have permission to export the attendees for this event.")
        return redirect(url_for('dashboard'))

    # Fetch attendees
    attendees = Attendee.query.filter_by(event_id=event_id).all()

    # Prepare data for export
    data = []
    for attendee in attendees:
        attendee_data = {
            'Full Name': attendee.full_name,
            'Email': attendee.email,
            'Phone Number': attendee.phone_number,
            'Tickets Purchased': attendee.tickets_purchased,
            'Ticket Price': attendee.ticket_price_at_purchase,
            'Billing Details': attendee.billing_details,
            'Ticket Answers': json.loads(attendee.ticket_answers) if attendee.ticket_answers else {},
            'Payment Status': attendee.payment_status,
        }
        data.append(attendee_data)

    # Create a DataFrame using pandas
    df = pd.DataFrame(data)

    # Convert the 'Ticket Answers' dictionary into separate columns
    ticket_answers_df = pd.json_normalize(df['Ticket Answers'])
    df = pd.concat([df.drop(columns='Ticket Answers'), ticket_answers_df], axis=1)

    # Generate the file name using the event name and date
    event_name_clean = re.sub(r'\W+', '_', event.name)  # Replace spaces and special characters with underscores
    event_date = event.date.replace('-', '_')  # Replace dashes with underscores in the date
    file_name = f"attendees_{event_name_clean}_{event_date}.xlsx"

    # Generate the Excel file in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Attendees')

    output.seek(0)

    # Return the Excel file as a response
    response = make_response(output.read())
    response.headers['Content-Disposition'] = f'attachment; filename={file_name}'
    response.headers['Content-type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response

@app.route('/stripe_onboarding_complete')
def stripe_onboarding_complete():
    # Get the account ID and user ID from the query parameters
    account_id = request.args.get('account')
    user_id = request.args.get('user_id')

    # Debug logs to track what's being received
    print(f"Received user_id: {user_id}")
    print(f"Received account_id: {account_id}")

    # Check if both account_id and user_id are present
    if account_id and user_id:
        # Fetch the user from the database by user_id
        user = User.query.get(user_id)
        if user:
            print(f"User found: {user.email}")

            # Save the Stripe account ID to the user's row
            user.stripe_connect_id = account_id
            db.session.commit()  # Commit changes to the database
            print(f"Stripe Connect ID {account_id} saved for user {user.email}")

            # Fetch the account details from Stripe to check onboarding status
            try:
                stripe_account = stripe.Account.retrieve(account_id)
                # Update the onboarding status based on the Stripe account details
                onboarding_status = "complete" if stripe_account.details_submitted else "pending"
                user.onboarding_status = onboarding_status
                db.session.commit()  # Commit the updated onboarding status to the database
                print(f"Onboarding status updated to {onboarding_status} for user {user.email}")

                # Send welcome email if onboarding is complete
                if onboarding_status == "complete":
                    send_welcome_email(user)
                    flash("Stripe onboarding complete! A welcome email has been sent.", "success")

            except Exception as e:
                print(f"Error fetching account details from Stripe: {str(e)}")
                flash('Error verifying Stripe onboarding status. Please try again later.')

            # Redirect to login page after onboarding
            return redirect(url_for('login'))
        else:
            print("User not found.")
            flash('User not found.')
            return redirect(url_for('register'))
    else:
        print("Stripe onboarding failed: Missing account_id or user_id.")
        flash('Stripe onboarding failed. Please try again.')
        return redirect(url_for('register'))








@app.route('/stripe_onboarding_refresh')
def stripe_onboarding_refresh():
    # Optionally, provide logic here to regenerate the onboarding link
    flash('Please complete the onboarding process.')
    return redirect(url_for('register'))

##

@app.template_filter('datetimeformat')
def datetimeformat(value):
    if value:
        return datetime.strptime(value, '%Y-%m-%d').strftime('%d-%m-%Y')
    return ""

@app.route('/success')
def success():
    # Retrieve the attendee based on session or other identifier
    # Since we don't have a user session, we'll need to find a way to identify the attendee
    # One common method is to pass the session_id as a query parameter during the redirect
    
    session_id = request.args.get('session_id')
    if not session_id:
        return "Invalid session. Unable to retrieve booking details.", 400

    # Fetch the attendee(s) associated with this session_id
    attendees = Attendee.query.filter_by(session_id=session_id, payment_status='succeeded').all()
    if not attendees:
        return "No booking found for this session.", 404

    # Assuming all attendees are for the same event
    event = Event.query.get(attendees[0].event_id)
    organizer = User.query.get(event.user_id)

    # Calculate total tickets purchased
    total_tickets = len(attendees)

    # Prepare data to pass to the template
    context = {
        'event': event,
        'organizer': organizer,
        'attendee': attendees[0],  # Assuming the buyer's details are the same
        'total_tickets': total_tickets
    }

    return render_template('success.html', **context)


def send_welcome_email(user):
    try:
        msg = Message(
            subject="Welcome to TicketRush!",
            sender="no-reply@ticketrush.io",
            recipients=[user.email]
        )
        msg.html = f"""
        <html>
        <body style="background-color: #ffffff; color: #333333; font-family: Arial, sans-serif; padding: 20px;">
            <div style="text-align: center; margin-bottom: 20px;">
                <img src="http://ticketrush.io/wp-content/uploads/2024/10/TicketRush-Logo.png" alt="TicketRush Logo" style="max-width: 200px;">
            </div>
            <h2 style="color: #ff0000;">Welcome to TicketRush, {user.first_name}!</h2>
            <p>We're thrilled to have you on board! Since you’ve joined TicketRush, you’re all set to start creating memorable events with our simple and secure ticketing platform.</p>
            <p><strong>Access Your Dashboard:</strong> <a href="https://bookings.ticketrush.io/manage_default_questions" style="color: #ff0000;" target="_blank">Login Here</a></p>
            <p>To help you get started, take a look at our <a href="https://www.ticketrush.io/support" style="color: #ff0000;" target="_blank">Tutorials Page</a>. It's full of tips to make the most out of your TicketRush experience.</p>
            <p>We can’t wait to see the incredible events you create!</p>
            <p>Happy Ticketing!<br>— The TicketRush Team</p>
        </body>
        </html>
        """
        mail.send(msg)
        print("Welcome email sent successfully!")
    except Exception as e:
        print(f"Failed to send welcome email: {str(e)}")

@app.route('/reset_request', methods=['GET', 'POST'])
def reset_request():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            send_reset_email(user)
            flash('An email has been sent with instructions to reset your password.', 'info')
        else:
            flash('If an account with that email exists, a reset link has been sent.', 'info')
        return redirect(url_for('login'))

    return render_template('reset_request.html')

def send_reset_email(user):
    """
    Sends a password reset email with a secure token link.
    :param user: User object containing email and token generation method.
    """
    # Generate a token for password reset
    token = user.get_reset_token()

    try:
        # Create the reset email message
        msg = Message(
            subject="Password Reset Request",
            sender=app.config['MAIL_DEFAULT_SENDER'],  # Use the default sender from config
            recipients=[user.email]
        )

        # HTML version of the email body
        msg.html = f"""
        <html>
        <body style="background-color: #ffffff; color: #333333; font-family: Arial, sans-serif; padding: 20px;">
            <!-- TicketRush Logo -->
            <div style="text-align: center; margin-bottom: 20px;">
                <img src="https://ticketrush.io/wp-content/uploads/2024/10/logo_T-1.png" alt="TicketRush Logo" style="max-width: 200px;">
            </div>

            <!-- Reset Password Heading -->
            <h2 style="color: #ff0000;">Password Reset Request</h2>
            <p>
                Hi {user.first_name},<br>
                We received a request to reset your password. Click the button below to reset your password. If you did not request this, please ignore this email.
            </p>

            <!-- Reset Password Button -->
            <div style="text-align: center; margin: 20px 0;">
                <a href="{url_for('reset_password', token=token, _external=True)}" style="display: inline-block; background-color: #ff0000; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Reset Password
                </a>
            </div>

            <p>
                Alternatively, you can copy and paste the following URL into your browser:
                <br><a href="{url_for('reset_password', token=token, _external=True)}" style="color: #ff0000;">{url_for('reset_password', token=token, _external=True)}</a>
            </p>

            <!-- Footer Section -->
            <hr style="border: 1px solid #ff0000;">
            <p style="font-size: 0.9em; color: #666666;">
                <strong>Need Assistance?</strong> Contact our support team at 
                <a href="mailto:support@ticketrush.io" style="color: #ff0000;">support@ticketrush.io</a>.
            </p>
        </body>
        </html>
        """

        # Plain-text version of the email body
        msg.body = f"""Hi {user.first_name},

We received a request to reset your password. To reset your password, visit the following link:
{url_for('reset_password', token=token, _external=True)}

If you did not make this request, you can ignore this email, and no changes will be made.

Need Assistance? Contact our support team at support@ticketrush.io.
"""

        # Send the email
        mail.send(msg)
        print("Password reset email sent successfully!")

    except Exception as e:
        print(f"Failed to send password reset email: {str(e)}")


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.verify_reset_token(token)
    if not user:
        flash('The token is invalid or has expired.', 'warning')
        return redirect(url_for('reset_request'))

    if request.method == 'POST':
        password = request.form.get('password')
        user.password = generate_password_hash(password)
        db.session.commit()

        # Send a confirmation email after successful reset
        send_password_reset_confirmation(user)

        flash('Your password has been updated!', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html')


def send_password_reset_confirmation(user):
    """
    Sends a confirmation email to the user after a successful password reset.
    :param user: User object containing email and other user details.
    """
    try:
        msg = Message(
            subject="Your Password Has Been Reset",
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=[user.email]
        )

        # HTML version of the email body
        msg.html = f"""
        <html>
        <body style="background-color: #ffffff; color: #333333; font-family: Arial, sans-serif; padding: 20px;">
            <!-- TicketRush Logo -->
            <div style="text-align: center; margin-bottom: 20px;">
                <img src="http://ticketrush.io/wp-content/uploads/2024/10/TicketRush-Logo.png" alt="TicketRush Logo" style="max-width: 200px;">
            </div>

            <!-- Confirmation Message -->
            <h2 style="color: #ff0000;">Password Reset Successful</h2>
            <p>
                Hi {user.first_name},<br>
                Your password has been successfully reset. You can now log in using your new password.
            </p>

            <p>
                If you did not request this change, please contact our support team immediately at 
                <a href="mailto:support@ticketrush.io" style="color: #ff0000;">support@ticketrush.io</a>.
            </p>

            <hr style="border: 1px solid #ff0000;">
            <p style="font-size: 0.9em; color: #666666;">
                Thanks for using TicketRush!<br>
                — The TicketRush Team
            </p>
        </body>
        </html>
        """

        # Plain-text version of the email body
        msg.body = f"""Hi {user.first_name},

Your password has been successfully reset. You can now log in using your new password.

If you did not request this change, please contact our support team immediately at support@ticketrush.io.

Thanks for using TicketRush!
— The TicketRush Team
"""

        # Send the email
        mail.send(msg)
        print("Password reset confirmation email sent successfully!")

    except Exception as e:
        print(f"Failed to send password reset confirmation email: {str(e)}")


@app.route('/create_webpage/<int:event_id>')
@login_required
def create_webpage(event_id):
    # Query the database for the event by its ID
    event = Event.query.get_or_404(event_id)

    # Render the create_webpage template with the event details
    return render_template('create_webpage.html', event=event)

# In app.py

@app.route('/submit_webpage_request/<int:event_id>', methods=['POST'])
def submit_webpage_request(event_id):
    event = Event.query.get(event_id)

    # Get files and additional information from the form
    business_logo = request.files.get('business_logo')
    event_picture = request.files.get('event_picture')
    additional_text = request.form.get('additional_text')

    # Prepare the email content
    subject = f"New Webpage Request for Event: {event.name}"
    body = f"""
    A new webpage request has been submitted for the event "{event.name}".\n
    Event details:
    Name: {event.name}
    Date: {event.date}
    Location: {event.location}
    Description: {event.description}
    Start Time: {event.start_time}
    End Time: {event.end_time}
    
    Additional text from user:
    {additional_text}
    """

    # Prepare the email
    msg = Message(
        subject=subject,
        recipients=["support@ticketrush.io"],
        body=body
    )

    # Attach files to the email if they exist
    if business_logo:
        msg.attach(
            filename=business_logo.filename,
            content_type=business_logo.content_type,
            data=business_logo.read()
        )

    if event_picture:
        msg.attach(
            filename=event_picture.filename,
            content_type=event_picture.content_type,
            data=event_picture.read()
        )

    try:
        # Send the email
        mail.send(msg)
        flash("Your webpage request has been submitted. Please allow up to 48 hours for processing.", "success")
        return redirect(url_for('dashboard'))

    except Exception as e:
        print(f"Error sending email: {str(e)}")
        flash("There was an error processing your request. Please try again later.", "error")
        return redirect(url_for('create_webpage', event_id=event_id))


def send_webpage_request_email(event, additional_text, attachments):
    try:
        subject = f"New Webpage Request for Event: {event.name}"
        body = f"""
        <html>
        <body>
            <h2>New Webpage Request Submitted</h2>
            <p>A new webpage request has been submitted for the following event:</p>
            <h3>Event Details:</h3>
            <p>
                <strong>Name:</strong> {event.name}<br>
                <strong>Date:</strong> {event.date}<br>
                <strong>Location:</strong> {event.location}<br>
                <strong>Description:</strong> {event.description}<br>
                <strong>Start Time:</strong> {event.start_time}<br>
                <strong>End Time:</strong> {event.end_time}<br>
                <strong>Additional Text:</strong> {additional_text or 'N/A'}
            </p>
            <p>Please ensure this request is processed within 48 hours.</p>
            <p><strong>TicketRush Support Team</strong></p>
        </body>
        </html>
        """

        # Create and send the email
        msg = Message(
            subject=subject,
            recipients=["support@ticketrush.io"],
            body=body,
            html=body
        )

        # Attach files to the email
        for attachment in attachments:
            with open(attachment, 'rb') as f:
                msg.attach(os.path.basename(attachment), "image/*", f.read())

        mail.send(msg)
        print(f"Webpage request email sent for event '{event.name}' to support@ticketrush.io.")
        
    except Exception as e:
        print(f"Failed to send webpage request email. Error: {str(e)}")
    finally:
        # Optionally, clean up files if stored temporarily
        for filepath in attachments:
            os.remove(filepath)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
