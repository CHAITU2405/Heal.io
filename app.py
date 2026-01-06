from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from models import db, User, Vital, Anomaly, Alert, PatientDoctor
from datetime import datetime, timedelta
from functools import wraps
import os
import sys
import logging
import pandas as pd
import io
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('healio.log')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
# Use absolute path for database to avoid path issues
import os
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'healio.db')
os.makedirs(os.path.dirname(db_path), exist_ok=True)
# Convert Windows path to forward slashes for SQLite URI
db_path_uri = db_path.replace('\\', '/')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path_uri}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Pre-import model at startup to avoid blocking requests
print("[APP] Pre-importing healio_model at startup...", flush=True)
try:
    import healio_model
    print(f"[APP] Model module pre-imported successfully: {healio_model}", flush=True)
    logger.info("Model module pre-imported successfully")
except Exception as e:
    print(f"[APP] Warning: Could not pre-import model: {e}", flush=True)
    logger.warning(f"Could not pre-import model: {e}")

# Create tables
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print(f"Warning: Error creating tables: {e}")
        # Try to recreate all tables
        try:
            db.drop_all()
            db.create_all()
        except Exception as e2:
            print(f"Error recreating tables: {e2}")

# Error handler for API routes to return JSON
@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/') or request.path.endswith('-csv'):
        return jsonify({'status': 'error', 'message': 'Route not found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    if request.path.startswith('/api/') or request.path.endswith('-csv'):
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500
    return render_template('500.html'), 500

# Authentication decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def patient_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Check if this is an API request (JSON expected)
            if request.is_json or request.path.startswith('/api/') or request.path.endswith('-csv'):
                return jsonify({'status': 'error', 'message': 'Authentication required'}), 401
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or user.user_type != 'patient':
            # Check if this is an API request (JSON expected)
            if request.is_json or request.path.startswith('/api/') or request.path.endswith('-csv'):
                return jsonify({'status': 'error', 'message': 'Access denied. Patient account required.'}), 403
            flash('Access denied. Patient account required.', 'error')
            return redirect(url_for('patient_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def doctor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Check if this is an API request (JSON expected)
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'status': 'error', 'message': 'Authentication required'}), 401
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or user.user_type != 'doctor':
            # Check if this is an API request (JSON expected)
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'status': 'error', 'message': 'Access denied. Doctor account required.'}), 403
            flash('Access denied. Doctor account required.', 'error')
            return redirect(url_for('doctor_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ============ AUTHENTICATION ROUTES ============

@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user.user_type == 'patient':
            return redirect(url_for('patient_dashboard'))
        else:
            return redirect(url_for('doctor_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Please fill in all fields.', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_type'] = user.user_type
            flash('Login successful!', 'success')
            
            if user.user_type == 'patient':
                return redirect(url_for('patient_dashboard'))
            else:
                return redirect(url_for('doctor_dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        user_type = request.form.get('user_type')
        phone = request.form.get('phone')
        date_of_birth = request.form.get('date_of_birth')
        
        # Validation
        if not all([email, password, first_name, last_name, user_type]):
            flash('Please fill in all required fields.', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('register.html')
        
        # Create user
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            user_type=user_type,
            phone=phone
        )
        
        if date_of_birth:
            try:
                user.date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
            except:
                pass
        
        # Doctor-specific fields
        if user_type == 'doctor':
            user.license_number = request.form.get('license_number')
            user.specialization = request.form.get('specialization')
        
        # Patient-specific fields
        if user_type == 'patient':
            user.is_non_verbal = request.form.get('is_non_verbal') == 'on'
            user.emergency_contact_name = request.form.get('emergency_contact_name')
            user.emergency_contact_phone = request.form.get('emergency_contact_phone')
        
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

# ============ PATIENT ROUTES ============

@app.route('/patient/dashboard')
@patient_required
def patient_dashboard():
    user = User.query.get(session['user_id'])
    
    # Get latest vitals
    latest_vital = Vital.query.filter_by(patient_id=user.id).order_by(Vital.recorded_at.desc()).first()
    
    # Get recent vitals for chart (last 24 hours, actual data from CSV)
    recent_vitals_24h = Vital.query.filter_by(patient_id=user.id).order_by(Vital.recorded_at.desc()).limit(24).all()
    
    # Get recent anomalies (handle case where table might not exist)
    # Get ALL anomalies for this patient, ordered by most recent
    try:
        recent_anomalies = Anomaly.query.filter_by(patient_id=user.id).order_by(Anomaly.detected_at.desc()).all()
    except Exception:
        recent_anomalies = []
    
    # Get unassigned anomalies (pending verification)
    try:
        unassigned_anomalies = Anomaly.query.filter_by(
            patient_id=user.id,
            case_status='pending'
        ).order_by(Anomaly.detected_at.desc()).all()
    except Exception:
        unassigned_anomalies = []
    
    # Get unread alerts
    try:
        unread_alerts = Alert.query.filter_by(patient_id=user.id, is_read=False).order_by(Alert.created_at.desc()).limit(5).all()
    except Exception:
        unread_alerts = []
    
    # Calculate health score based on vitals and anomalies
    health_score = 100
    if latest_vital:
        # Basic health score calculation based on vital ranges
        if latest_vital.heart_rate:
            if latest_vital.heart_rate < 60 or latest_vital.heart_rate > 100:
                health_score -= 5
        if latest_vital.oxygen_saturation:
            if latest_vital.oxygen_saturation < 95:
                health_score -= 10
        if latest_vital.blood_pressure_systolic:
            if latest_vital.blood_pressure_systolic > 140 or latest_vital.blood_pressure_systolic < 90:
                health_score -= 5
    
    # Reduce health score based on anomalies
    if recent_anomalies:
        for anomaly in recent_anomalies:
            if anomaly.severity == 'critical':
                health_score -= 10
            elif anomaly.severity == 'high':
                health_score -= 5
            elif anomaly.severity == 'medium':
                health_score -= 2
    
    # Get vitals for consistency map (last 6 months, 1 per day for heatmap)
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    daily_vitals = Vital.query.filter(
        Vital.patient_id == user.id,
        Vital.recorded_at >= six_months_ago
    ).order_by(Vital.recorded_at.asc()).all()
    
    # Group by date and check for anomalies on each day
    from collections import defaultdict
    daily_anomaly_status = {}
    
    # Get anomalies grouped by date (use string keys for JSON serialization)
    anomalies_by_date = defaultdict(list)
    try:
        for anomaly in Anomaly.query.filter_by(patient_id=user.id).all():
            date_key = anomaly.detected_at.date().isoformat()  # Convert to string
            anomalies_by_date[date_key].append(anomaly)
    except Exception:
        pass  # If Anomaly table doesn't exist yet, just skip
    
    # Mark days with anomalies
    for date_key, anomalies in anomalies_by_date.items():
        if anomalies:  # Check if list is not empty
            max_severity = max([a.severity for a in anomalies], key=lambda x: ['low', 'medium', 'high', 'critical'].index(x))
            daily_anomaly_status[date_key] = {
                'has_anomaly': True,
                'severity': max_severity
            }
    
    # Prepare vitals data for charts (actual data from CSV)
    vitals_chart_data = []
    if recent_vitals_24h:
        # Reverse to get chronological order (oldest first)
        for vital in reversed(recent_vitals_24h):
            vitals_chart_data.append({
                'heart_rate': vital.heart_rate if vital.heart_rate else None,
                'oxygen_saturation': vital.oxygen_saturation if vital.oxygen_saturation else None,
                'timestamp': vital.recorded_at.strftime('%H:%M') if vital.recorded_at else None
            })
    
    return render_template('patient/dashboard.html', 
                         user=user, 
                         latest_vital=latest_vital,
                         recent_anomalies=recent_anomalies,
                         unassigned_anomalies=unassigned_anomalies,
                         unread_alerts=unread_alerts,
                         health_score=max(0, min(100, health_score)),
                         daily_anomaly_status=daily_anomaly_status,
                         vitals_chart_data=vitals_chart_data,
                         page='dashboard')

@app.route('/patient/anomalies')
@patient_required
def patient_anomalies():
    user = User.query.get(session['user_id'])
    
    # Get all anomalies with pagination
    try:
        anomalies = Anomaly.query.filter_by(patient_id=user.id).order_by(Anomaly.detected_at.desc()).all()
    except Exception:
        anomalies = []
    
    return render_template('patient/anomalies.html', 
                         user=user,
                         anomalies=anomalies,
                         page='anomalies')

@app.route('/patient/anomaly/<int:anomaly_id>/consult-doctor')
@patient_required
def consult_doctor(anomaly_id):
    user = User.query.get(session['user_id'])
    anomaly = Anomaly.query.get_or_404(anomaly_id)
    
    # Verify anomaly belongs to patient
    if anomaly.patient_id != user.id:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('patient_anomalies'))
    
    # Get all available doctors
    all_doctors = User.query.filter_by(user_type='doctor').all()
    
    return render_template('patient/consult_doctor.html',
                         user=user,
                         anomaly=anomaly,
                         doctors=all_doctors,
                         page='anomalies')

@app.route('/patient/anomaly/<int:anomaly_id>/assign-doctor/<int:doctor_id>', methods=['POST'])
@patient_required
def assign_anomaly_to_doctor(anomaly_id, doctor_id):
    user = User.query.get(session['user_id'])
    anomaly = Anomaly.query.get_or_404(anomaly_id)
    doctor = User.query.get_or_404(doctor_id)
    
    # Verify anomaly belongs to patient and doctor is valid
    if anomaly.patient_id != user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    
    if doctor.user_type != 'doctor':
        return jsonify({'status': 'error', 'message': 'Invalid doctor'}), 400
    
    # Assign anomaly to doctor
    anomaly.assigned_doctor_id = doctor_id
    anomaly.case_status = 'assigned'
    anomaly.assigned_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': f'Anomaly assigned to Dr. {doctor.first_name} {doctor.last_name}'})

@app.route('/patient/upload-vitals-csv', methods=['POST'])
@patient_required
def upload_vitals_csv():
    """Handle CSV upload for vitals data (3 days = 72 rows)"""
    import traceback
    
    # CRITICAL: Force output immediately
    sys.stdout.write("\n" + "=" * 80 + "\n")
    sys.stdout.write("[UPLOAD] ========== CSV UPLOAD ROUTE CALLED ==========\n")
    sys.stdout.write("=" * 80 + "\n")
    sys.stdout.flush()
    
    logger.info("=" * 80)
    logger.info("[UPLOAD] ========== CSV UPLOAD ROUTE CALLED ==========")
    logger.info("=" * 80)
    
    # Also write to a log file to ensure we capture it
    try:
        with open('upload_log.txt', 'a') as f:
            f.write(f"\n[{datetime.utcnow()}] CSV UPLOAD ROUTE CALLED\n")
            f.flush()
    except:
        pass
    
    try:
        user = User.query.get(session['user_id'])
        logger.info(f"[UPLOAD] User ID: {user.id if user else 'None'}")
        logger.info(f"[UPLOAD] Request method: {request.method}")
        logger.info(f"[UPLOAD] Request files: {list(request.files.keys())}")
        print(f"[UPLOAD] User ID: {user.id if user else 'None'}", flush=True)
        print(f"[UPLOAD] Request method: {request.method}", flush=True)
        print(f"[UPLOAD] Request files: {list(request.files.keys())}", flush=True)
        sys.stdout.flush()
        
        # Clear existing anomalies for this patient before processing new data
        try:
            Anomaly.query.filter_by(patient_id=user.id).delete()
            db.session.commit()
        except Exception as e:
            print(f"Warning: Could not clear anomalies: {e}")
            db.session.rollback()
        
        if 'csv_file' not in request.files:
            print("[UPLOAD ERROR] No file provided in request")
            return jsonify({'status': 'error', 'message': 'No file provided'}), 400
        
        file = request.files['csv_file']
        print(f"[UPLOAD] File received: {file.filename}")
        if file.filename == '':
            print("[UPLOAD ERROR] No file selected")
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            print("[UPLOAD ERROR] File is not a CSV")
            return jsonify({'status': 'error', 'message': 'File must be a CSV'}), 400
        
        # Read CSV file
        try:
            print("[UPLOAD] Reading CSV file...")
            file_content = file.stream.read()
            # Try UTF-8 first, fallback to latin-1 if needed
            try:
                decoded_content = file_content.decode("UTF-8")
            except UnicodeDecodeError:
                decoded_content = file_content.decode("latin-1")
            stream = io.StringIO(decoded_content, newline=None)
            df = pd.read_csv(stream)
            print(f"[UPLOAD] CSV read successfully. Shape: {df.shape}, Columns: {list(df.columns)}")
        except UnicodeDecodeError:
            return jsonify({'status': 'error', 'message': 'File encoding error. Please ensure the CSV file uses UTF-8 encoding'}), 400
        except pd.errors.EmptyDataError:
            return jsonify({'status': 'error', 'message': 'CSV file is empty or invalid'}), 400
        except pd.errors.ParserError as e:
            return jsonify({'status': 'error', 'message': f'Invalid CSV format: {str(e)}'}), 400
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'Error reading CSV file: {str(e)}'}), 400
        
        if df.empty:
            return jsonify({'status': 'error', 'message': 'CSV file is empty'}), 400
        
        # Normalize column names (handle various formats) - case-insensitive matching
        column_mapping = {
            'heart_rate': ['heart_rate', 'hr', 'heart rate', 'heartrate', 'pulse', 'bpm'],
            'blood_pressure_systolic': ['blood_pressure_systolic', 'sbp', 'systolic', 'systolic_bp', 'systolic bp', 'bp_systolic', 'bp systolic', 'blood_pressure_sys'],
            'blood_pressure_diastolic': ['blood_pressure_diastolic', 'dbp', 'diastolic', 'diastolic_bp', 'diastolic bp', 'bp_diastolic', 'bp diastolic', 'blood_pressure_dia'],
            'oxygen_saturation': ['oxygen_saturation', 'spo2', 'sp_o2', 'oxygen', 'oxygen sat', 'o2_sat', 'o2 sat', 'saturation'],
            'respiratory_rate': ['respiratory_rate', 'rr', 'respiratory rate', 'breathing_rate', 'breathing rate', 'respiration'],
            'body_temperature': ['body_temperature', 'temp', 'temperature', 'body temp', 'body_temp', 'fever'],
            'steps': ['steps', 'step_count', 'step count', 'walking_steps', 'walking steps'],
            'sleep_hours': ['sleep_hours', 'sleep', 'sleep hours', 'sleep_hours', 'sleep_time', 'sleep time', 'sleep_duration', 'sleep duration'],
            'energy_level': ['energy_level', 'energy', 'energy level', 'energy_lvl', 'vitality']
        }
        
        # Map columns - case-insensitive matching with normalization
        mapped_columns = {}
        df.columns = df.columns.str.strip()  # Remove whitespace from column names
        
        for standard_name, variants in column_mapping.items():
            for col in df.columns:
                col_normalized = col.strip().lower().replace(' ', '_').replace('-', '_')
                variants_normalized = [v.lower().replace(' ', '_').replace('-', '_') for v in variants]
                if col_normalized in variants_normalized or col.strip().lower() in [v.lower() for v in variants]:
                    mapped_columns[standard_name] = col
                    break
        
        print(f"[UPLOAD] CSV columns found: {list(df.columns)}")
        print(f"[UPLOAD] Column mapping result: {mapped_columns}")
        
        # Log which columns were NOT mapped
        unmapped_cols = [col for col in df.columns if col not in mapped_columns.values()]
        if unmapped_cols:
            print(f"[UPLOAD] WARNING: Unmapped columns found: {unmapped_cols}")
            logger.warning(f"Unmapped columns: {unmapped_cols}")
        
        # Create vitals records - use entire dataset
        now = datetime.utcnow()
        vitals_added = []
        total_rows = len(df)  # Process all rows from CSV
        
        for idx, row in df.iterrows():
            
            # Calculate timestamp - spread data over time (1 minute intervals)
            # Start from (total_rows-1) minutes ago and go forward
            minutes_ago = total_rows - 1 - idx
            recorded_time = now - timedelta(minutes=minutes_ago)
            
            # Extract values with fallbacks - ensure ALL columns are stored
            def safe_float(value):
                """Safely convert to float"""
                try:
                    if pd.notna(value) and value != '':
                        return float(value)
                except (ValueError, TypeError):
                    pass
                return None
            
            def safe_int(value):
                """Safely convert to int"""
                try:
                    if pd.notna(value) and value != '':
                        return int(float(value))
                except (ValueError, TypeError):
                    pass
                return None
            
            def safe_str(value):
                """Safely convert to string"""
                try:
                    if pd.notna(value) and value != '':
                        return str(value).strip()
                except (ValueError, TypeError):
                    pass
                return None
            
            # Extract all vital signs - ALL columns must be stored
            heart_rate = safe_float(row[mapped_columns['heart_rate']]) if 'heart_rate' in mapped_columns else None
            blood_pressure_systolic = safe_float(row[mapped_columns['blood_pressure_systolic']]) if 'blood_pressure_systolic' in mapped_columns else None
            blood_pressure_diastolic = safe_float(row[mapped_columns['blood_pressure_diastolic']]) if 'blood_pressure_diastolic' in mapped_columns else None
            oxygen_saturation = safe_float(row[mapped_columns['oxygen_saturation']]) if 'oxygen_saturation' in mapped_columns else None
            respiratory_rate = safe_float(row[mapped_columns['respiratory_rate']]) if 'respiratory_rate' in mapped_columns else None
            body_temperature = safe_float(row[mapped_columns['body_temperature']]) if 'body_temperature' in mapped_columns else None
            steps = safe_int(row[mapped_columns['steps']]) if 'steps' in mapped_columns else None
            sleep_hours = safe_float(row[mapped_columns['sleep_hours']]) if 'sleep_hours' in mapped_columns else None
            energy_level = safe_str(row[mapped_columns['energy_level']]) if 'energy_level' in mapped_columns else None
            
            # Log first row for debugging
            if idx == 0:
                print(f"[UPLOAD] First row sample - HR: {heart_rate}, SBP: {blood_pressure_systolic}, DBP: {blood_pressure_diastolic}, SpO2: {oxygen_saturation}, RR: {respiratory_rate}, Temp: {body_temperature}, Steps: {steps}, Sleep: {sleep_hours}")
                logger.info(f"First row: HR={heart_rate}, SBP={blood_pressure_systolic}, DBP={blood_pressure_diastolic}, SpO2={oxygen_saturation}, RR={respiratory_rate}, Temp={body_temperature}, Steps={steps}, Sleep={sleep_hours}")
            
            # Create vital record - ALL fields must be stored
            vital = Vital(
                patient_id=user.id,
                heart_rate=heart_rate,
                blood_pressure_systolic=blood_pressure_systolic,
                blood_pressure_diastolic=blood_pressure_diastolic,
                oxygen_saturation=oxygen_saturation,
                respiratory_rate=respiratory_rate,
                body_temperature=body_temperature,
                steps=steps,
                sleep_hours=sleep_hours,
                energy_level=energy_level,
                recorded_at=recorded_time
            )
            
            db.session.add(vital)
            vitals_added.append(vital)
            
            # Log every 10th row for verification
            if (idx + 1) % 10 == 0:
                print(f"[UPLOAD] Processed {idx + 1}/{total_rows} rows - HR: {heart_rate}, SBP: {blood_pressure_systolic}, DBP: {blood_pressure_diastolic}, RR: {respiratory_rate}, Temp: {body_temperature}, Sleep: {sleep_hours}")
        
        # Commit all vitals
        print(f"[UPLOAD] Committing {len(vitals_added)} vitals to database...")
        db.session.commit()
        print(f"[UPLOAD] Vitals committed successfully")
        
        # Run Heal.io Quantum DL Model Prediction
        print("[UPLOAD] ========== STARTING MODEL PREDICTION ==========", flush=True)
        logger.info("========== STARTING MODEL PREDICTION ==========")
        healio_prediction = None
        
        # FORCE MODEL EXECUTION - Always try to run the model
        print("[UPLOAD] Step 1: Importing healio_model...", flush=True)
        logger.info("Step 1: Importing healio_model...")
        sys.stdout.flush()
        
        # Get the model function - module should already be imported at startup
        try:
            print("[UPLOAD] Getting predict_from_csv from pre-imported module...", flush=True)
            logger.info("Getting predict_from_csv from pre-imported module...")
            sys.stdout.flush()
            
            # Use the pre-imported module
            import healio_model
            if hasattr(healio_model, 'predict_from_csv'):
                predict_from_csv = healio_model.predict_from_csv
                print(f"[UPLOAD] Function retrieved: {predict_from_csv}", flush=True)
                logger.info(f"Function retrieved: {predict_from_csv}")
            else:
                print("[ERROR] predict_from_csv function not found in module", flush=True)
                logger.error("predict_from_csv function not found in module")
                predict_from_csv = None
                
        except Exception as import_err:
            print(f"[ERROR] ========== IMPORT ERROR ==========", flush=True)
            print(f"[ERROR] Cannot get predict_from_csv: {import_err}", flush=True)
            logger.error(f"Import error: {import_err}")
            traceback.print_exc()
            print(f"[ERROR] ==================================", flush=True)
            sys.stdout.flush()
            predict_from_csv = None
        
        if predict_from_csv is not None and callable(predict_from_csv):
            print(f"[UPLOAD] predict_from_csv is available and callable", flush=True)
            logger.info("predict_from_csv is available and callable")
            print(f"[UPLOAD] Step 2: Preparing model data. CSV has {len(df)} rows", flush=True)
            logger.info(f"Step 2: Preparing model data. CSV has {len(df)} rows")
            print(f"[UPLOAD] Mapped columns: {mapped_columns}", flush=True)
            logger.info(f"Mapped columns: {mapped_columns}")
            sys.stdout.flush()
            
            # Prepare data for model: extract the 5 required features
            # heart_rate, sbp, dbp, spo2, sleep_state
            model_data = []
            print("[UPLOAD] Step 3: Extracting features from CSV...", flush=True)
            logger.info("Step 3: Extracting features from CSV...")
            sys.stdout.flush()
            
            row_count = 0
            for idx, row in df.iterrows():
                row_count += 1
                # Get heart_rate
                hr = 72  # default
                if 'heart_rate' in mapped_columns:
                    try:
                        hr = float(row[mapped_columns['heart_rate']]) if pd.notna(row[mapped_columns['heart_rate']]) else 72
                    except:
                        pass
                
                # Get sbp (systolic blood pressure)
                sbp = 120  # default
                if 'blood_pressure_systolic' in mapped_columns:
                    try:
                        sbp = float(row[mapped_columns['blood_pressure_systolic']]) if pd.notna(row[mapped_columns['blood_pressure_systolic']]) else 120
                    except:
                        pass
                
                # Get dbp (diastolic blood pressure)
                dbp = 80  # default
                if 'blood_pressure_diastolic' in mapped_columns:
                    try:
                        dbp = float(row[mapped_columns['blood_pressure_diastolic']]) if pd.notna(row[mapped_columns['blood_pressure_diastolic']]) else 80
                    except:
                        pass
                
                # Get spo2 (oxygen saturation)
                spo2 = 98  # default
                if 'oxygen_saturation' in mapped_columns:
                    try:
                        spo2 = float(row[mapped_columns['oxygen_saturation']]) if pd.notna(row[mapped_columns['oxygen_saturation']]) else 98
                    except:
                        pass
                
                # Map sleep_hours to sleep_state (0=awake, 1=light, 2=deep, 3=REM)
                sleep_state = 0
                if 'sleep_hours' in mapped_columns:
                    try:
                        sleep_hrs = float(row[mapped_columns['sleep_hours']]) if pd.notna(row[mapped_columns['sleep_hours']]) else 0
                        if sleep_hrs > 0.5:
                            sleep_state = 2  # Deep sleep
                        elif sleep_hrs > 0.25:
                            sleep_state = 1  # Light sleep
                        elif sleep_hrs > 0:
                            sleep_state = 3  # REM
                    except:
                        sleep_state = 0
                
                model_data.append([hr, sbp, dbp, spo2, sleep_state])
            
            print(f"[UPLOAD] Step 4: Converted {len(model_data)} rows to model format", flush=True)
            logger.info(f"Step 4: Converted {len(model_data)} rows to model format")
            sys.stdout.flush()
            
            # Convert to numpy array
            model_array = np.array(model_data)
            print(f"[UPLOAD] Step 5: Model data shape: {model_array.shape}", flush=True)
            logger.info(f"Step 5: Model data shape: {model_array.shape}")
            print(f"[UPLOAD] First 3 rows: {model_array[:3].tolist() if len(model_array) >= 3 else model_array.tolist()}", flush=True)
            sys.stdout.flush()
            
            # Run prediction - THIS IS THE CRITICAL CALL
            print(f"[UPLOAD] Step 6: CALLING predict_from_csv() NOW...", flush=True)
            print(f"[UPLOAD] Array shape being passed: {model_array.shape}", flush=True)
            print(f"[UPLOAD] Array dtype: {model_array.dtype}", flush=True)
            print(f"[UPLOAD] Array sample (first row): {model_array[0] if len(model_array) > 0 else 'EMPTY'}", flush=True)
            sys.stdout.flush()
            
            try:
                # Write to log file
                try:
                    with open('upload_log.txt', 'a') as f:
                        f.write(f"[{datetime.utcnow()}] About to call predict_from_csv with shape {model_array.shape}\n")
                        f.flush()
                except:
                    pass
                
                print(f"[UPLOAD] About to call predict_from_csv...", flush=True)
                logger.info("About to call predict_from_csv...")
                logger.info(f"Array shape: {model_array.shape}, dtype: {model_array.dtype}")
                sys.stdout.write(f"[UPLOAD] CALLING predict_from_csv NOW with shape {model_array.shape}\n")
                sys.stdout.flush()
                
                # ACTUALLY CALL THE FUNCTION - THIS IS THE CRITICAL LINE
                healio_prediction = predict_from_csv(model_array)
                
                # Write success to log file
                try:
                    with open('upload_log.txt', 'a') as f:
                        f.write(f"[{datetime.utcnow()}] predict_from_csv completed successfully\n")
                        f.write(f"Result: {healio_prediction}\n")
                        f.flush()
                except:
                    pass
                
                print(f"[UPLOAD] MODEL PREDICTION SUCCESSFUL", flush=True)
                logger.info("MODEL PREDICTION SUCCESSFUL")
                print(f"[UPLOAD] Prediction result type: {type(healio_prediction)}", flush=True)
                logger.info(f"Prediction result type: {type(healio_prediction)}")
                print(f"[UPLOAD] Prediction result: {healio_prediction}", flush=True)
                logger.info(f"Prediction result: {healio_prediction}")
                sys.stdout.flush()
                
                # Store prediction in session for display
                session['latest_healio_prediction'] = healio_prediction
                session.permanent = True  # Make session persistent
                print(f"[UPLOAD] ✓ Prediction stored in session", flush=True)
                print(f"[UPLOAD] Scores - Quantum: {healio_prediction.get('quantum_score', 'N/A')}, Classical: {healio_prediction.get('classical_score', 'N/A')}", flush=True)
            except Exception as model_error:
                print(f"[ERROR] ========== MODEL EXECUTION ERROR ==========", flush=True)
                print(f"[ERROR] Error during predict_from_csv call: {model_error}", flush=True)
                print(f"[ERROR] Error type: {type(model_error).__name__}", flush=True)
                traceback.print_exc()
                print(f"[ERROR] ===========================================", flush=True)
                sys.stdout.flush()
                healio_prediction = None
        else:
            print("[ERROR] predict_from_csv function not available - import failed", flush=True)
            logger.error("predict_from_csv function not available - import failed")
            print(f"[ERROR] predict_from_csv value: {predict_from_csv}", flush=True)
            logger.error(f"predict_from_csv value: {predict_from_csv}")
            sys.stdout.flush()
        
        print("[UPLOAD] ========== MODEL PREDICTION SECTION COMPLETE ==========", flush=True)
        print(f"[UPLOAD] Final healio_prediction status: {healio_prediction is not None}", flush=True)
        sys.stdout.flush()
        
        # Create anomalies and alerts based on Heal.io Quantum DL Model prediction
        anomalies_created = 0
        if healio_prediction:
            try:
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                
                # Map alert level to severity
                alert = healio_prediction.get('alert', 'NORMAL')
                if alert == 'HIGH RISK':
                    # Create anomaly for high risk detection
                    anomaly_type = 'quantum_high_risk'
                    existing = Anomaly.query.filter(
                        Anomaly.patient_id == user.id,
                        Anomaly.anomaly_type == anomaly_type,
                        Anomaly.detected_at >= cutoff_time
                    ).first()
                    
                    if not existing:
                        anomaly = Anomaly(
                            patient_id=user.id,
                            anomaly_type=anomaly_type,
                            severity='high',
                            description=f"High risk detected by Quantum DL Model. Quantum score: {healio_prediction.get('quantum_score', 0):.4f}, Classical score: {healio_prediction.get('classical_score', 0):.4f}",
                            risk_score=float(healio_prediction.get('quantum_score', 0)),
                            detected_at=datetime.utcnow(),
                            case_status='pending'
                        )
                        db.session.add(anomaly)
                        anomalies_created += 1
                        
                        # Create alert
                        alert_obj = Alert(
                            patient_id=user.id,
                            alert_type='quantum_high_risk',
                            message=f"HIGH RISK detected by Quantum DL Model. Immediate attention recommended.",
                            severity='critical',
                            is_read=False
                        )
                        db.session.add(alert_obj)
                
                elif alert == 'EARLY WARNING':
                    # Create anomaly for early warning
                    anomaly_type = 'quantum_early_warning'
                    existing = Anomaly.query.filter(
                        Anomaly.patient_id == user.id,
                        Anomaly.anomaly_type == anomaly_type,
                        Anomaly.detected_at >= cutoff_time
                    ).first()
                    
                    if not existing:
                        anomaly = Anomaly(
                            patient_id=user.id,
                            anomaly_type=anomaly_type,
                            severity='medium',
                            description=f"Early warning detected by Quantum DL Model. Quantum score: {healio_prediction.get('quantum_score', 0):.4f}, Classical score: {healio_prediction.get('classical_score', 0):.4f}",
                            risk_score=float(healio_prediction.get('quantum_score', 0)),
                            detected_at=datetime.utcnow(),
                            case_status='pending'
                        )
                        db.session.add(anomaly)
                        anomalies_created += 1
                        
                        # Create alert
                        alert_obj = Alert(
                            patient_id=user.id,
                            alert_type='quantum_early_warning',
                            message=f"Early warning detected by Quantum DL Model. Monitor closely.",
                            severity='high',
                            is_read=False
                        )
                        db.session.add(alert_obj)
                
                # Create anomalies for individual disease risks if above threshold (0.5)
                risks = healio_prediction.get('risks', {})
                risk_threshold = 0.5
                
                disease_mapping = {
                    'cardio': 'Cardiovascular',
                    'respiratory': 'Respiratory',
                    'metabolic': 'Metabolic',
                    'neurological': 'Neurological'
                }
                
                for risk_key, risk_value in risks.items():
                    if risk_value > risk_threshold:
                        disease_name = disease_mapping.get(risk_key, risk_key.title())
                        anomaly_type = f"quantum_{risk_key}_risk"
                        
                        # Check for duplicate
                        existing = Anomaly.query.filter(
                            Anomaly.patient_id == user.id,
                            Anomaly.anomaly_type == anomaly_type,
                            Anomaly.detected_at >= cutoff_time
                        ).first()
                        
                        if not existing:
                            # Determine severity based on risk value
                            if risk_value > 0.7:
                                severity = 'high'
                            elif risk_value > 0.5:
                                severity = 'medium'
                            else:
                                severity = 'low'
                            
                            anomaly = Anomaly(
                                patient_id=user.id,
                                anomaly_type=anomaly_type,
                                severity=severity,
                                description=f"{disease_name} risk detected by Quantum DL Model. Risk probability: {risk_value:.1%}",
                                risk_score=float(risk_value),
                                detected_at=datetime.utcnow(),
                                case_status='pending'
                            )
                            db.session.add(anomaly)
                            anomalies_created += 1
                            
                            # Create alert for high risk diseases
                            if risk_value > 0.7:
                                alert_obj = Alert(
                                    patient_id=user.id,
                                    alert_type='quantum_disease_risk',
                                    message=f"{disease_name} risk detected: {risk_value:.1%} probability (High)",
                                    severity='critical',
                                    is_read=False
                                )
                                db.session.add(alert_obj)
                            elif risk_value > 0.5:
                                alert_obj = Alert(
                                    patient_id=user.id,
                                    alert_type='quantum_disease_risk',
                                    message=f"{disease_name} risk detected: {risk_value:.1%} probability (Moderate)",
                                    severity='high',
                                    is_read=False
                                )
                                db.session.add(alert_obj)
                
                if anomalies_created > 0:
                    db.session.commit()
                    
            except Exception as e:
                print(f"Error creating anomalies from Heal.io prediction: {e}")
                import traceback
                traceback.print_exc()
                db.session.rollback()
        
        response_data = {
            'status': 'success',
            'count': len(vitals_added),
            'anomalies_created': anomalies_created,
            'message': f'Successfully uploaded {len(vitals_added)} vital records. {anomalies_created} anomaly/anomalies detected.' if anomalies_created > 0 else f'Successfully uploaded {len(vitals_added)} vital records.'
        }
        
        # Add Heal.io prediction results if available
        if healio_prediction:
            print(f"[UPLOAD] Adding prediction to response: {healio_prediction}")
            response_data['healio_prediction'] = healio_prediction
        else:
            print("[UPLOAD] WARNING: No prediction result available")
        
        print(f"[UPLOAD] Returning response: {response_data.get('status')}, count: {response_data.get('count')}, has_prediction: {healio_prediction is not None}")
        print("=" * 80)
        return jsonify(response_data)
        
    except pd.errors.EmptyDataError:
        db.session.rollback()
        print("[ERROR] Empty CSV file", flush=True)
        sys.stdout.flush()
        return jsonify({'status': 'error', 'message': 'CSV file is empty or invalid'}), 400
    except pd.errors.ParserError as e:
        db.session.rollback()
        print(f"[ERROR] CSV parse error: {e}", flush=True)
        sys.stdout.flush()
        return jsonify({'status': 'error', 'message': f'Invalid CSV format: {str(e)}'}), 400
    except UnicodeDecodeError:
        db.session.rollback()
        print("[ERROR] Unicode decode error", flush=True)
        sys.stdout.flush()
        return jsonify({'status': 'error', 'message': 'File encoding error. Please ensure the CSV file uses UTF-8 encoding'}), 400
    except Exception as e:
        db.session.rollback()
        error_trace = traceback.format_exc()
        print(f"[ERROR] ========== UNEXPECTED ERROR IN UPLOAD ==========", flush=True)
        print(f"Error in upload_vitals_csv: {error_trace}", flush=True)
        print(f"[ERROR] =================================================", flush=True)
        sys.stdout.flush()
        # Return user-friendly error message
        error_message = str(e)
        if "No module named" in error_message or "cannot import" in error_message.lower():
            error_message = "Disease detection module not available. Vitals uploaded successfully."
        elif len(error_message) > 200:
            error_message = "An error occurred while processing the file. Please check the CSV format."
        return jsonify({'status': 'error', 'message': error_message}), 500

@app.route('/patient/vitals')
@patient_required
def patient_vitals():
    user = User.query.get(session['user_id'])
    
    # Get current vitals
    current_vital = Vital.query.filter_by(patient_id=user.id).order_by(Vital.recorded_at.desc()).first()
    
    # Get latest Heal.io prediction from session (stored during upload)
    healio_prediction = session.get('latest_healio_prediction', None)
    
    # Get date range from query parameters
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    
    # Build query for vitals
    query = Vital.query.filter_by(patient_id=user.id)
    
    # Apply date filters if provided
    if from_date:
        try:
            # Parse date and set to start of day in UTC
            from_datetime = datetime.strptime(from_date, '%Y-%m-%d')
            from_datetime = from_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
            # Ensure UTC timezone for comparison
            from_datetime = from_datetime.replace(tzinfo=None)  # Remove timezone for SQLite
            query = query.filter(Vital.recorded_at >= from_datetime)
        except ValueError:
            pass
    
    if to_date:
        try:
            # Parse date and set to end of day in UTC (inclusive)
            to_datetime = datetime.strptime(to_date, '%Y-%m-%d')
            to_datetime = to_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)
            # Ensure UTC timezone for comparison
            to_datetime = to_datetime.replace(tzinfo=None)  # Remove timezone for SQLite
            query = query.filter(Vital.recorded_at <= to_datetime)
        except ValueError:
            pass
    
    # If no date filters, default to last year
    if not from_date and not to_date:
        one_year_ago = datetime.utcnow() - timedelta(days=365)
        query = query.filter(Vital.recorded_at >= one_year_ago)
    
    # Get vitals for visualization
    yearly_vitals = query.order_by(Vital.recorded_at.asc()).all()
    
    # Prepare data for charts - include all vital metrics (aligned with dates)
    vitals_data = {
        'dates': [v.recorded_at.strftime('%Y-%m-%d %H:%M') for v in yearly_vitals],
        'heart_rate': [v.heart_rate if v.heart_rate else None for v in yearly_vitals],
        'oxygen_saturation': [v.oxygen_saturation if v.oxygen_saturation else None for v in yearly_vitals],
        'blood_pressure_systolic': [v.blood_pressure_systolic if v.blood_pressure_systolic else None for v in yearly_vitals],
        'blood_pressure_diastolic': [v.blood_pressure_diastolic if v.blood_pressure_diastolic else None for v in yearly_vitals],
        'respiratory_rate': [v.respiratory_rate if v.respiratory_rate else None for v in yearly_vitals],
        'temperature': [v.body_temperature if v.body_temperature else None for v in yearly_vitals],
        'steps': [v.steps if v.steps else None for v in yearly_vitals],
        'sleep_hours': [v.sleep_hours if v.sleep_hours else None for v in yearly_vitals]
    }
    
    return render_template('patient/vitals.html', 
                         user=user,
                         current_vital=current_vital,
                         vitals_data=vitals_data,
                         from_date=from_date,
                         to_date=to_date,
                         healio_prediction=healio_prediction,
                         page='vitals')

@app.route('/patient/doctors')
@patient_required
def patient_doctors():
    user = User.query.get(session['user_id'])
    
    # Get connected doctors
    connected_doctors = PatientDoctor.query.filter_by(
        patient_id=user.id,
        status='accepted'
    ).all()
    
    # Get pending requests
    pending_requests = PatientDoctor.query.filter_by(
        patient_id=user.id,
        status='pending'
    ).all()
    
    # Get all available doctors
    all_doctors = User.query.filter_by(user_type='doctor').all()
    connected_doctor_ids = [rel.doctor_id for rel in connected_doctors]
    available_doctors = [d for d in all_doctors if d.id not in connected_doctor_ids]
    
    return render_template('patient/doctors.html', 
                         user=user,
                         connected_doctors=connected_doctors,
                         pending_requests=pending_requests,
                         available_doctors=available_doctors,
                         page='doctors')

@app.route('/patient/request_doctor/<int:doctor_id>', methods=['POST'])
@patient_required
def request_doctor(doctor_id):
    user = User.query.get(session['user_id'])
    doctor = User.query.get(doctor_id)
    
    if not doctor or doctor.user_type != 'doctor':
        flash('Invalid doctor.', 'error')
        return redirect(url_for('patient_doctors'))
    
    # Check if request already exists
    existing = PatientDoctor.query.filter_by(
        patient_id=user.id,
        doctor_id=doctor_id
    ).first()
    
    if existing:
        flash('Request already sent.', 'info')
    else:
        relationship = PatientDoctor(
            patient_id=user.id,
            doctor_id=doctor_id,
            status='pending'
        )
        db.session.add(relationship)
        db.session.commit()
        flash('Request sent to doctor.', 'success')
    
    return redirect(url_for('patient_doctors'))

# ============ DOCTOR ROUTES ============

@app.route('/doctor/dashboard')
@doctor_required
def doctor_dashboard():
    user = User.query.get(session['user_id'])
    
    # Get pending patient requests
    pending_requests = PatientDoctor.query.filter_by(
        doctor_id=user.id,
        status='pending'
    ).all()
    
    # Get accepted patients
    accepted_patients = PatientDoctor.query.filter_by(
        doctor_id=user.id,
        status='accepted'
    ).all()
    
    # Get assigned cases
    try:
        assigned_cases = Anomaly.query.filter_by(assigned_doctor_id=user.id).order_by(Anomaly.detected_at.desc()).limit(5).all()
    except Exception:
        assigned_cases = []
    
    # Get all assigned cases for consistency map
    try:
        all_assigned_cases = Anomaly.query.filter_by(assigned_doctor_id=user.id).all()
    except Exception:
        all_assigned_cases = []
    
    # Group anomalies by date for consistency map
    from collections import defaultdict
    daily_anomaly_status = {}
    anomalies_by_date = defaultdict(list)
    
    try:
        for case in all_assigned_cases:
            date_key = case.detected_at.date().isoformat()
            anomalies_by_date[date_key].append(case)
        
        # Mark days with anomalies
        for date_key, anomalies in anomalies_by_date.items():
            if anomalies:
                max_severity = max([a.severity for a in anomalies], key=lambda x: ['low', 'medium', 'high', 'critical'].index(x))
                daily_anomaly_status[date_key] = {
                    'has_anomaly': True,
                    'severity': max_severity,
                    'count': len(anomalies)
                }
    except Exception:
        pass
    
    return render_template('doctor/dashboard.html', 
                         user=user,
                         pending_requests=pending_requests,
                         accepted_patients=accepted_patients,
                         assigned_cases=assigned_cases,
                         daily_anomaly_status=daily_anomaly_status,
                         page='dashboard')

@app.route('/doctor/patients')
@doctor_required
def doctor_patients():
    user = User.query.get(session['user_id'])
    
    # Get all accepted patients
    relationships = PatientDoctor.query.filter_by(
        doctor_id=user.id,
        status='accepted'
    ).all()
    
    patients = [rel.patient for rel in relationships]
    
    return render_template('doctor/patients.html', 
                         user=user,
                         patients=patients,
                         page='patients')

@app.route('/doctor/patient/<int:patient_id>')
@doctor_required
def doctor_patient_detail(patient_id):
    user = User.query.get(session['user_id'])
    
    # Verify doctor has access to this patient
    relationship = PatientDoctor.query.filter_by(
        doctor_id=user.id,
        patient_id=patient_id,
        status='accepted'
    ).first()
    
    if not relationship:
        flash('Access denied.', 'error')
        return redirect(url_for('doctor_patients'))
    
    patient = User.query.get(patient_id)
    
    # Get current vitals
    current_vital = Vital.query.filter_by(patient_id=patient_id).order_by(Vital.recorded_at.desc()).first()
    
    # Get recent vitals for graph
    recent_vitals = Vital.query.filter_by(patient_id=patient_id).order_by(Vital.recorded_at.desc()).limit(30).all()
    
    # Prepare vitals data for charts - include all vital metrics
    vitals_data = {
        'dates': [v.recorded_at.strftime('%Y-%m-%d %H:%M') for v in reversed(recent_vitals)],
        'heart_rate': [v.heart_rate for v in reversed(recent_vitals) if v.heart_rate],
        'oxygen_saturation': [v.oxygen_saturation for v in reversed(recent_vitals) if v.oxygen_saturation],
        'blood_pressure_systolic': [v.blood_pressure_systolic for v in reversed(recent_vitals) if v.blood_pressure_systolic],
        'blood_pressure_diastolic': [v.blood_pressure_diastolic for v in reversed(recent_vitals) if v.blood_pressure_diastolic],
        'respiratory_rate': [v.respiratory_rate for v in reversed(recent_vitals) if v.respiratory_rate],
        'temperature': [v.body_temperature for v in reversed(recent_vitals) if v.body_temperature],
        'steps': [v.steps for v in reversed(recent_vitals) if v.steps],
        'sleep_hours': [v.sleep_hours for v in reversed(recent_vitals) if v.sleep_hours]
    }
    
    return render_template('doctor/patient_detail.html', 
                         user=user,
                         patient=patient,
                         current_vital=current_vital,
                         vitals_data=vitals_data,
                         page='patient_detail')

@app.route('/doctor/cases')
@doctor_required
def doctor_cases():
    user = User.query.get(session['user_id'])
    
    # Get assigned anomalies
    try:
        assigned_cases = Anomaly.query.filter_by(assigned_doctor_id=user.id).order_by(Anomaly.detected_at.desc()).all()
    except Exception:
        assigned_cases = []
    
    return render_template('doctor/cases.html',
                         user=user,
                         cases=assigned_cases,
                         page='cases')

@app.route('/doctor/case/<int:anomaly_id>')
@doctor_required
def doctor_view_case(anomaly_id):
    user = User.query.get(session['user_id'])
    anomaly = Anomaly.query.get_or_404(anomaly_id)
    
    # Verify doctor is assigned to this anomaly
    if anomaly.assigned_doctor_id != user.id:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('doctor_cases'))
    
    patient = User.query.get(anomaly.patient_id)
    
    # Get vitals related to this case - last 30 records only
    # Get the most recent 30 vitals before and up to the anomaly detection time
    related_vitals = Vital.query.filter(
        Vital.patient_id == anomaly.patient_id,
        Vital.recorded_at <= anomaly.detected_at
    ).order_by(Vital.recorded_at.desc()).limit(30).all()
    
    # Reverse to get chronological order (oldest first)
    related_vitals = list(reversed(related_vitals))
    
    # Get latest vital for current metrics display
    latest_vital = Vital.query.filter_by(patient_id=anomaly.patient_id).order_by(Vital.recorded_at.desc()).first()
    
    # Prepare vitals data for charts
    vitals_data = {
        'dates': [v.recorded_at.strftime('%Y-%m-%d %H:%M') for v in related_vitals],
        'heart_rate': [v.heart_rate for v in related_vitals if v.heart_rate],
        'oxygen_saturation': [v.oxygen_saturation for v in related_vitals if v.oxygen_saturation],
        'blood_pressure_systolic': [v.blood_pressure_systolic for v in related_vitals if v.blood_pressure_systolic],
        'blood_pressure_diastolic': [v.blood_pressure_diastolic for v in related_vitals if v.blood_pressure_diastolic],
        'respiratory_rate': [v.respiratory_rate for v in related_vitals if v.respiratory_rate],
        'temperature': [v.body_temperature for v in related_vitals if v.body_temperature],
        'steps': [v.steps for v in related_vitals if v.steps],
        'sleep_hours': [v.sleep_hours for v in related_vitals if v.sleep_hours]
    }
    
    return render_template('doctor/case_detail.html',
                         user=user,
                         anomaly=anomaly,
                         patient=patient,
                         latest_vital=latest_vital,
                         vitals_data=vitals_data,
                         related_vitals=related_vitals,
                         page='cases')

@app.route('/doctor/anomaly/<int:anomaly_id>/complete', methods=['POST'])
@doctor_required
def complete_anomaly(anomaly_id):
    user = User.query.get(session['user_id'])
    anomaly = Anomaly.query.get_or_404(anomaly_id)
    
    # Verify doctor is assigned to this anomaly
    if anomaly.assigned_doctor_id != user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    
    # Mark as completed
    anomaly.case_status = 'completed'
    
    # Increment doctor's persons_treated count
    if user.persons_treated is None:
        user.persons_treated = 0
    user.persons_treated += 1
    
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'Case marked as completed', 'persons_treated': user.persons_treated})

