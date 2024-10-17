from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # You should change this to something secure
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, id):
        self.id = id

# Create a single admin user (for simplicity)
users = {'admin': {'password': 'password123'}}

@login_manager.user_loader
def load_user(user_id):
    if user_id == 'admin':
        return User(id=user_id)
    return None

@app.route('/')
def home():
    return "Hello, World!"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            user = User(id=username)
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return "Welcome to the dashboard!"

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# Add this below your login routes
events = []

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', events=events)

# Route to create a new event
@app.route('/create_event', methods=['GET', 'POST'])
@login_required
def create_event():
    if request.method == 'POST':
        event_name = request.form['event_name']
        event_date = request.form['event_date']
        events.append({'name': event_name, 'date': event_date})
        flash('Event created successfully!')
        return redirect(url_for('dashboard'))
    return render_template('create_event.html')

if __name__ == "__main__":
    app.run(debug=True)
