import numpy as np
from flask import Flask, request, render_template
import pickle

flask_app = Flask(__name__)
model = pickle.load(open("model.pkl", "rb"))


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

if __name__=="__main__":
    flask_app.run(debug=True)