@app.route('/doctor/anomaly/<int:anomaly_id>/transfer')
@doctor_required
def transfer_anomaly_page(anomaly_id):
    user = User.query.get(session['user_id'])
    anomaly = Anomaly.query.get_or_404(anomaly_id)
    
    # Verify doctor is assigned to this anomaly
    if anomaly.assigned_doctor_id != user.id:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('doctor_cases'))
    
    # Get all other doctors (excluding current doctor)
    other_doctors = User.query.filter(
        User.user_type == 'doctor',
        User.id != user.id
    ).all()
    
    return render_template('doctor/transfer_case.html',
                         user=user,
                         anomaly=anomaly,
                         doctors=other_doctors,
                         page='cases')

@app.route('/doctor/anomaly/<int:anomaly_id>/transfer/<int:new_doctor_id>', methods=['POST'])
@doctor_required
def transfer_anomaly(anomaly_id, new_doctor_id):
    user = User.query.get(session['user_id'])
    anomaly = Anomaly.query.get_or_404(anomaly_id)
    new_doctor = User.query.get_or_404(new_doctor_id)
    
    # Verify doctor is assigned to this anomaly
    if anomaly.assigned_doctor_id != user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    
    if new_doctor.user_type != 'doctor':
        return jsonify({'status': 'error', 'message': 'Invalid doctor'}), 400
    
    # Transfer anomaly
    anomaly.transferred_from_doctor_id = user.id
    anomaly.assigned_doctor_id = new_doctor_id
    anomaly.case_status = 'transferred'
    anomaly.assigned_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': f'Case transferred to Dr. {new_doctor.first_name} {new_doctor.last_name}'})

