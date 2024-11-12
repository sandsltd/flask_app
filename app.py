from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
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
from datetime import datetime, timezone
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
from dotenv import load_dotenv
import qrcode
from io import BytesIO
from flask import send_file
from PIL import Image
import base64
from sqlalchemy import func
from requests.auth import HTTPBasicAuth
import requests
from werkzeug.utils import secure_filename
import boto3
from botocore.exceptions import NoCredentialsError
from werkzeug.utils import send_from_directory

load_dotenv()

app = Flask(__name__)

# Enable CORS for all routes and origins
CORS(app)  # This will allow all origins by default, but you can restrict it if needed.

# Load environment variables for S3 configuration
S3_BUCKET_NAME = os.getenv('AWS_S3_BUCKET_NAME')
S3_REGION = os.getenv('AWS_REGION')

# Initialize the S3 client
s3 = boto3.client(
    's3',
    region_name=S3_REGION,
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

# Set your Stripe secret key from the environment variable
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

app.secret_key = 'supersecretkey'
login_manager = LoginManager()
login_manager.init_app(app)
 
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

print("Database URI:", app.config['SQLALCHEMY_DATABASE_URI'])

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
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
# Set the upload folder in the configuration
# Load environment variables for WordPress credentials
WORDPRESS_API_URL = 'https://ticketrush.io/wp-json/wp/v2/media'
WORDPRESS_USER = os.getenv('WP-USER')
WORDPRESS_PASSWORD = os.getenv('WP-PASSWORD')

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
    business_logo_url = db.Column(db.String(255), nullable=True)

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
    __tablename__ = 'event'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    start_time = db.Column(db.String(50), nullable=False)
    end_time = db.Column(db.String(50), nullable=False)
    
    
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


    # Foreign key relationship to User
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationship to TicketType
    ticket_types = db.relationship('TicketType', back_populates='event', cascade='all, delete-orphan')
    ticket_quantity = db.Column(db.Integer, nullable=True)  # Total event capacity
    enforce_individual_ticket_limits = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.String(255), nullable=True)  # To store the image file path
    discount_rules = db.relationship('DiscountRule', backref='event', lazy=True)

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
    ticket_number = db.Column(db.String(20), unique=True, nullable=True)  # New ticket_number column
    qr_image_path = db.Column(db.String(255), nullable=True)
    checked_in = db.Column(db.Boolean, default=False)
    check_in_time = db.Column(db.DateTime)

    ticket_type_id = db.Column(db.Integer, db.ForeignKey('ticket_type.id'), nullable=False)
    
    # Relationship to TicketType
    ticket_type = db.relationship('TicketType', backref=db.backref('attendees', lazy=True))
    
    # Relationship to the Event model
    event = db.relationship('Event', backref=db.backref('attendees', passive_deletes=True))

    @property
    def ticket_answers_dict(self):
        if not hasattr(self, '_ticket_answers_dict'):
            if self.ticket_answers:
                try:
                    self._ticket_answers_dict = json.loads(self.ticket_answers)
                except json.JSONDecodeError:
                    self._ticket_answers_dict = {}
            else:
                self._ticket_answers_dict = {}
        return self._ticket_answers_dict

    @property
    def billing_details_dict(self):
        if not hasattr(self, '_billing_details_dict'):
            if self.billing_details:
                try:
                    self._billing_details_dict = json.loads(self.billing_details)
                except json.JSONDecodeError:
                    self._billing_details_dict = {}
            else:
                self._billing_details_dict = {}
        return self._billing_details_dict




class DefaultQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question = db.Column(db.String(255), nullable=False)

class TicketType(db.Model):
    __tablename__ = 'ticket_type'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=True)  # Allowing NULLs now

    # Relationship back to Event
    event = db.relationship('Event', back_populates='ticket_types')

# Add this with your other models
class DiscountRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    discount_type = db.Column(db.String(20), nullable=False)  # 'bulk', 'early_bird', 'promo_code'
    discount_percent = db.Column(db.Float, nullable=False)
    
    # Bulk purchase fields
    min_tickets = db.Column(db.Integer)
    apply_to = db.Column(db.String(20))  # 'all' or 'additional'
    
    # Early bird fields
    valid_until = db.Column(db.DateTime)
    max_early_bird_tickets = db.Column(db.Integer)
    
    # Promo code fields
    promo_code = db.Column(db.String(50))
    max_uses = db.Column(db.Integer)
    uses_count = db.Column(db.Integer, default=0)
    
    def calculate_discount(self, quantity, original_price, promo_code=None):
        """
        Calculate the discount amount based on the rule type and conditions.
        
        Args:
            quantity (int): Number of tickets being purchased
            original_price (float): Original price per ticket
            promo_code (str, optional): Promo code provided by customer
            
        Returns:
            float: Discount amount to be applied
        """
        if self.discount_type == 'bulk' and quantity >= self.min_tickets:
            if self.apply_to == 'all':
                return (original_price * quantity) * (self.discount_percent / 100)
            else:  # 'additional'
                return (original_price * (quantity - 1)) * (self.discount_percent / 100)
                
        elif self.discount_type == 'early_bird' and datetime.utcnow() < self.valid_until:
            if not self.max_early_bird_tickets or self.max_early_bird_tickets >= quantity:
                return (original_price * quantity) * (self.discount_percent / 100)
            
        elif (self.discount_type == 'promo_code' and 
              promo_code == self.promo_code and 
              (not self.max_uses or self.uses_count < self.max_uses)):
            return (original_price * quantity) * (self.discount_percent / 100)
        
        return 0

