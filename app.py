from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'
login_manager = LoginManager()
login_manager.init_app(app)

# Store users and events in memory (for now)
users = {}
events_by_user = {}

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(id=user_id)
    return None

@app.route('/')
def home():
    return "Hello, World!"

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users:
            flash('Username already exists!')
        else:
            hashed_password = generate_password_hash(password)
            users[username] = {'password': hashed_password}
            events_by_user[username] = []  # Each user gets their own event list
            flash('Registration successful! You can now log in.')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and check_password_hash(users[username]['password'], password):
            user = User(id=username)
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user_events = events_by_user.get(current_user.id, [])
    return render_template('dashboard.html', events=user_events)

@app.route('/create_event', methods=['GET', 'POST'])
@login_required
def create_event():
    if request.method == 'POST':
        event_name = request.form['event_name']
        event_date = request.form['event_date']
        events_by_user[current_user.id].append({'name': event_name, 'date': event_date})
        flash('Event created successfully!')
        return redirect(url_for('dashboard'))
    return render_template('create_event.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)