@app.route('/doctor/case/<int:anomaly_id>/generate-pdf')
@doctor_required
def generate_case_pdf(anomaly_id):
    user = User.query.get(session['user_id'])
    anomaly = Anomaly.query.get_or_404(anomaly_id)
    
    # Verify doctor is assigned to this anomaly
    if anomaly.assigned_doctor_id != user.id:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('doctor_cases'))
    
    patient = User.query.get(anomaly.patient_id)
    
    # Get last 30 vitals related to this case
    related_vitals = Vital.query.filter(
        Vital.patient_id == anomaly.patient_id,
        Vital.recorded_at <= anomaly.detected_at
    ).order_by(Vital.recorded_at.desc()).limit(30).all()
    related_vitals = list(reversed(related_vitals))
    
    # Get latest vital
    latest_vital = Vital.query.filter_by(patient_id=anomaly.patient_id).order_by(Vital.recorded_at.desc()).first()
    
    # Get all anomalies for this patient to determine disease risks
    all_patient_anomalies = Anomaly.query.filter_by(patient_id=anomaly.patient_id).all()
    
    # Disease features mapping
    disease_features = {
        "Neurological": ["sleep_entropy", "sleep_transition_rate", "hr_irregularity"],
        "Cardiovascular": ["hr_mean", "sbp_trend", "bp_gap"],
        "Respiratory": ["spo2_trend", "spo2_variability", "hr_mean", "bp_gap"],
        "Infectious": ["hr_mean", "hrv"],
        "Metabolic": ["bp_gap", "hr_mean"],
        "Mental Health": ["sleep_entropy", "sleep_transition_rate"]
    }
    
    feature_explain = {
        "sleep_entropy": "high sleep fragmentation",
        "sleep_transition_rate": "frequent sleep stage changes",
        "hrv": "abnormal heart rate variability",
        "hr_irregularity": "irregular heart rate pattern",
        "hr_mean": "abnormal heart rate",
        "sbp_trend": "unstable systolic blood pressure",
        "bp_gap": "abnormal pulse pressure",
        "spo2_trend": "falling oxygen saturation",
        "spo2_variability": "high oxygen saturation swings"
    }
    
    # Generate 3D map based on actual anomaly data
    diseases = list(disease_features.keys())
    features = list(feature_explain.keys())
    disease_idx = {d: i for i, d in enumerate(diseases)}
    feature_idx = {f: i for i, f in enumerate(features)}
    
    # Map anomaly types to diseases and calculate scores
    x, y, z = [], [], []
    anomaly_disease_map = {}
    
    for patient_anomaly in all_patient_anomalies:
        anomaly_type = patient_anomaly.anomaly_type.lower()
        risk_score = patient_anomaly.risk_score if patient_anomaly.risk_score else 0.5
        
        # Map anomaly type to disease category
        for disease, feats in disease_features.items():
            if disease.lower().replace(' ', '_') in anomaly_type or anomaly_type in disease.lower():
                anomaly_disease_map[disease] = max(anomaly_disease_map.get(disease, 0), risk_score)
                for feat in feats:
                    if feat in feature_idx:
                        x.append(disease_idx[disease])
                        y.append(feature_idx[feat])
                        z.append(risk_score)
    
    # If no anomalies mapped, use the current anomaly
    if not x:
        anomaly_type = anomaly.anomaly_type.lower()
        risk_score = anomaly.risk_score if anomaly.risk_score else 0.7
        
        for disease, feats in disease_features.items():
            if disease.lower().replace(' ', '_') in anomaly_type or anomaly_type in disease.lower():
                for feat in feats:
                    if feat in feature_idx:
                        x.append(disease_idx[disease])
                        y.append(feature_idx[feat])
                        z.append(risk_score)
    
    # Generate 3D map image
    img_buffer = io.BytesIO()
    if x and y and z:
        fig = plt.figure(figsize=(10, 7))
        ax = fig.add_subplot(111, projection="3d")
        
        scatter = ax.scatter(x, y, z, c=z, cmap="viridis", s=120)
        
        ax.set_xlabel("Disease Category")
        ax.set_ylabel("Physiological Feature")
        ax.set_zlabel("Anomaly Severity")
        
        ax.set_xticks(range(len(diseases)))
        ax.set_xticklabels(diseases, rotation=30, ha="right")
        
        ax.set_yticks(range(len(features)))
        ax.set_yticklabels(features, fontsize=8)
        
        plt.colorbar(scatter, pad=0.1, label="Severity Score")
        plt.title("3D Disease–Feature Anomaly Map")
        
        plt.tight_layout()
        plt.savefig(img_buffer, format='png', dpi=200, bbox_inches='tight')
        plt.close()
        img_buffer.seek(0)
    
    # Generate summaries
    doctor_summary = "<b>Clinical Interpretation</b><br/>"
    patient_summary = "<b>Patient-Friendly Summary</b><br/>"
    
    # Build doctor summary from detected anomalies
    detected_diseases = set()
    for patient_anomaly in all_patient_anomalies:
        anomaly_type = patient_anomaly.anomaly_type.lower()
        for disease in disease_features.keys():
            if disease.lower().replace(' ', '_') in anomaly_type or anomaly_type in disease.lower():
                detected_diseases.add(disease)
    
    for disease in detected_diseases:
        if disease in disease_features:
            doctor_summary += f"<br/><b>{disease}</b><br/>"
            for feat in disease_features[disease]:
                if feat in feature_explain:
                    doctor_summary += f"- {feature_explain[feat]}<br/>"
    
    if not detected_diseases:
        # Fallback to current anomaly
        doctor_summary += f"<br/><b>{anomaly.anomaly_type.replace('_', ' ').title()}</b><br/>"
        doctor_summary += f"- {anomaly.description or 'Anomaly detected'}<br/>"
    
    patient_summary += (
        "Multiple physiological signals show abnormal patterns. "
        "These patterns may indicate stress on neurological, "
        "cardiovascular, respiratory, or metabolic systems. "
        "Please consult a healthcare professional for confirmation."
    )
    
    # Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#334155'),
        spaceAfter=12,
        spaceBefore=20
    )
    
    # Title
    elements.append(Paragraph("Health Anomaly Assessment Report", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Case Information
    elements.append(Paragraph("Case Information", heading_style))
    case_data = [
        ['Anomaly Type:', anomaly.anomaly_type.replace('_', ' ').title()],
        ['Severity:', anomaly.severity.upper()],
        ['Status:', anomaly.case_status.upper()],
        ['Risk Score:', f"{anomaly.risk_score:.3f}" if anomaly.risk_score else 'N/A'],
        ['Detected At:', anomaly.detected_at.strftime('%B %d, %Y at %H:%M UTC')],
    ]
    if anomaly.assigned_at:
        case_data.append(['Assigned At:', anomaly.assigned_at.strftime('%B %d, %Y at %H:%M UTC')])
    
    case_table = Table(case_data, colWidths=[2*inch, 4*inch])
    case_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1e293b')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0'))
    ]))
    elements.append(case_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Patient Information
    elements.append(Paragraph("Patient Information", heading_style))
    patient_data = [
        ['Name:', f"{patient.first_name} {patient.last_name}"],
        ['Email:', patient.email],
        ['Phone:', patient.phone or 'N/A'],
    ]
    if patient.date_of_birth:
        patient_data.append(['Date of Birth:', patient.date_of_birth.strftime('%B %d, %Y')])
    
    patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1e293b')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0'))
    ]))
    elements.append(patient_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Description
    if anomaly.description:
        elements.append(Paragraph("Description", heading_style))
        elements.append(Paragraph(anomaly.description, styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
    
    # Clinical Interpretation
    elements.append(PageBreak())
    elements.append(Paragraph("Clinical Interpretation", heading_style))
    elements.append(Paragraph(doctor_summary, styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Patient-Friendly Summary
    elements.append(Paragraph("Patient-Friendly Summary", heading_style))
    elements.append(Paragraph(patient_summary, styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Generate 2D vital charts
    chart_images = []
    
    if related_vitals:
        # Prepare chart data
        dates = [v.recorded_at.strftime('%Y-%m-%d %H:%M') for v in related_vitals]
        heart_rates = [v.heart_rate for v in related_vitals if v.heart_rate]
        spo2_values = [v.oxygen_saturation for v in related_vitals if v.oxygen_saturation]
        bp_systolic = [v.blood_pressure_systolic for v in related_vitals if v.blood_pressure_systolic]
        bp_diastolic = [v.blood_pressure_diastolic for v in related_vitals if v.blood_pressure_diastolic]
        resp_rates = [v.respiratory_rate for v in related_vitals if v.respiratory_rate]
        
        # Heart Rate Chart
        if heart_rates:
            hr_dates = [dates[i] for i, v in enumerate(related_vitals) if v.heart_rate]
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(hr_dates, heart_rates, color='#ef4444', linewidth=2, marker='o', markersize=3)
            ax.fill_between(hr_dates, heart_rates, alpha=0.3, color='#ef4444')
            ax.set_xlabel('Date/Time', fontsize=9)
            ax.set_ylabel('Heart Rate (BPM)', fontsize=9, color='#ef4444')
            ax.set_title('Heart Rate Trend', fontsize=11, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.tick_params(axis='x', rotation=45, labelsize=7)
            plt.tight_layout()
            hr_buffer = io.BytesIO()
            plt.savefig(hr_buffer, format='png', dpi=150, bbox_inches='tight')
            plt.close()
            hr_buffer.seek(0)
            chart_images.append(('Heart Rate Trend', hr_buffer))
        
        # SpO2 Chart
        if spo2_values:
            spo2_dates = [dates[i] for i, v in enumerate(related_vitals) if v.oxygen_saturation]
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(spo2_dates, spo2_values, color='#10b981', linewidth=2, marker='o', markersize=3)
            ax.fill_between(spo2_dates, spo2_values, alpha=0.3, color='#10b981')
            ax.set_xlabel('Date/Time', fontsize=9)
            ax.set_ylabel('Oxygen Saturation (SpO2%)', fontsize=9, color='#10b981')
            ax.set_title('Oxygen Saturation Trend', fontsize=11, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.tick_params(axis='x', rotation=45, labelsize=7)
            plt.tight_layout()
            spo2_buffer = io.BytesIO()
            plt.savefig(spo2_buffer, format='png', dpi=150, bbox_inches='tight')
            plt.close()
            spo2_buffer.seek(0)
            chart_images.append(('Oxygen Saturation Trend', spo2_buffer))
        
        # Blood Pressure Chart
        if bp_systolic and bp_diastolic:
            bp_dates = [dates[i] for i, v in enumerate(related_vitals) if v.blood_pressure_systolic and v.blood_pressure_diastolic]
            bp_sys = [v.blood_pressure_systolic for v in related_vitals if v.blood_pressure_systolic and v.blood_pressure_diastolic]
            bp_dia = [v.blood_pressure_diastolic for v in related_vitals if v.blood_pressure_systolic and v.blood_pressure_diastolic]
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(bp_dates, bp_sys, color='#3b82f6', linewidth=2, marker='o', markersize=3, label='Systolic')
            ax.plot(bp_dates, bp_dia, color='#8b5cf6', linewidth=2, marker='s', markersize=3, label='Diastolic')
            ax.fill_between(bp_dates, bp_sys, alpha=0.2, color='#3b82f6')
            ax.fill_between(bp_dates, bp_dia, alpha=0.2, color='#8b5cf6')
            ax.set_xlabel('Date/Time', fontsize=9)
            ax.set_ylabel('Blood Pressure (mmHg)', fontsize=9)
            ax.set_title('Blood Pressure Trend', fontsize=11, fontweight='bold')
            ax.legend(loc='best', fontsize=8)
            ax.grid(True, alpha=0.3)
            ax.tick_params(axis='x', rotation=45, labelsize=7)
            plt.tight_layout()
            bp_buffer = io.BytesIO()
            plt.savefig(bp_buffer, format='png', dpi=150, bbox_inches='tight')
            plt.close()
            bp_buffer.seek(0)
            chart_images.append(('Blood Pressure Trend', bp_buffer))
        
        # Respiratory Rate Chart
        if resp_rates:
            resp_dates = [dates[i] for i, v in enumerate(related_vitals) if v.respiratory_rate]
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(resp_dates, resp_rates, color='#f59e0b', linewidth=2, marker='o', markersize=3)
            ax.fill_between(resp_dates, resp_rates, alpha=0.3, color='#f59e0b')
            ax.set_xlabel('Date/Time', fontsize=9)
            ax.set_ylabel('Respiratory Rate (breaths/min)', fontsize=9, color='#f59e0b')
            ax.set_title('Respiratory Rate Trend', fontsize=11, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.tick_params(axis='x', rotation=45, labelsize=7)
            plt.tight_layout()
            resp_buffer = io.BytesIO()
            plt.savefig(resp_buffer, format='png', dpi=150, bbox_inches='tight')
            plt.close()
            resp_buffer.seek(0)
            chart_images.append(('Respiratory Rate Trend', resp_buffer))
    
    # 3D Disease-Feature Map
    if img_buffer and len(x) > 0:
        elements.append(PageBreak())
        elements.append(Paragraph("3D Disease–Feature Anomaly Map", heading_style))
        img_buffer.seek(0)
        elements.append(Image(img_buffer, width=450, height=320))
        elements.append(Spacer(1, 0.3*inch))
    
    # Add 2D Vital Charts
    if chart_images:
        elements.append(PageBreak())
        elements.append(Paragraph("Vital Signs Trends", heading_style))
        elements.append(Spacer(1, 0.2*inch))
        
        for chart_title, chart_buffer in chart_images:
            elements.append(Paragraph(chart_title, ParagraphStyle('ChartTitle', parent=styles['Heading3'], fontSize=12, spaceAfter=6)))
            chart_buffer.seek(0)
            elements.append(Image(chart_buffer, width=500, height=250))
            elements.append(Spacer(1, 0.2*inch))
    
    # Current Vital Metrics
    if latest_vital:
        elements.append(Paragraph("Current Vital Metrics", heading_style))
        vitals_data = []
        if latest_vital.heart_rate:
            vitals_data.append(['Heart Rate:', f"{latest_vital.heart_rate:.0f} BPM"])
        if latest_vital.oxygen_saturation:
            vitals_data.append(['Oxygen Saturation (SpO2):', f"{latest_vital.oxygen_saturation:.0f}%"])
        if latest_vital.blood_pressure_systolic and latest_vital.blood_pressure_diastolic:
            vitals_data.append(['Blood Pressure:', f"{latest_vital.blood_pressure_systolic:.0f}/{latest_vital.blood_pressure_diastolic:.0f} mmHg"])
        if latest_vital.respiratory_rate:
            vitals_data.append(['Respiratory Rate:', f"{latest_vital.respiratory_rate:.0f} breaths/min"])
        if latest_vital.body_temperature:
            vitals_data.append(['Body Temperature:', f"{latest_vital.body_temperature:.1f} °C"])
        if latest_vital.steps:
            vitals_data.append(['Steps:', f"{latest_vital.steps} steps"])
        
        if vitals_data:
            vitals_table = Table(vitals_data, colWidths=[2.5*inch, 3.5*inch])
            vitals_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1e293b')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0'))
            ]))
            elements.append(vitals_table)
            elements.append(Spacer(1, 0.3*inch))
    
    # Vitals Timeline Data
    if related_vitals:
        elements.append(PageBreak())
        elements.append(Paragraph("Vitals Timeline (Last 30 Records)", heading_style))
        
        # Prepare table data
        table_data = [['Date/Time', 'HR (BPM)', 'SpO2 (%)', 'BP (mmHg)', 'RR', 'Temp (°C)']]
        
        for vital in related_vitals:
            row = [
                vital.recorded_at.strftime('%Y-%m-%d %H:%M'),
                f"{vital.heart_rate:.0f}" if vital.heart_rate else 'N/A',
                f"{vital.oxygen_saturation:.0f}" if vital.oxygen_saturation else 'N/A',
                f"{vital.blood_pressure_systolic:.0f}/{vital.blood_pressure_diastolic:.0f}" if vital.blood_pressure_systolic and vital.blood_pressure_diastolic else 'N/A',
                f"{vital.respiratory_rate:.0f}" if vital.respiratory_rate else 'N/A',
                f"{vital.body_temperature:.1f}" if vital.body_temperature else 'N/A'
            ]
            table_data.append(row)
        
        # Create table
        vitals_timeline_table = Table(table_data, colWidths=[1.2*inch, 0.8*inch, 0.8*inch, 1*inch, 0.7*inch, 0.8*inch])
        vitals_timeline_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')])
        ]))
        elements.append(vitals_timeline_table)
    
    # Footer
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph(f"Generated on {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}", 
                              ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, 
                                           textColor=colors.HexColor('#64748b'), alignment=TA_CENTER)))
    elements.append(Paragraph(f"Assigned Doctor: Dr. {user.first_name} {user.last_name}", 
                              ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, 
                                           textColor=colors.HexColor('#64748b'), alignment=TA_CENTER)))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF from buffer
    buffer.seek(0)
    
    # Generate filename
    filename = f"Health_Anomaly_Report_{anomaly.id}_{patient.first_name}_{patient.last_name}_{anomaly.detected_at.strftime('%Y%m%d')}.pdf"
    
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)

