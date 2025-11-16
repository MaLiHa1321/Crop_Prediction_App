import numpy as np
from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import pickle
from config import MONGO_URI, SECRET_KEY
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash

flask_app = Flask(__name__)
model = pickle.load(open("model.pkl", "rb"))

flask_app.config["MONGO_URI"] = MONGO_URI
flask_app.secret_key = SECRET_KEY

print("MONGO URI =", MONGO_URI)

mongo = PyMongo(flask_app)
db = mongo.db

@flask_app.route("/testdb")
def testdb():
    try:
        result = db.users.find_one()
        return str(result)
    except Exception as e:
        return str(e)


@flask_app.route("/")
def home():
    return render_template("home.html")


@flask_app.route("/form")
def form_page():
    return render_template("index.html")

@flask_app.route("/how-it-works")
def how_it_works():
    return render_template("work.html")

@flask_app.route("/predict", methods=["POST"])
def predict():

    nitrogen = float(request.form['Nitrogen'])
    phosphorus = float(request.form['Phosporash'])
    potassium = float(request.form['potassium'])
    temperature = float(request.form['temperature'])
    humidity = float(request.form['humidity'])
    ph = float(request.form['ph'])
    rainfall = float(request.form['rainfall'])


    feature = np.array([[nitrogen, phosphorus, potassium, temperature, humidity, ph, rainfall]])
    prediction = model.predict(feature)


    return render_template("index.html", prediction_txt=f"The predicted crop is {prediction[0]}")



@flask_app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

     
        if db.users.find_one({"email": email}):
            return "Email already exists!"

        hashed_pass = generate_password_hash(password)
        db.users.insert_one({
            "name": name,
            "email": email,
            "password": hashed_pass
        })

        return redirect(url_for("login"))

    return render_template("register.html")


@flask_app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = db.users.find_one({"email": email})
        if user and check_password_hash(user["password"], password):
            session["user_id"] = str(user["_id"])
            session["name"] = user["name"]
            return redirect(url_for("dashboard"))
        else:
            return "Invalid email or password!"

    return render_template("login.html")


@flask_app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_predictions = list(db.predictions.find({"user_id": session['user_id']}))
    return render_template("dashboard.html", name=session["name"], predictions=user_predictions)


@flask_app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()  
    return redirect(url_for('home'))

if __name__=="__main__":
    flask_app.run(debug=True)
