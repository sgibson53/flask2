from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from forms import SignupForm, LoginForm, AddressForm
from flask_heroku import Heroku
from werkzeug import generate_password_hash, check_password_hash
import geocoder
import urllib.request
import json


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost/learningflask'
# heroku = Heroku(app)
db = SQLAlchemy(app)
db.init_app(app)

# from models import User, Place

class User(db.Model):
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True}
    uid = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(100))
    lastname = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    pwdhash = db.Column(db.String(54))

    def __init__(self, firstname, lastname, email, password):
        self.firstname = firstname.title()
        self.lastname = lastname.title()
        self.email = email.lower()
        self.set_password(password)

    def set_password(self, password):
        self.pwdhash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.pwdhash, password)

class Place(object):
    def meters_to_walking_time(self, meters):
        # 80 meters is one minute of walking time
        return int(meters / 80)

    def wiki_path(self, slug):
        return urllib2.urlparse.urljoin("http://en.wikipedia.org/wiki/", slug.replace(' ', '_'))

    def address_to_latlng(self, address):
        g = geocoder.google(address)
        return (g.lat, g.lng)

    def query(self, address):
        lat, lng = self.address_to_latlng(address)

        query_url = "https://en.wikipedia.org/w/api.php?action=query&list=geosearch&gsradius=5000&gscoord={0}%7C{1}&gslimit=20&format=json".format(lat, lng)
        g = urllib2.urlopen(query_url)
        results = g.read()
        g.close()

        data = json.loads(results)
        
        places = []
        for place in data['query']['geosearch']:
            name = place['title']
            meters = place['dist']
            lat = place['lat']
            lng = place['lon']

            wiki_url = self.wiki_path(name)
            walking_time = self.meters_to_walking_time(meters)

            d = {
                'name': name,
                'url': wiki_url,
                'time': walking_time,
                'lat': lat,
                'lng': lng
            }

            places.append(d)

        return places

app.secret_key = "development-key"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    form = SignupForm()

    if 'email' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        if form.validate() == False:
            return render_template('signup.html', form=form)
        else:
            newuser = User(form.first_name.data, form.last_name.data, form.email.data, form.password.data)
            db.session.add(newuser)
            db.session.commit()

            session['email'] = newuser.email
            return redirect(url_for('home'))
            return "Success!"
    elif request.method == 'GET':
        return render_template('signup.html', form=form)

@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'email' not in session:
        return redirect(url_for('login'))

    form = AddressForm()

    places = []
    my_coordinates = (37.4221, -122.0844)

    if request.method == 'POST':
        if form.validate() == False:
            return render_template('home.html', form=form)
        else:
            # get the address
            address = form.address.data

            # query for places around it
            p = Place()
            my_coordinates = p.address_to_latlng(address)
            places = p.query(address)

            # return those results
            return render_template('home.html', form=form, my_coordinates=my_coordinates, places=places)
    elif request.method == 'GET':
        return render_template("home.html", form=form, my_coordinates=my_coordinates, places=places)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if 'email' in session:
        return redirect(url_for('home'))

    if request.method == "POST":
        if form.validate() == False:
            return render_template('login.html', form=form)
        else:
            email = form.email.data
            password = form.password.data

            user = User.query.filter_by(email=email).first()
            if user is not None and user.check_password(password):
                session['email'] = form.email.data
                return redirect(url_for('home'))
            else:
                return redirect(url_for('login'))

    elif request.method == "GET":
        return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)