@app.route('/doctor/accept_request/<int:request_id>', methods=['POST'])
@doctor_required
def accept_request(request_id):
    user = User.query.get(session['user_id'])
    
    relationship = PatientDoctor.query.get(request_id)
    
    if not relationship or relationship.doctor_id != user.id:
        flash('Invalid request.', 'error')
        return redirect(url_for('doctor_dashboard'))
    
    relationship.status = 'accepted'
    relationship.accepted_at = datetime.utcnow()
    db.session.commit()
    
    flash('Patient request accepted.', 'success')
    return redirect(url_for('doctor_dashboard'))

@app.route('/doctor/reject_request/<int:request_id>', methods=['POST'])
@doctor_required
def reject_request(request_id):
    user = User.query.get(session['user_id'])
    
    relationship = PatientDoctor.query.get(request_id)
    
    if not relationship or relationship.doctor_id != user.id:
        flash('Invalid request.', 'error')
        return redirect(url_for('doctor_dashboard'))
    
    relationship.status = 'rejected'
    db.session.commit()
    
    flash('Patient request rejected.', 'info')
    return redirect(url_for('doctor_dashboard'))

# ============ API ROUTES FOR DATA (for future ML integration) ============

@app.route('/api/vitals', methods=['POST'])
@login_required
def add_vital():
    """API endpoint for adding vitals data (from wearables/sensors)"""
    data = request.json
    user_id = session.get('user_id')
    
    vital = Vital(
        patient_id=user_id,
        heart_rate=data.get('heart_rate'),
        blood_pressure_systolic=data.get('blood_pressure_systolic'),
        blood_pressure_diastolic=data.get('blood_pressure_diastolic'),
        oxygen_saturation=data.get('oxygen_saturation'),
        respiratory_rate=data.get('respiratory_rate'),
        body_temperature=data.get('body_temperature'),
        steps=data.get('steps'),
        sleep_hours=data.get('sleep_hours'),
        energy_level=data.get('energy_level')
    )
    
    db.session.add(vital)
    db.session.commit()
    
    return jsonify({'status': 'success', 'vital_id': vital.id})


