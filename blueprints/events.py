from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app import db, User, Event, Attendee, DefaultQuestion  # Import models directly from app.py
import random
import string
from datetime import datetime
import json  # Import json to handle JSON operations

# Create a blueprint for events
events_blueprint = Blueprint('events', __name__)

# Helper function to generate a random unique ID with 15 characters
def generate_unique_id():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(15))

# Dashboard route
@events_blueprint.route('/dashboard')
@login_required
def dashboard():
    filter_value = request.args.get('filter', 'all')

    # Fetch events for the logged-in user
    user_events = Event.query.filter_by(user_id=current_user.id).all()

    # Convert string dates to datetime for comparison
    def str_to_date(date_str):
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')  # Adjust date format if needed
        except ValueError:
            return None

    # Filter events based on 'upcoming' or 'past'
    if filter_value == 'upcoming':
        user_events = [event for event in user_events if str_to_date(event.date) and str_to_date(event.date) >= datetime.now()]
    elif filter_value == 'past':
        user_events = [event for event in user_events if str_to_date(event.date) and str_to_date(event.date) < datetime.now()]

    total_tickets_sold = 0
    total_revenue = 0

    event_data = []
    for event in user_events:
        attendees = Attendee.query.filter_by(event_id=event.id).all()
        tickets_sold = sum([attendee.tickets_purchased for attendee in attendees])
        tickets_remaining = event.ticket_quantity - tickets_sold
        
        # Calculate revenue based on ticket price at purchase
        event_revenue = sum([attendee.tickets_purchased * attendee.ticket_price_at_purchase for attendee in attendees])

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

# Create Event route
@events_blueprint.route('/create_event', methods=['GET', 'POST'])
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
        return redirect(url_for('events.dashboard'))

    default_questions = DefaultQuestion.query.filter_by(user_id=current_user.id).all()
    return render_template('create_event.html', default_questions=default_questions)

# Edit Event route
@events_blueprint.route('/edit_event/<int:event_id>', methods=['GET', 'POST'])
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
        return redirect(url_for('events.dashboard'))

    return render_template('edit_event.html', event=event)

# Delete Event route
@events_blueprint.route('/delete_event/<int:event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash('Event deleted successfully!')
    return redirect(url_for('events.dashboard'))

# View Attendees route
@events_blueprint.route('/view_attendees/<int:event_id>')
@login_required
def view_attendees(event_id):
    event = Event.query.get(event_id)
    if not event or event.user_id != current_user.id:
        flash("Event not found or you don't have permission to view it.")
        return redirect(url_for('events.dashboard'))

    attendees = Attendee.query.filter_by(event_id=event_id).all()

    # Parse the JSON fields for each attendee
    for attendee in attendees:
        if attendee.ticket_answers:
            attendee.ticket_answers = json.loads(attendee.ticket_answers)  # Parse JSON string to dictionary
        else:
            attendee.ticket_answers = {}

        if attendee.billing_details:
            attendee.billing_details = json.loads(attendee.billing_details)  # Parse JSON string to dictionary
        else:
            attendee.billing_details = {}

    return render_template('view_attendees.html', event=event, attendees=attendees)

# Embed Events route
@events_blueprint.route('/embed/<unique_id>')
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
            <button onclick="window.location.href='/purchase/{event.id}'">Buy Ticket</button>
        </li><br>
        '''
    events_html += '</ul>'

    response = f"document.write(`{events_html}`);"
    return response, 200, {'Content-Type': 'application/javascript'}
