

import numpy as np
from flask import Flask, request, render_template, redirect, url_for, session, jsonify, send_file
import pickle
from config import MONGO_URI, SECRET_KEY
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from bson import ObjectId
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)

# Load model
try:
    model = pickle.load(open("model.pkl", "rb"))
    print("✓ Model loaded successfully")
except:
    print("✗ Error loading model")
    model = None

# MongoDB setup
app.config["MONGO_URI"] = MONGO_URI
app.secret_key = SECRET_KEY
mongo = PyMongo(app)
db = mongo.db

# ============ HELPER FUNCTIONS ============
def get_user_predictions(user_id):
    """Get all predictions for a user"""
    predictions = list(db.predictions.find({"user_id": user_id}).sort("prediction_date", -1))
    for pred in predictions:
        pred['_id'] = str(pred['_id'])
    return predictions

def save_prediction(user_id, user_name, form_data, crop_prediction):
    """Save prediction to database"""
    prediction_data = {
        "user_id": user_id,
        "user_name": user_name,
        **form_data,
        "predicted_crop": crop_prediction,
        "prediction_date": datetime.now(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    db.predictions.insert_one(prediction_data)
    return prediction_data

def create_simple_pdf(prediction, prediction_id):
    """Create a simple PDF report for single prediction"""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Title
    p.setFont("Helvetica-Bold", 20)
    p.drawString(50, height - 50, "Crop Prediction Report")
    
    # User info
    p.setFont("Helvetica", 12)
    p.drawString(50, height - 80, f"User: {prediction['user_name']}")
    p.drawString(50, height - 100, f"Date: {prediction['timestamp']}")
    p.drawString(50, height - 120, f"Prediction ID: {prediction_id}")
    
    # Parameters
    y = height - 160
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Soil Parameters:")
    
    p.setFont("Helvetica", 12)
    params = [
        ("Nitrogen (N)", f"{prediction['nitrogen']} ppm"),
        ("Phosphorus (P)", f"{prediction['phosphorus']} ppm"),
        ("Potassium (K)", f"{prediction['potassium']} ppm"),
        ("Temperature", f"{prediction['temperature']} °C"),
        ("Humidity", f"{prediction['humidity']} %"),
        ("pH Level", f"{prediction['ph']}"),
        ("Rainfall", f"{prediction['rainfall']} mm")
    ]
    
    for param_name, param_value in params:
        y -= 20
        p.drawString(70, y, f"{param_name}: {param_value}")
    
    # Prediction Result
    y -= 40
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, f"Predicted Crop: {prediction['predicted_crop']}")
    
    # Footer
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(50, 50, "This prediction is based on machine learning analysis.")
    p.drawString(50, 35, "For best agricultural practices, consult with local agricultural experts.")
    
    p.save()
    buffer.seek(0)
    return buffer

def create_all_predictions_pdf(predictions, user_name):
    """Create PDF with all predictions"""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Title
    p.setFont("Helvetica-Bold", 24)
    p.drawCentredString(width/2, height - 50, "All Crop Predictions Report")
    
    # User info
    p.setFont("Helvetica", 14)
    p.drawString(50, height - 90, f"User: {user_name}")
    p.drawString(50, height - 110, f"Total Predictions: {len(predictions)}")
    p.drawString(50, height - 130, f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Start Y position for table
    y = height - 180
    
    # Table headers
    headers = ["Date", "N", "P", "K", "Temp", "Humidity", "pH", "Rainfall", "Crop"]
    col_widths = [80, 40, 40, 40, 50, 60, 40, 60, 80]
    
    # Draw headers
    p.setFont("Helvetica-Bold", 10)
    x = 30
    for i, header in enumerate(headers):
        p.drawString(x, y, header)
        x += col_widths[i]
    
    y -= 20
    
    # Draw horizontal line
    p.line(30, y, sum(col_widths) + 30, y)
    y -= 10
    
    # Draw predictions
    p.setFont("Helvetica", 9)
    for pred in predictions:
        if y < 50:  # New page if running out of space
            p.showPage()
            p.setFont("Helvetica", 9)
            y = height - 50
        
        x = 30
        row_data = [
            pred['timestamp'][:16],  # Date (first 16 chars)
            str(pred['nitrogen']),
            str(pred['phosphorus']),
            str(pred['potassium']),
            str(pred['temperature']),
            str(pred['humidity']),
            str(pred['ph']),
            str(pred['rainfall']),
            pred['predicted_crop']
        ]
        
        for i, data in enumerate(row_data):
            p.drawString(x, y, data)
            x += col_widths[i]
        
        y -= 15
    
    # Summary
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Summary:")
    
    y -= 20
    p.setFont("Helvetica", 11)
    
    # Count unique crops
    unique_crops = {}
    for pred in predictions:
        crop = pred['predicted_crop']
        unique_crops[crop] = unique_crops.get(crop, 0) + 1
    
    # Display crop frequency
    for crop, count in unique_crops.items():
        p.drawString(70, y, f"{crop}: {count} time(s)")
        y -= 15
    
    # Footer
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(50, 50, "Report generated by Crop Prediction System")
    p.drawString(50, 35, f"Total records: {len(predictions)}")
    
    p.save()
    buffer.seek(0)
    return buffer

# ============ ROUTES ============
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/form")
def form():
    return render_template("index.html")

@app.route("/how-it-works")
def how_it_works():
    return render_template("work.html")

@app.route("/register", methods=["GET", "POST"])
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

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        user = db.users.find_one({"email": email})
        if user and check_password_hash(user["password"], password):
            session["user_id"] = str(user["_id"])
            session["name"] = user["name"]
            return redirect(url_for("dashboard"))
        return "Invalid email or password!"
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/predict", methods=["POST"])
def predict():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    # Get form data
    form_data = {
        "nitrogen": float(request.form['Nitrogen']),
        "phosphorus": float(request.form['Phosporash']),
        "potassium": float(request.form['potassium']),
        "temperature": float(request.form['temperature']),
        "humidity": float(request.form['humidity']),
        "ph": float(request.form['ph']),
        "rainfall": float(request.form['rainfall'])
    }
    
    # Make prediction
    feature = np.array([[form_data["nitrogen"], form_data["phosphorus"], form_data["potassium"], 
                        form_data["temperature"], form_data["humidity"], form_data["ph"], 
                        form_data["rainfall"]]])
    predicted_crop = model.predict(feature)[0]
    
    # Save to database
    save_prediction(session["user_id"], session["name"], form_data, predicted_crop)
    
    return render_template("index.html", prediction_txt=f"The predicted crop is {predicted_crop}")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    predictions = get_user_predictions(session["user_id"])
    return render_template("dashboard.html", 
                         name=session["name"], 
                         predictions=predictions,
                         total_predictions=len(predictions))

@app.route("/delete_prediction/<prediction_id>", methods=["POST"])
def delete_prediction(prediction_id):
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"})
    
    result = db.predictions.delete_one({"_id": ObjectId(prediction_id), "user_id": session["user_id"]})
    if result.deleted_count > 0:
        return jsonify({"success": True, "message": "Prediction deleted"})
    return jsonify({"success": False, "message": "Prediction not found"})

@app.route("/download_prediction_pdf/<prediction_id>")
def download_prediction_pdf(prediction_id):
    """Download single prediction as PDF"""
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    prediction = db.predictions.find_one({"_id": ObjectId(prediction_id), "user_id": session["user_id"]})
    if not prediction:
        return "Prediction not found", 404
    
    pdf_buffer = create_simple_pdf(prediction, prediction_id)
    return send_file(pdf_buffer, 
                    as_attachment=True, 
                    download_name=f"crop_prediction_{prediction_id}.pdf",
                    mimetype='application/pdf')

@app.route("/download_all_predictions_pdf")
def download_all_predictions_pdf():
    """Download all predictions as a single PDF"""
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    predictions = get_user_predictions(session["user_id"])
    
    if not predictions:
        return "No predictions found", 404
    
    pdf_buffer = create_all_predictions_pdf(predictions, session["name"])
    filename = f"all_predictions_{session['name']}_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    return send_file(pdf_buffer,
                    as_attachment=True,
                    download_name=filename,
                    mimetype='application/pdf')

@app.route("/testdb")
def testdb():
    try:
        result = db.users.find_one()
        return str(result)
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    print("=" * 50)
    print(" Crop Prediction App Starting...")
    print("=" * 50)
    app.run(debug=True, port=5000)