# Test endpoint to verify upload route is accessible
@app.route('/test-upload-route', methods=['GET'])
def test_upload_route():
    """Test if upload route is accessible"""
    logger.info("Test upload route called")
    print("[TEST] Upload route test endpoint called", flush=True)
    return jsonify({
        'status': 'success',
        'message': 'Upload route is accessible',
        'route': '/patient/upload-vitals-csv'
    })

# Test endpoint to verify model works
@app.route('/test-model', methods=['GET'])
def test_model():
    """Test endpoint to verify model is working"""
    import sys
    sys.stdout.flush()
    print("[TEST] Test endpoint called", flush=True)
    
    try:
        from healio_model import predict_from_csv, healio_predict
        import numpy as np
        
        # Create test data
        test_data = np.random.normal(
            loc=[72, 45, 98, 0.19, 0.42],
            scale=[2, 2, 0.4, 0.015, 0.04],
            size=(60, 5)
        )
        
        print(f"[TEST] Calling healio_predict with test data...", flush=True)
        result = healio_predict(test_data)
        print(f"[TEST] Result: {result}", flush=True)
        
        return jsonify({
            'status': 'success',
            'message': 'Model test successful',
            'prediction': result
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[TEST ERROR] {error_trace}", flush=True)
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': error_trace
        }), 500

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    print("=" * 80)
    print("Starting Flask app with debug logging enabled")
    print("=" * 80)
    app.run(debug=True, port=5000, use_reloader=False)