# Generate a random unique ID with 15 characters
def generate_unique_id():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(15))

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

    
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
                                "We're excited to have you here! It looks like it's your first time logging in, so we recommend starting with our "
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
        # Calculate total tickets sold and revenue for the event
        succeeded_attendees = Attendee.query.filter_by(event_id=event.id, payment_status='succeeded').all()
        tickets_sold = len(succeeded_attendees)

        # Adjust total ticket quantity calculation based on enforcement setting
        if event.enforce_individual_ticket_limits:
            total_ticket_quantity = sum([ticket_type.quantity or 0 for ticket_type in event.ticket_types])
        else:
            total_ticket_quantity = event.ticket_quantity or 0

        # Calculate tickets sold and remaining per ticket type
        ticket_breakdown = []
        for ticket_type in event.ticket_types:
            # Count the number of attendees for this ticket type
            tickets_sold_type = Attendee.query.filter_by(
                event_id=event.id,
                ticket_type_id=ticket_type.id,
                payment_status='succeeded'
            ).count()
            if event.enforce_individual_ticket_limits:
                tickets_remaining_type = (ticket_type.quantity or 0) - tickets_sold_type
                total_quantity = ticket_type.quantity
            else:
                # When individual limits are not enforced, total_quantity is the event's total capacity
                tickets_remaining_type = (total_ticket_quantity or 0) - tickets_sold
                total_quantity = total_ticket_quantity

            ticket_breakdown.append({
                'name': ticket_type.name,
                'price': ticket_type.price,
                'tickets_sold': tickets_sold_type,
                'tickets_remaining': tickets_remaining_type,
                'total_quantity': total_quantity
            })

        # Calculate overall tickets remaining
        tickets_remaining = total_ticket_quantity - tickets_sold

        # Calculate total revenue for the event
        event_revenue = sum([attendee.ticket_price_at_purchase for attendee in succeeded_attendees])

        total_tickets_sold += tickets_sold
        total_revenue += event_revenue

        event_date = str_to_date(event.date) if event.date else None
        event_status = "Upcoming" if event_date and event_date >= datetime.now() else "Past"

        # Add discount rules
        discount_rules = DiscountRule.query.filter_by(event_id=event.id).all()
        discount_rules_data = [{
            'discount_type': rule.discount_type,
            'discount_percent': rule.discount_percent,
            'min_tickets': rule.min_tickets if rule.discount_type == 'bulk' else None,
            'apply_to': rule.apply_to if rule.discount_type == 'bulk' else None,
            'valid_until': rule.valid_until if rule.discount_type == 'early_bird' else None,
            'max_tickets': rule.max_early_bird_tickets if rule.discount_type == 'early_bird' else None,
            'code': rule.promo_code if rule.discount_type == 'promo_code' else None,
            'max_uses': rule.max_uses if rule.discount_type == 'promo_code' else None,
            'uses_left': rule.max_uses - rule.times_used if rule.discount_type == 'promo_code' else None
        } for rule in discount_rules]

        event_data.append({
            'name': event.name,
            'date': event.date,
            'location': event.location,
            'description': event.description,
            'tickets_sold': tickets_sold,
            'ticket_quantity': total_ticket_quantity,
            'tickets_remaining': tickets_remaining,
            'total_revenue': event_revenue,
            'status': event_status,
            'id': event.id,
            'ticket_breakdown': ticket_breakdown,
            'enforce_individual_ticket_limits': event.enforce_individual_ticket_limits,
            'discount_rules': discount_rules_data
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
                created_at=datetime.now(timezone.utc),
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









@app.route('/create_event', methods=['GET', 'POST'])
@login_required
def create_event():
    if request.method == 'POST':
        try:
            # ------------------------------
            # 1. Collect and Validate Form Data
            # ------------------------------
            
            # Basic event details
            name = request.form.get('name', '').strip()
            date_str = request.form.get('date', '').strip()
            start_time = request.form.get('start_time', '').strip()
            end_time = request.form.get('end_time', '').strip()
            location = request.form.get('location', '').strip()
            description = request.form.get('description', '').strip()

            # Validate basic event details
            if not all([name, date_str, start_time, end_time, location, description]):
                flash('Please fill in all required fields for the event.', 'danger')
                return redirect(url_for('create_event'))

            # Parse event date
            try:
                event_date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
                return redirect(url_for('create_event'))

            # Handle recurrence details
            recurrence = request.form.get('recurrence', 'none')  # Default to 'none'
            occurrences_str = request.form.get('occurrences', '1')  # Get as string

            if recurrence != 'none':
                try:
                    occurrences = int(occurrences_str)
                    if occurrences < 1:
                        flash('Number of occurrences must be at least 1.', 'danger')
                        return redirect(url_for('create_event'))
                    elif occurrences > 100:
                        flash('Number of occurrences cannot exceed 100.', 'danger')
                        return redirect(url_for('create_event'))
                except ValueError:
                    flash('Invalid number of occurrences. Please enter a valid integer.', 'danger')
                    return redirect(url_for('create_event'))
            else:
                occurrences = 1  # Default to 1 if no recurrence

            # Enforce individual ticket limits
            enforce_limits = request.form.get('enforce_individual_ticket_limits') == 'on'
            total_ticket_quantity = None
            if not enforce_limits:
                total_ticket_quantity = request.form.get('total_ticket_quantity', type=int)
                if not total_ticket_quantity or total_ticket_quantity < 1:
                    flash('Total ticket quantity must be a positive integer.', 'danger')
                    return redirect(url_for('create_event'))

            # Process ticket types
            ticket_names = request.form.getlist('ticket_name[]')
            ticket_prices = request.form.getlist('ticket_price[]')
            ticket_quantities = []
            if enforce_limits:
                ticket_quantities = request.form.getlist('ticket_quantity[]')
                # Validate ticket quantities
                for qty in ticket_quantities:
                    if qty:
                        try:
                            qty_int = int(qty)
                            if qty_int < 1:
                                flash('Ticket quantities must be positive integers.', 'danger')
                                return redirect(url_for('create_event'))
                        except ValueError:
                            flash('Invalid ticket quantity. Please enter valid integers.', 'danger')
                            return redirect(url_for('create_event'))
            else:
                ticket_quantities = [None] * len(ticket_names)  # No individual limits

            # Ensure at least one ticket type is provided
            if not ticket_names or not any(ticket_names):
                flash('Please provide at least one ticket type.', 'danger')
                return redirect(url_for('create_event'))

            # Capture custom questions for the event
            custom_questions = [request.form.get(f'custom_question_{i}') for i in range(1, 11)]

            # Fetch default questions from the database
            default_questions = DefaultQuestion.query.filter_by(user_id=current_user.id).all()
            default_question_texts = [dq.question for dq in default_questions]

            # ------------------------------
            # 2. Define Date Increment Based on Recurrence
            # ------------------------------
            
            def get_next_date(current_date, pattern):
                if pattern == 'daily':
                    return current_date + timedelta(days=1)
                elif pattern == 'weekly':
                    return current_date + timedelta(weeks=1)
                elif pattern == 'monthly':
                    # Properly handle month increments, accounting for year changes and varying month lengths
                    month = current_date.month
                    year = current_date.year
                    if month == 12:
                        month = 1
                        year += 1
                    else:
                        month += 1
                    # Handle day overflow (e.g., February 30th)
                    day = min(current_date.day, [31,
                        29 if (year % 4 == 0 and not year % 100 == 0) or (year % 400 == 0) else 28,
                        31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month-1])
                    return datetime(year, month, day)
                return current_date  # No recurrence

            # ------------------------------
            # 3. Handle Image Upload
            # ------------------------------
            

            image_url = None
            event_image = request.files.get('event_image')
            if event_image and event_image.filename != '':
                image_url = upload_to_s3(event_image, "event-logos")  # Specify the folder prefix here
                if not image_url:
                    flash("Failed to upload event image to S3", "danger")
                    return redirect(url_for('create_event'))

            # ------------------------------
            # 4. Create Each Event Occurrence
            # ------------------------------
            
            current_date = event_date
            for i in range(occurrences):
                # Create event instance with custom and default questions
                event = Event(
                    user_id=current_user.id,
                    name=name,
                    date=current_date.strftime('%Y-%m-%d'),  # Store as string
                    start_time=start_time,
                    end_time=end_time,
                    location=location,
                    description=description,
                    ticket_quantity=total_ticket_quantity,
                    enforce_individual_ticket_limits=enforce_limits,
                    image_url=image_url,  # Store the image URL in the event record
                    custom_question_1=custom_questions[0] or (default_question_texts[0] if len(default_question_texts) > 0 else None),
                    custom_question_2=custom_questions[1] or (default_question_texts[1] if len(default_question_texts) > 1 else None),
                    custom_question_3=custom_questions[2] or (default_question_texts[2] if len(default_question_texts) > 2 else None),
                    custom_question_4=custom_questions[3] or (default_question_texts[3] if len(default_question_texts) > 3 else None),
                    custom_question_5=custom_questions[4] or (default_question_texts[4] if len(default_question_texts) > 4 else None),
                    custom_question_6=custom_questions[5] or (default_question_texts[5] if len(default_question_texts) > 5 else None),
                    custom_question_7=custom_questions[6] or (default_question_texts[6] if len(default_question_texts) > 6 else None),
                    custom_question_8=custom_questions[7] or (default_question_texts[7] if len(default_question_texts) > 7 else None),
                    custom_question_9=custom_questions[8] or (default_question_texts[8] if len(default_question_texts) > 8 else None),
                    custom_question_10=custom_questions[9] or (default_question_texts[9] if len(default_question_texts) > 9 else None),
                )
                db.session.add(event)
                db.session.commit()

                # Add ticket types for this event
                for t_name, t_price, t_quantity in zip(ticket_names, ticket_prices, ticket_quantities):
                    if t_name and t_price:
                        try:
                            ticket_type = TicketType(
                                event_id=event.id,
                                name=t_name,
                                price=float(t_price),
                                quantity=int(t_quantity) if enforce_limits and t_quantity else None
                            )
                            db.session.add(ticket_type)
                        except ValueError:
                            flash('Invalid ticket price or quantity. Please ensure they are valid numbers.', 'danger')
                            db.session.rollback()
                            return redirect(url_for('create_event'))
                db.session.commit()

                # Update current_date for next recurrence
                if i < occurrences - 1:
                    current_date = get_next_date(current_date, recurrence)

            # Process discount rules
            discount_types = request.form.getlist('discount_type[]')
            print("\n=== Starting Discount Rules Processing ===")
            print(f"Found discount types: {discount_types}")

            for i, discount_type in enumerate(discount_types):
                try:
                    print(f"\nProcessing discount rule {i+1}:")
                    print(f"Discount type: {discount_type}")
                    
                    # Get and print all relevant form data
                    discount_percent = float(request.form.getlist('discount_percent[]')[i])
                    print(f"Discount percentage: {discount_percent}")

                    discount_rule = DiscountRule(
                        event_id=event.id,
                        discount_type=discount_type,
                        discount_percent=discount_percent
                    )

                    if discount_type == 'early_bird':
                        valid_until = request.form.getlist('valid_until[]')[i]
                        max_tickets = request.form.getlist('max_early_bird_tickets[]')[i]
                        print(f"Early Bird details:")
                        print(f"- Valid until: {valid_until}")
                        print(f"- Max tickets: {max_tickets}")
                        
                        discount_rule.valid_until = datetime.strptime(valid_until, '%Y-%m-%dT%H:%M')
                        discount_rule.max_early_bird_tickets = int(max_tickets)
                        print(f"Processed Early Bird rule: valid until {discount_rule.valid_until}, max tickets: {discount_rule.max_early_bird_tickets}")

                    elif discount_type == 'bulk':
                        discount_rule.min_tickets = int(request.form.getlist('min_tickets[]')[i])
                        discount_rule.apply_to = request.form.getlist('discount_apply_to[]')[i]
                        print(f"Bulk discount details:")
                        print(f"- Min tickets: {discount_rule.min_tickets}")
                        print(f"- Apply to: {discount_rule.apply_to}")

                    print(f"Adding discount rule to session: {discount_rule.__dict__}")
                    db.session.add(discount_rule)

                except (ValueError, IndexError) as e:
                    print(f"ERROR processing discount rule: {str(e)}")
                    print(f"Form data for debugging:")
                    print(f"- All discount_percent values: {request.form.getlist('discount_percent[]')}")
                    print(f"- All valid_until values: {request.form.getlist('valid_until[]')}")
                    print(f"- All max_tickets values: {request.form.getlist('max_early_bird_tickets[]')}")
                    continue

            print("\nCommitting all changes to database...")
            db.session.commit()
            print("Successfully committed changes!")
            print("=== Finished Discount Rules Processing ===\n")

            flash(f'{occurrences} occurrence(s) of the event "{name}" created successfully!', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            print(f"\nCRITICAL ERROR in create_event:")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("Full form data:")
            for key in request.form:
                print(f"- {key}: {request.form.getlist(key)}")
            
            db.session.rollback()
            flash('An unexpected error occurred while creating the event. Please try again.', 'danger')
            return redirect(url_for('create_event'))

    # Fetch and pass default questions for display in form
    default_questions = DefaultQuestion.query.filter_by(user_id=current_user.id).all()
    return render_template('create_event.html', default_questions=default_questions)






@app.route('/reset_db')
def reset_db():
    try:
        db.drop_all()
        db.create_all()
        return "Database reset and tables recreated!"
    except Exception as e:
        return f"An error occurred during reset: {str(e)}"



from markupsafe import escape

from datetime import datetime

@app.route('/embed/<unique_id>')
def embed_events(unique_id):
    try:
        # Find the user
        user = User.query.filter_by(unique_id=unique_id).first()
        if not user:
            print(f"User not found for unique_id: {unique_id}")
            return "document.write(`<div id='ticketrush-embed'><p>User not found</p></div>`);"

        # Get user events
        user_events = Event.query.filter_by(user_id=user.id).all()
        if not user_events:
            print(f"No events found for user: {user.id}")
            return "document.write(`<div id='ticketrush-embed'><p>No upcoming events available.</p></div>`);"

        # Filter future events with proper error handling
        future_events = []
        current_date = datetime.now().date()
        
        def parse_date(date_str):
            """Try multiple date formats to parse the date string"""
            formats = [
                '%Y-%m-%d',  # 2024-01-10
                '%y-%m-%d',  # 24-01-10
                '%d-%m-%y',  # 10-01-24
                '%d-%m-%Y',  # 10-01-2024
                '%Y/%m/%d',  # 2024/01/10
                '%d/%m/%Y',  # 10/01/2024
                '%m-%d-%y',  # 01-10-24
                '%m-%d-%Y'   # 01-10-2024
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            
            # If no format matches, raise an error
            raise ValueError(f"Unable to parse date: {date_str}")

        for event in user_events:
            try:
                # Try to parse the date with our helper function
                event_date = parse_date(event.date)
                if event_date >= current_date:
                    # Store the parsed date for later use
                    event.parsed_date = event_date
                    future_events.append(event)
            except (ValueError, TypeError) as e:
                print(f"Error parsing date for event {event.id}: {e}")
                continue

        # Sort events by parsed date
        future_events.sort(key=lambda x: getattr(x, 'parsed_date', datetime.max.date()))

        # Begin constructing the HTML
        events_html = '''
        <style>
            #ticketrush-embed * {
                box-sizing: border-box;
                font-family: Arial, sans-serif;
            }
            #ticketrush-embed {
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            .event-card {
                border: 1px solid #e0e0e0;
                margin-bottom: 20px;
                padding: 15px;
                border-radius: 5px;
            }
            .event-title {
                font-size: 1.2em;
                margin-bottom: 10px;
            }
            .event-details {
                margin-bottom: 10px;
            }
            .book-button {
                background-color: #ff0000;
                color: white;
                padding: 10px 20px;
                text-decoration: none;
                border-radius: 5px;
                display: inline-block;
            }
            .book-button:hover {
                background-color: #cc0000;
            }
        </style>
        <div id="ticketrush-embed">
        '''

        if not future_events:
            events_html += '<p>No upcoming events available.</p>'
        else:
            for event in future_events:
                try:
                    # Calculate tickets sold
                    succeeded_attendees = Attendee.query.filter_by(
                        event_id=event.id, 
                        payment_status='succeeded'
                    ).all()
                    tickets_sold = sum(attendee.tickets_purchased for attendee in succeeded_attendees)

                    # Calculate tickets available
                    if event.ticket_quantity is not None:
                        tickets_available = event.ticket_quantity - tickets_sold
                    else:
                        tickets_available = "Unlimited"

                    # Format date using the previously parsed date
                    formatted_date = event.parsed_date.strftime('%A %d %B %Y')

                    # Get ticket types
                    ticket_types = TicketType.query.filter_by(event_id=event.id).all()
                    ticket_info = "Free" if not ticket_types else "<br>".join(
                        f"{escape(tt.name)}: {'Free' if tt.price == 0 else f'£{tt.price:.2f}'}"
                        for tt in ticket_types
                    )

                    # Add event card
                    events_html += f'''
                    <div class="event-card">
                        <div class="event-title">{escape(event.name)}</div>
                        <div class="event-details">
                            <strong>Date:</strong> {formatted_date}<br>
                            <strong>Time:</strong> {event.start_time} - {event.end_time}<br>
                            <strong>Location:</strong> {escape(event.location)}<br>
                            <strong>Price:</strong><br>{ticket_info}
                        </div>
                    '''

                    if tickets_available == "Unlimited" or tickets_available > 0:
                        events_html += f'''
                        <a href="https://bookings.ticketrush.io/purchase/{event.id}" 
                           class="book-button" target="_blank">Book Tickets</a>
                        '''
                    else:
                        events_html += '<p style="color: red;">Sold Out</p>'

                    events_html += '</div>'

                except Exception as e:
                    print(f"Error processing event {event.id}: {e}")
                    continue

        events_html += '''
            <div style="text-align: center; margin-top: 20px; font-size: 0.8em;">
                Powered by <a href="https://www.ticketrush.io" target="_blank">TicketRush</a>
            </div>
        </div>
        '''

        # Return JavaScript
        response = f"document.write(`{events_html}`);"
        return Response(response, mimetype='application/javascript')

    except Exception as e:
        print(f"Unexpected error in embed_events: {e}")
        return "document.write(`<div id='ticketrush-embed'><p>Error loading events</p></div>`);"

@app.route('/cancel')
def cancel():
    return "Payment canceled. You can try again."


@app.route('/manage-default-questions', methods=['GET', 'POST'])
@login_required
def manage_default_questions():
    user = User.query.get(current_user.id)

    if request.method == 'POST':
        try:
            # Collect form data for user profile updates
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
                if not re.match(r'^https?://', terms_link):
                    terms_link = 'https://' + terms_link
                user.terms = terms_link

            if request.method == 'POST':
                # Handle the logo file upload
                logo_file = request.files.get('business_logo')
                logo_url = None

                if logo_file:
                    print(f"Received file: {logo_file.filename}")

                    if allowed_file(logo_file.filename):
                        # Upload the file to S3 and save the URL
                        logo_url = upload_to_s3(logo_file, "business-logos")
                        
                        if logo_url:
                            # Update the user's business logo URL in the database
                            current_user.business_logo_url = logo_url
                            db.session.add(current_user)
                            db.session.commit()
                            flash("Business logo uploaded successfully!", "success")
                        else:
                            flash("There was an error uploading your business logo to S3. Please try again.", "danger")
                    else:
                        print("File type not allowed.")
                        flash('Unsupported file type for business logo. Please upload a PNG, JPG, JPEG, or GIF image.', 'danger')
                else:
                    print("No file received for 'business_logo'.")

            # Process default questions
            questions = request.form.getlist('questions[]')
            existing_questions = DefaultQuestion.query.filter_by(user_id=user.id).all()

            # Update existing questions
            for i, question_text in enumerate(questions):
                question_text = question_text.strip()
                if i < len(existing_questions):
                    existing_questions[i].question = question_text
                else:
                    if question_text:
                        new_question = DefaultQuestion(user_id=user.id, question=question_text)
                        db.session.add(new_question)

            # Remove extra questions if fewer are submitted
            if len(questions) < len(existing_questions):
                for q in existing_questions[len(questions):]:
                    db.session.delete(q)

            # Commit changes to the database
            db.session.commit()
            flash('Account settings successfully updated.', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            db.session.rollback()
            print(f"Error during POST request: {e}")
            flash('An error occurred while updating your account settings. Please try again.', 'danger')

    # GET request - render the form
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
@app.route('/purchase/<int:event_id>/<string:promo_code>', methods=['GET', 'POST'])
def purchase(event_id, promo_code=None):
    try:
        event = Event.query.get_or_404(event_id)
        print(f"Event ID: {event.id}, Ticket Quantity: {event.ticket_quantity}")
        organizer = User.query.get(event.user_id)
        if not organizer:
            return "Event organizer not found", 404
        
        # Assign the business logo URL to logo_url
        organizer.logo_url = organizer.business_logo_url
        # Initialize variables
        attendees = []
        total_amount = 0  # Total amount in pence
        line_items = []
        booking_fee_pence = 0  # Initialize booking fee
        total_tickets_requested = 0
        total_tickets_sold = 0  # Initialize to 0

        # Collect questions - Move this up before the GET/POST split
        default_questions = DefaultQuestion.query.filter_by(user_id=organizer.id).order_by(DefaultQuestion.id).all()
        default_question_texts = [dq.question for dq in default_questions]
        custom_questions = [getattr(event, f'custom_question_{i}') for i in range(1, 11) if getattr(event, f'custom_question_{i}', None)]
        all_questions = default_question_texts + [q for q in custom_questions if q not in default_question_texts]

        # Fetch ticket types
        ticket_types = event.ticket_types
        
        if request.method == 'POST':
            try:
                session_id = str(uuid4())
                full_name = request.form.get('full_name')
                email = request.form.get('email')
                phone_number = request.form.get('phone_number')

                # Validate required fields
                if not all([full_name, email, phone_number]):
                    flash('Please fill in all required fields.')
                    return redirect(url_for('purchase', event_id=event_id))

                if organizer.terms and organizer.terms.lower() != 'none':
                    if not request.form.get('accept_organizer_terms'):
                        flash("You must accept the event organizer's Terms and Conditions.")
                        return redirect(url_for('purchase', event_id=event_id))

                if not request.form.get('accept_platform_terms'):
                    flash("You must accept the platform's Terms and Conditions.")
                    return redirect(url_for('purchase', event_id=event_id))

                # Initialize variables
                attendees = []
                line_items = []
                booking_fee_pence = 0  # Initialize booking fee
                total_tickets_requested = 0

                # Collect quantities for each ticket type
                quantities = {}
                for ticket_type in ticket_types:
                    quantity_str = request.form.get(f'quantity_{ticket_type.id}', '0')
                    quantity = int(quantity_str)
                    quantities[ticket_type.id] = quantity
                    if quantity > 0:
                        total_tickets_requested += quantity

                        if event.enforce_individual_ticket_limits and ticket_type.quantity is not None:
                            # Check if requested quantity exceeds available tickets for this type
                            tickets_sold_type = Attendee.query.filter_by(
                                event_id=event.id,
                                ticket_type_id=ticket_type.id,
                                payment_status='succeeded'
                            ).count()
                            tickets_remaining = ticket_type.quantity - tickets_sold_type
                            if quantity > tickets_remaining:
                                flash(f"Cannot purchase {quantity} tickets for {ticket_type.name}. Only {tickets_remaining} tickets are available.")
                                return redirect(url_for('purchase', event_id=event_id))
                        else:
                            # Will check total capacity later
                            pass

                # If individual ticket limits are not enforced, check total event capacity
                if not event.enforce_individual_ticket_limits:
                    total_tickets_sold = db.session.query(
                        func.sum(Attendee.tickets_purchased)
                    ).filter_by(event_id=event.id, payment_status='succeeded').scalar() or 0
                    tickets_available = event.ticket_quantity - total_tickets_sold
                    if total_tickets_requested > tickets_available:
                        flash(f"Cannot purchase {total_tickets_requested} tickets. Only {tickets_available} tickets are available.")
                        return redirect(url_for('purchase', event_id=event_id))
                else:
                    # When individual ticket limits are enforced, tickets_available isn't used in the same way
                    tickets_available = None  # Or handle accordingly

                # Collect custom questions
                questions = all_questions
                attendee_answers = {}

                # Collect answers for each ticket
                for ticket_type in ticket_types:
                    quantity = quantities[ticket_type.id]
                    for i in range(quantity):
                        answers = {}
                        for q_index, question in enumerate(questions):
                            answer_key = f'ticket_{ticket_type.id}_{i}_question_{q_index}'
                            answer = request.form.get(answer_key)
                            if not answer:
                                flash(f'Please answer all questions for {ticket_type.name} Ticket {i + 1}.')
                                return redirect(url_for('purchase', event_id=event_id))
                            answers[question] = answer
                        attendee_answers[(ticket_type.id, i)] = answers

                # Create Attendee entries and calculate amounts
                for ticket_type in ticket_types:
                    quantity = quantities[ticket_type.id]
                    if quantity > 0:
                        for i in range(quantity):
                            ticket_number = generate_unique_ticket_number()
                            answers = attendee_answers.get((ticket_type.id, i), {})

                            attendee = Attendee(
                                event_id=event.id,
                                ticket_type_id=ticket_type.id,
                                ticket_answers=json.dumps(answers),
                                payment_status='pending',
                                full_name=full_name,
                                email=email,
                                phone_number=phone_number,
                                tickets_purchased=1,
                                ticket_price_at_purchase=ticket_type.price,
                                session_id=session_id,
                                created_at=datetime.now(timezone.utc),
                                ticket_number=ticket_number
                            )
                            db.session.add(attendee)
                            attendees.append(attendee)

                # Calculate the total ticket price
                total_ticket_price_pence = sum(
                    int(ticket_type.price * 100) * quantities[ticket_type.id]
                    for ticket_type in ticket_types
                    if quantities[ticket_type.id] > 0
                )

                # Calculate the total number of tickets
                total_tickets = sum(quantities[ticket_type.id] for ticket_type in ticket_types)

                # Calculate the platform fee (30p per ticket)
                platform_fee_pence = 30 * total_tickets

                # Calculate the subtotal (ticket price + platform fee)
                subtotal_pence = total_ticket_price_pence + platform_fee_pence

                # Calculate the Stripe percentage fee (1.4% of subtotal)
                stripe_percent_fee_pence = int(subtotal_pence * 0.014)

                # Add the fixed Stripe fee (20p)
                stripe_fixed_fee_pence = 20

                # Calculate the total booking fee
                booking_fee_pence = platform_fee_pence + stripe_percent_fee_pence + stripe_fixed_fee_pence

                # Calculate the total charge to the buyer
                total_charge_pence = total_ticket_price_pence + booking_fee_pence

                if not attendees:
                    flash('Please select at least one ticket.')
                    return redirect(url_for('purchase', event_id=event_id))

                db.session.commit()

                # Handle free tickets
                if total_charge_pence == 0:
                    for attendee in attendees:
                        attendee.payment_status = 'succeeded'  # Mark as paid for free tickets
                    db.session.commit()

                    # Set up billing details for the confirmation email
                    billing_details = {'name': full_name, 'email': email, 'phone': phone_number}

                    # Send confirmation emails for free tickets
                    send_confirmation_email_to_attendee(attendees, billing_details)
                    send_confirmation_email_to_organizer(organizer, attendees, billing_details, event)

                    flash('Your free ticket(s) have been booked successfully!')
                    return redirect(url_for('success', session_id=session_id))

                else:
                    # Create Stripe checkout session
                    checkout_session = stripe.checkout.Session.create(
                        payment_method_types=['card'],
                        line_items=[{
                            'price_data': {
                                'currency': 'gbp',
                                'unit_amount': total_charge_pence,
                                'product_data': {
                                    'name': f'Tickets for {event.name}',
                                },
                            },
                            'quantity': 1,
                        }],
                        mode='payment',
                        success_url=url_for('success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                        cancel_url=url_for('cancel', _external=True),
                        payment_intent_data={
                            'application_fee_amount': booking_fee_pence,
                            'transfer_data': {
                                'destination': organizer.stripe_connect_id,
                            },
                        }
                    )

                    return redirect(checkout_session.url)

            except Exception as e:
                app.logger.error(f"Error creating checkout session: {str(e)}")
                flash('An error occurred while processing your payment. Please try again.', 'error')
                return redirect(url_for('purchase', event_id=event_id))

        else:
            # Get active discount rules
            discount_rules = DiscountRule.query.filter_by(event_id=event_id).all()
            active_discount = None
            
            for rule in discount_rules:
                if rule.discount_type == 'early_bird':
                    if rule.valid_until and datetime.now() < rule.valid_until:
                        active_discount = {
                            'type': 'early_bird',
                            'percentage': rule.discount_percent,
                            'valid_until': rule.valid_until.isoformat(),
                            'max_tickets': rule.max_early_bird_tickets
                        }
                        break
                elif rule.discount_type == 'bulk':
                    active_discount = {
                        'type': 'bulk',
                        'percentage': rule.discount_percent,
                        'minTickets': rule.min_tickets,
                        'apply_to': rule.apply_to
                    }
                    break
                elif rule.discount_type == 'promo_code':
                    active_discount = {
                        'type': 'promo_code',
                        'percentage': rule.discount_percent
                    }
                    break

            platform_terms_link = 'https://ticketrush.io/wp-content/uploads/2024/10/TicketRush-Terms-of-Service-25th-October-2024.pdf'
            organizer_terms_link = organizer.terms if organizer.terms and organizer.terms.lower() != 'none' else None

            # Calculate tickets available for total capacity events
            if not event.enforce_individual_ticket_limits:
                total_tickets_sold = db.session.query(
                    func.sum(Attendee.tickets_purchased)
                ).filter_by(event_id=event.id, payment_status='succeeded').scalar() or 0
                tickets_available = event.ticket_quantity - total_tickets_sold
            else:
                tickets_available = None

            return render_template(
                'purchase.html',
                event=event,
                organizer=organizer,
                questions=all_questions,
                organizer_terms_link=organizer_terms_link,
                platform_terms_link=platform_terms_link,
                ticket_types=ticket_types,
                enforce_individual_ticket_limits=event.enforce_individual_ticket_limits,
                tickets_available=tickets_available,
                discount_config=active_discount
            )

    except Exception as e:
        app.logger.error(f"Error in purchase route: {str(e)}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('dashboard'))


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

        # Fetch event and organizer details
        event = Event.query.get(first_attendee.event_id)
        organizer = User.query.get(event.user_id)

        # Calculate total tickets and total price
        total_tickets = sum(attendee.tickets_purchased for attendee in attendees)
        total_price = sum(attendee.ticket_price_at_purchase * attendee.tickets_purchased for attendee in attendees)

        # Generate calendar links
        start_time = event.start_time.replace(':', '')
        end_time = event.end_time.replace(':', '')
        event_date = event.date.replace('-', '')
        google_calendar_url = (
            f"https://www.google.com/calendar/render?"
            f"action=TEMPLATE&text={urllib.parse.quote(event.name)}"
            f"&dates={event_date}T{start_time}Z/{event_date}T{end_time}Z"
            f"&details=Event+at+{urllib.parse.quote(event.location)}"
            f"&location={urllib.parse.quote(event.location)}"
            f"&sf=true&output=xml"
        )
        ics_file_url = url_for('download_ics', event_id=event.id, _external=True)

        # Organizer details section
        organizer_details = f"""
        <p>
            <strong>Business:</strong> {organizer.business_name}<br>
            <strong>Website:</strong> <a href="{organizer.website_url or '#'}" style="color: #ff0000;">{organizer.website_url or 'No website provided'}</a><br>
        """
        if organizer.terms and organizer.terms.lower() != 'none':
            organizer_details += f"""
            <strong>Organiser's Terms:</strong> <a href="{organizer.terms}" style="color: #ff0000;">{organizer.terms}</a>
            """
        organizer_details += "</p>"

        # Generate QR codes for each ticket and label by ticket type
        qr_code_images = []
        for attendee in attendees:
            qr_data = attendee.ticket_number
            qr_img = qrcode.make(qr_data)
            buffer = BytesIO()
            qr_img.save(buffer, format="PNG")
            qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            ticket_type_label = attendee.ticket_type.name if attendee.ticket_type else "General Admission"
            qr_code_images.append((ticket_type_label, qr_base64))

        # Construct email body with QR codes and details
        body = f"""
        <html>
        <body style="background-color: #ffffff; color: #000000; font-family: Arial, sans-serif; padding: 20px;">
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
                <a href="{ics_file_url}" style="display: inline-block; background-color: #ff0000; color: #ffffff; padding: 10px 15px; text-decoration: none; border-radius: 5px;">Apple/iOS Calendar</a>
                <a href="{google_calendar_url}" style="display: inline-block; background-color: #ff0000; color: #ffffff; padding: 10px 15px; text-decoration: none; border-radius: 5px;">Google Calendar</a>
            </div>

            <hr style="border: 1px solid #ff0000;">
            <h3 style="color: #ff0000;">Your QR Code(s) for Event Entry:</h3>
            <p>Please present the following QR code(s) at the event entrance:</p>
            <div style="display: flex; flex-wrap: wrap;">
        """

        # Add each QR code image to the email body with the ticket type label
        for label, qr_base64 in qr_code_images:
            body += f"""
            <div style="text-align: center; margin: 10px;">
                <p><strong>{label}</strong></p>
                <img src="data:image/png;base64,{qr_base64}" alt="QR Code" style="width: 150px; height: 150px;">
            </div>
            """

        # Finish the email body
        body += f"""
            </div>
            <hr style="border: 1px solid #ff0000;">
            <h3 style="color: #ff0000;">Organiser Details:</h3>
            {organizer_details}

            <hr style="border: 1px solid #ff0000;">
            <h3 style="color: #ff0000;">Need Help?</h3>
            <p>
                For questions about the event, reach out directly to {organizer.business_name} at <a href="mailto:{organizer.email}" style="color: #ff0000;">{organizer.email}</a>.
            </p>

            <p style="color: #ff0000;"><strong>Powered by TicketRush</strong></p>
        </body>
        </html>
        """

        # Send the email
        msg = Message(
            subject=f"Your Ticket Confirmation for {event.name}",
            recipients=[first_attendee.email],
            body=body,
            html=body  # HTML body for rich content
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



# Update handle_checkout_session to generate QR codes
def handle_checkout_session(session):
    session_id = session.get('metadata', {}).get('session_id')
    if not session_id:
        print("No session ID found in metadata.")
        return

    # Retrieve all attendees for this session ID
    attendees = Attendee.query.filter_by(session_id=session_id).all()

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

    # Update attendee records and generate QR codes
    for attendee in attendees:
        attendee.billing_details = json.dumps(billing_details)
        attendee.stripe_charge_id = charge.id
        attendee.payment_status = 'succeeded'
        
        # Generate ticket number if it is None
        if attendee.ticket_number is None:
            attendee.ticket_number = generate_unique_ticket_number()
        
        # Generate QR code for the ticket number
        qr_code = qrcode.make(attendee.ticket_number)
        
        # Save the QR code to an in-memory file
        qr_image_path = f'static/qr_codes/{attendee.ticket_number}.png'
        qr_code.save(qr_image_path)
        
        # Save the path to the attendee object
        attendee.qr_image_path = qr_image_path

    db.session.commit()  # Commit all updates after the loop

    # Send confirmation emails
    send_confirmation_email_to_attendee(attendees, billing_details)
    event = Event.query.get(attendees[0].event_id)
    organizer = User.query.get(event.user_id)
    if organizer:
        send_confirmation_email_to_organizer(organizer, attendees, billing_details, event)





from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime

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

    # Fetch attendees
    attendees = Attendee.query.filter_by(event_id=event_id).all()

    # Initialize ticket type data and total tickets sold
    ticket_types = event.ticket_types
    ticket_type_data = {}
    tickets_sold_total = 0  # Total tickets sold across all types

    if event.enforce_individual_ticket_limits:
        # When individual ticket type limits are enforced
        for ticket_type in ticket_types:
            tickets_sold_type = Attendee.query.filter_by(
                event_id=event.id,
                ticket_type_id=ticket_type.id,
                payment_status='succeeded'
            ).count()
            tickets_remaining_type = (ticket_type.quantity or 0) - tickets_sold_type
            tickets_sold_total += tickets_sold_type

            ticket_type_data[ticket_type.id] = {
                'name': ticket_type.name,
                'price': ticket_type.price,
                'quantity': ticket_type.quantity,
                'tickets_sold': tickets_sold_type,
                'tickets_remaining': tickets_remaining_type
            }
        total_quantity = sum(
            tt.quantity for tt in ticket_types if tt.quantity is not None
        )
        tickets_available = total_quantity - tickets_sold_total

    else:
        # When total event capacity is enforced
        for ticket_type in ticket_types:
            tickets_sold_type = Attendee.query.filter_by(
                event_id=event.id,
                ticket_type_id=ticket_type.id,
                payment_status='succeeded'
            ).count()
            tickets_sold_total += tickets_sold_type

            ticket_type_data[ticket_type.id] = {
                'name': ticket_type.name,
                'price': ticket_type.price,
                'quantity': "N/A",  # Indicate not applicable
                'tickets_sold': tickets_sold_type,
                'tickets_remaining': None  # Do not calculate remaining
            }
        total_quantity = event.ticket_quantity
        tickets_available = total_quantity - tickets_sold_total

    # Format the event date as dd-mm-yyyy
    event_date = datetime.strptime(event.date, '%Y-%m-%d').strftime('%d-%m-%Y')

    return render_template(
        'view_attendees.html',
        event=event,
        attendees=attendees,
        questions=all_questions,
        tickets_sold=tickets_sold_total,
        tickets_available=tickets_available,
        total_quantity=total_quantity,
        event_date=event_date,
        ticket_type_data=ticket_type_data  # Pass ticket type data to template
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

    # Ensure the user has permission to edit the event
    if event.user_id != current_user.id:
        flash("You don't have permission to edit this event.")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # Update basic event details
        event.name = request.form['name']
        event.date = request.form['date']
        event.start_time = request.form.get('start_time')
        event.end_time = request.form.get('end_time')
        event.location = request.form['location']
        event.description = request.form.get('description')

        # Update event image if a new one is uploaded
        image_file = request.files.get('event_image')
        if image_file and allowed_file(image_file.filename):
            image_url = upload_to_s3(image_file, 'events')
            if image_url:
                event.image_url = image_url
            else:
                flash("Error uploading the event image. Please try again.", "danger")

        # Determine if individual ticket limits are enforced
        enforce_limits = request.form.get('enforce_individual_ticket_limits') == 'on'
        event.enforce_individual_ticket_limits = enforce_limits

        # Process ticket types and limits
        if enforce_limits:
            # Handle existing ticket types with limits
            existing_ticket_types = TicketType.query.filter_by(event_id=event.id).all()
            for ticket_type in existing_ticket_types:
                delete_key = f'delete_{ticket_type.id}'
                if request.form.get(delete_key):
                    db.session.delete(ticket_type)
                else:
                    ticket_type.name = request.form.get(f'name_{ticket_type.id}')
                    ticket_type.price = float(request.form.get(f'price_{ticket_type.id}'))
                    ticket_type.quantity = int(request.form.get(f'quantity_{ticket_type.id}'))

            # Handle new ticket types with limits
            new_names = request.form.getlist('new_ticket_name')
            new_prices = request.form.getlist('new_ticket_price')
            new_quantities = request.form.getlist('new_ticket_quantity')
            
            for name, price, quantity in zip(new_names, new_prices, new_quantities):
                if name and price and quantity:
                    new_ticket = TicketType(
                        event_id=event.id,
                        name=name,
                        price=float(price),
                        quantity=int(quantity)
                    )
                    db.session.add(new_ticket)
                    
            event.ticket_quantity = None  # Clear total capacity when using individual limits

        else:
            # Handle existing ticket types without limits
            existing_ticket_types = TicketType.query.filter_by(event_id=event.id).all()
            for ticket_type in existing_ticket_types:
                delete_key = f'delete_no_limit_{ticket_type.id}'
                if request.form.get(delete_key):
                    db.session.delete(ticket_type)
                else:
                    ticket_type.name = request.form.get(f'name_no_limit_{ticket_type.id}')
                    ticket_type.price = float(request.form.get(f'price_no_limit_{ticket_type.id}'))
                    ticket_type.quantity = None

            # Handle new ticket types without limits
            new_names = request.form.getlist('new_ticket_name_no_limit')
            new_prices = request.form.getlist('new_ticket_price_no_limit')
            
            for name, price in zip(new_names, new_prices):
                if name and price:
                    new_ticket = TicketType(
                        event_id=event.id,
                        name=name,
                        price=float(price),
                        quantity=None
                    )
                    db.session.add(new_ticket)
            
            # Update total event capacity
            event.ticket_quantity = int(request.form.get('total_ticket_quantity'))

        # Update custom questions conditionally
        for i in range(1, 11):
            question_key = f'custom_question_{i}'
            question_value = request.form.get(question_key)
            setattr(event, question_key, question_value if question_value else None)

        # Commit all changes
        try:
            db.session.commit()
            flash('Event updated successfully!')
            print("Event updated in database with image URL:", event.image_url)  # Debugging
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating the event. Please try again.')
            print(f"Database commit error: {e}")  # Debugging

    # Prepare custom questions with empty strings as default values if None
    custom_questions = {
        f'custom_question_{i}': getattr(event, f'custom_question_{i}', '') or ''
        for i in range(1, 11)
    }

    # Separate ticket types based on enforcement
    ticket_types_with_limits = []
    ticket_types_no_limits = []
    for ticket_type in event.ticket_types:
        if event.enforce_individual_ticket_limits and ticket_type.quantity is not None:
            ticket_types_with_limits.append(ticket_type)
        elif not event.enforce_individual_ticket_limits:
            ticket_types_no_limits.append(ticket_type)

    return render_template(
        'edit_event.html',
        event=event,
        custom_questions=custom_questions,
        ticket_types_with_limits=ticket_types_with_limits,
        ticket_types_no_limits=ticket_types_no_limits
    )

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
    
    if event.user_id != current_user.id:
        flash("You don't have permission to add attendees to this event.")
        return redirect(url_for('dashboard'))

    # Get ticket types for the event
    ticket_types = TicketType.query.filter_by(event_id=event_id).all()
    
    # Get questions
    user = User.query.get(event.user_id)
    default_questions = DefaultQuestion.query.filter_by(user_id=user.id).all()
    default_question_texts = [dq.question for dq in default_questions]
    
    custom_questions = []
    for i in range(1, 11):
        question = getattr(event, f'custom_question_{i}')
        if question:
            custom_questions.append(question)
    
    all_questions = default_question_texts + custom_questions

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        ticket_type_id = request.form.get('ticket_type')
        number_of_tickets = int(request.form.get('number_of_tickets', 1))

        # Collect answers for each ticket
        ticket_answers = []
        for ticket_num in range(1, number_of_tickets + 1):
            answers = {}
            for q_index, question in enumerate(all_questions, 1):
                answer = request.form.get(f'ticket_{ticket_num}_question_{q_index}')
                if not answer:
                    flash(f'Please answer all questions for Ticket #{ticket_num}')
                    return redirect(url_for('add_attendee', event_id=event_id))
                answers[question] = answer
            ticket_answers.append(answers)

        # Create attendee record
        ticket_type = TicketType.query.get(ticket_type_id)
        ticket_number = generate_unique_ticket_number()

        attendee = Attendee(
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            full_name=full_name,
            email=email,
            phone_number=phone_number,
            tickets_purchased=number_of_tickets,
            ticket_price_at_purchase=ticket_type.price,
            payment_status='succeeded',
            session_id='MANUAL_ENTRY',
            ticket_answers=json.dumps(ticket_answers),
            ticket_number=ticket_number,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(attendee)
        db.session.commit()

        flash(f"Attendee added successfully with ticket number: {ticket_number}")
        return redirect(url_for('view_attendees', event_id=event_id))

    return render_template('add_attendee.html', 
                         event=event, 
                         questions=all_questions,
                         ticket_types=ticket_types)


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
        if isinstance(value, str):
            # If it's a string, parse it first
            return datetime.strptime(value, '%Y-%m-%d').strftime('%d-%m-%Y')
        else:
            # If it's already a datetime object, just format it
            return value.strftime('%d-%m-%Y')
    return ""

from flask import render_template, request, redirect, url_for
import qrcode
import base64
from io import BytesIO

@app.route('/success')
def success():
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

    # Generate QR codes for each ticket
    qr_codes = []
    for attendee in attendees:
        qr_data = attendee.ticket_number  # Data for QR code (the unique ticket number)
        qr_img = qrcode.make(qr_data)

        # Convert the QR code image to base64 to embed in HTML
        buffer = BytesIO()
        qr_img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        qr_codes.append(qr_base64)  # Append each QR code to the list

    # Prepare data to pass to the template
    context = {
        'event': event,
        'organizer': organizer,
        'attendee': attendees[0],  # Assumes buyer's details are the same
        'total_tickets': total_tickets,
        'qr_codes': qr_codes  # Pass the list of QR codes as base64 strings
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
            <p>We're thrilled to have you on board! Since you've joined TicketRush, you're all set to start creating memorable events with our simple and secure ticketing platform.</p>
            <p><strong>Access Your Dashboard:</strong> <a href="https://bookings.ticketrush.io/manage_default_questions" style="color: #ff0000;" target="_blank">Login Here</a></p>
            <p>To help you get started, take a look at our <a href="https://www.ticketrush.io/support" style="color: #ff0000;" target="_blank">Tutorials Page</a>. It's full of tips to make the most out of your TicketRush experience.</p>
            <p>We can't wait to see the incredible events you create!</p>
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


def generate_unique_ticket_number():
    characters = string.ascii_uppercase + string.digits
    while True:
        ticket_number = ''.join(random.choice(characters) for _ in range(20))
        existing_ticket = Attendee.query.filter_by(ticket_number=ticket_number).first()
        if not existing_ticket:
            return ticket_number



@app.route('/resend_ticket/<int:attendee_id>', methods=['POST'])
@login_required
def resend_ticket(attendee_id):
    attendee = Attendee.query.get_or_404(attendee_id)
    event = Event.query.get(attendee.event_id)

    # Ensure the user has permission to resend tickets
    if event.user_id != current_user.id:
        flash("You don't have permission to resend tickets for this attendee.")
        return redirect(url_for('dashboard'))

    # Fetch organizer and billing details
    organizer = User.query.get(event.user_id)
    billing_details = json.loads(attendee.billing_details) if attendee.billing_details else {}

    # Resend the confirmation email
    send_confirmation_email_to_attendee([attendee], billing_details)

    flash(f"Ticket has been resent to {attendee.email}.")
    return redirect(url_for('view_attendees', event_id=event.id))



def upload_to_s3(file, folder_prefix="event-logos"):
    unique_suffix = uuid.uuid4().hex
    filename = f"{unique_suffix}_{secure_filename(file.filename)}"
    s3_filename = f"{folder_prefix}/{filename}"

    try:
        # Remove the "ACL" parameter
        s3.upload_fileobj(
            file,
            S3_BUCKET_NAME,
            s3_filename,
            ExtraArgs={"ContentType": file.content_type}  # Only specify ContentType
        )
        return f"https://{S3_BUCKET_NAME}.s3.{os.getenv('AWS_REGION')}.amazonaws.com/{s3_filename}"
    except NoCredentialsError:
        print("S3 credentials not available")
        return None

@app.route('/event/<int:event_id>/scanner')
@login_required
def start_event_scanner(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Check if user owns this event
    if event.user_id != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard'))
    
    # Get all attendees for this event
    attendees = Attendee.query.filter_by(
        event_id=event_id,
        payment_status='succeeded'
    ).all()
    
    # Calculate statistics
    total_attendees = len(attendees)
    checked_in = sum(1 for a in attendees if getattr(a, 'checked_in', False))
    
    # Get ticket types if using individual limits
    if event.enforce_individual_ticket_limits:
        event.ticket_types = TicketType.query.filter_by(event_id=event_id).all()
    
    return render_template('event_scanner.html',
                             event=event,
                             total_attendees=total_attendees,
                             checked_in=checked_in)

@app.route('/api/check-in/<int:event_id>', methods=['POST'])
@login_required
def check_in_attendee(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Check if user owns this event
    if event.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    ticket_number = request.json.get('ticket_number')
    if not ticket_number:
        return jsonify({'error': 'No ticket number provided'}), 400
        
    attendee = Attendee.query.filter_by(
        event_id=event_id,
        ticket_number=ticket_number,
        payment_status='succeeded'
    ).first()
    
    if not attendee:
        return jsonify({
            'status': 'error',
            'message': 'Invalid ticket'
        }), 404
        
    if getattr(attendee, 'checked_in', False):
        return jsonify({
            'status': 'warning',
            'message': 'Already checked in',
            'attendee': {
                'name': attendee.full_name,
                'check_in_time': attendee.check_in_time.strftime('%H:%M:%S'),
                'ticket_type': attendee.ticket_type.name
            }
        })
    
    # Update check-in status
    attendee.checked_in = True
    attendee.check_in_time = datetime.now()
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Check-in successful',
        'attendee': {
            'name': attendee.full_name,
            'ticket_type': attendee.ticket_type.name
        },
        'stats': {
            'total_checked_in': Attendee.query.filter_by(
                event_id=event_id,
                checked_in=True
            ).count(),
            'total_attendees': Attendee.query.filter_by(
                event_id=event_id,
                payment_status='succeeded'
            ).count()
        }
    })



if __name__ == "__main__":
    app.run(debug=True)

