from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import math
import requests
from werkzeug.utils import secure_filename
import os
from flask_dance.contrib.google import make_google_blueprint, google
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError
from wtforms import Form, StringField, PasswordField, BooleanField, validators
from wtforms.validators import DataRequired, Email, Length, EqualTo

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///travel.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Google OAuth Configuration
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # For development only
google_bp = make_google_blueprint(
    client_id="YOUR_GOOGLE_CLIENT_ID",
    client_secret="YOUR_GOOGLE_CLIENT_SECRET",
    scope=["profile", "email"]
)
app.register_blueprint(google_bp, url_prefix="/login")

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    experiences = db.relationship('Experience', backref='author', lazy=True)

class Experience(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    date_visited = db.Column(db.Date, nullable=False)
    budget_category = db.Column(db.String(20))
    duration = db.Column(db.String(50))
    best_season = db.Column(db.String(50))
    external_links = db.Column(db.Text)
    tips = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    photos = db.relationship('ExperiencePhoto', backref='experience', lazy=True)
    ratings = db.relationship('ExperienceRating', backref='experience', lazy=True)

class ExperiencePhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    experience_id = db.Column(db.Integer, db.ForeignKey('experience.id'), nullable=False)
    photo_url = db.Column(db.String(200), nullable=False)
    caption = db.Column(db.String(200))
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ExperienceRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    experience_id = db.Column(db.Integer, db.ForeignKey('experience.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    rating = db.Column(db.Integer, nullable=False)

class SavedExperience(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    experience_id = db.Column(db.Integer, db.ForeignKey('experience.id'), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

class RegistrationForm(Form):
    username = StringField('Username', [
        validators.Length(min=3, message='Username must be at least 3 characters long'),
        validators.DataRequired(message='Username is required')
    ])
    email = StringField('Email', [
        validators.Email(message='Please enter a valid email address'),
        validators.DataRequired(message='Email is required')
    ])
    password = PasswordField('Password', [
        validators.Length(min=8, message='Password must be at least 8 characters long'),
        validators.DataRequired(message='Password is required')
    ])
    terms = BooleanField('Terms', [
        validators.DataRequired(message='You must accept the terms and conditions')
    ])
    location = StringField('Location')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_location():
    try:
        ip_response = requests.get('https://api.ipify.org?format=json')
        ip = ip_response.json()['ip']
        location_response = requests.get(f'https://ipapi.co/{ip}/json/')
        location_data = location_response.json()
        return {
            'city': location_data.get('city'),
            'latitude': location_data.get('latitude'),
            'longitude': location_data.get('longitude')
        }
    except:
        return None

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    try:
        user_location = None
        if current_user.is_authenticated and current_user.latitude and current_user.longitude:
            user_location = {
                'city': current_user.location,
                'latitude': current_user.latitude,
                'longitude': current_user.longitude
            }
        else:
            user_location = get_user_location()

        # Get popular experiences
        popular_experiences = Experience.query.order_by(
            Experience.views.desc(), 
            Experience.likes.desc()
        ).limit(6).all()
        
        # Get nearby experiences if location is available
        nearby_experiences = []
        if user_location and user_location.get('latitude') and user_location.get('longitude'):
            all_experiences = Experience.query.all()
            experiences_with_distance = []
            for exp in all_experiences:
                if exp.latitude and exp.longitude:
                    distance = calculate_distance(
                        user_location['latitude'], user_location['longitude'],
                        exp.latitude, exp.longitude
                    )
                    experiences_with_distance.append((exp, distance))
            
            experiences_with_distance.sort(key=lambda x: x[1])
            nearby_experiences = [exp for exp, _ in experiences_with_distance[:6]]

        return render_template('index.html',
                            popular_experiences=popular_experiences,
                            nearby_experiences=nearby_experiences,
                            user_location=user_location)
    except Exception as e:
        print(f"Error in index route: {str(e)}")
        return render_template('index.html',
                            popular_experiences=[],
                            nearby_experiences=[],
                            user_location=None)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    city = request.args.get('city', '')
    country = request.args.get('country', '')
    budget = request.args.get('budget', '')
    season = request.args.get('season', '')
    rating_min = request.args.get('rating_min', '')

    experiences = Experience.query
    
    if query:
        experiences = experiences.filter(
            (Experience.title.contains(query)) |
            (Experience.description.contains(query)) |
            (Experience.location.contains(query))
        )
    
    if city:
        experiences = experiences.filter(Experience.city.contains(city))
    if country:
        experiences = experiences.filter(Experience.country.contains(country))
    if budget:
        experiences = experiences.filter(Experience.budget_category == budget)
    if season:
        experiences = experiences.filter(Experience.best_season == season)

    experiences = experiences.all()

    if rating_min:
        rating_min = float(rating_min)
        experiences = [exp for exp in experiences if exp.average_rating >= rating_min]

    return render_template('search.html',
                         experiences=experiences,
                         query=query,
                         city=city,
                         country=country,
                         budget=budget,
                         season=season,
                         rating_min=rating_min)

@app.route('/experience/add', methods=['GET', 'POST'])
@login_required
def add_experience():
    if request.method == 'POST':
        # Get location coordinates
        location = request.form['location']
        try:
            geocoding_response = requests.get(
                f'https://nominatim.openstreetmap.org/search',
                params={'q': location, 'format': 'json', 'limit': 1}
            )
            location_data = geocoding_response.json()[0]
            latitude = float(location_data['lat'])
            longitude = float(location_data['lon'])
        except:
            latitude = None
            longitude = None

        experience = Experience(
            title=request.form['title'],
            description=request.form['description'],
            location=location,
            city=request.form['city'],
            country=request.form['country'],
            latitude=latitude,
            longitude=longitude,
            date_visited=datetime.strptime(request.form['date_visited'], '%Y-%m-%d'),
            budget_category=request.form['budget_category'],
            duration=request.form['duration'],
            best_season=request.form['best_season'],
            external_links=request.form['external_links'],
            tips=request.form['tips'],
            user_id=current_user.id
        )
        db.session.add(experience)
        db.session.flush()

        # Handle photos
        photos = request.files.getlist('photos')
        for i, photo in enumerate(photos):
            if photo and allowed_file(photo.filename):
                filename = secure_filename(photo.filename)
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                photo.save(photo_path)
                
                photo_db = ExperiencePhoto(
                    experience_id=experience.id,
                    photo_url=filename,
                    caption=request.form.get(f'caption_{i}', ''),
                    is_primary=(i == 0)
                )
                db.session.add(photo_db)

        # Handle ratings
        rating_categories = ['overall', 'safety', 'value', 'facilities', 'accessibility']
        for category in rating_categories:
            rating_value = request.form.get(f'rating_{category}')
            if rating_value:
                rating = ExperienceRating(
                    experience_id=experience.id,
                    category=category,
                    rating=int(rating_value)
                )
                db.session.add(rating)

        db.session.commit()
        flash('Experience added successfully!', 'success')
        return redirect(url_for('experience'))

    return render_template('add_experience.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form if request.method == 'POST' else None)
    if request.method == 'POST' and form.validate():
        hashed_password = generate_password_hash(form.password.data)
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password,
            location=form.location.data
        )
        try:
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('Registration successful!', 'success')
            return redirect(url_for('index'))
        except IntegrityError:
            db.session.rollback()
            flash('Username or email already exists.', 'error')
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/experience/<int:id>/like', methods=['POST'])
@login_required
def like_experience(id):
    experience = Experience.query.get_or_404(id)
    experience.likes += 1
    db.session.commit()
    return jsonify({'likes': experience.likes})

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/my-experiences')
@login_required
def my_experiences():
    experiences = Experience.query.filter_by(user_id=current_user.id).order_by(Experience.created_at.desc()).all()
    return render_template('my_experiences.html', experiences=experiences)

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html', user=current_user)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route("/login/google")
def google_login():
    if not google.authorized:
        return redirect(url_for("google.login"))
    
    try:
        resp = google.get("/oauth2/v2/userinfo")
        assert resp.ok, resp.text
        email = resp.json()["email"]
        
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        if not user:
            # Create new user
            username = email.split('@')[0]
            password = generate_password_hash(os.urandom(24).hex())
            user = User(username=username, email=email, password=password)
            db.session.add(user)
            db.session.commit()
        
        login_user(user)
        flash('Successfully signed in with Google!', 'success')
        return redirect(url_for('index'))
        
    except TokenExpiredError:
        return redirect(url_for("google.login"))

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

if __name__ == '__main__':
    with app.app_context():
        db.drop_all()  # Drop all existing tables
        db.create_all()  # Create new tables with updated schema
    app.run(debug=True)
