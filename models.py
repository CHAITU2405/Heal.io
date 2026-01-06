"""
Database Models for Heal.io Application
"""
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    """User model for patients and doctors"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'patient' or 'doctor'
    phone = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    
    # Doctor-specific fields
    license_number = db.Column(db.String(100))
    specialization = db.Column(db.String(200))
    persons_treated = db.Column(db.Integer, default=0)
    
    # Patient-specific fields
    is_non_verbal = db.Column(db.Boolean, default=False)
    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_phone = db.Column(db.String(20))
    
    # Relationships
    vitals = db.relationship('Vital', backref='patient', lazy='dynamic', foreign_keys='Vital.patient_id')
    anomalies = db.relationship('Anomaly', backref='patient', lazy='dynamic', foreign_keys='Anomaly.patient_id')
    alerts = db.relationship('Alert', backref='patient', lazy='dynamic', foreign_keys='Alert.patient_id')
    
    # Doctor relationships
    assigned_anomalies = db.relationship('Anomaly', backref='assigned_doctor', lazy='dynamic', foreign_keys='Anomaly.assigned_doctor_id')
    patient_relationships = db.relationship('PatientDoctor', backref='doctor', lazy='dynamic', foreign_keys='PatientDoctor.doctor_id')
    
    # Patient relationships
    doctor_relationships = db.relationship('PatientDoctor', backref='patient', lazy='dynamic', foreign_keys='PatientDoctor.patient_id')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'

class Vital(db.Model):
    """Vital signs model"""
    __tablename__ = 'vitals'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Vital signs
    heart_rate = db.Column(db.Float)
    blood_pressure_systolic = db.Column(db.Float)
    blood_pressure_diastolic = db.Column(db.Float)
    oxygen_saturation = db.Column(db.Float)
    respiratory_rate = db.Column(db.Float)
    body_temperature = db.Column(db.Float)
    steps = db.Column(db.Integer)
    sleep_hours = db.Column(db.Float)
    energy_level = db.Column(db.String(50))
    
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f'<Vital {self.id} for Patient {self.patient_id}>'

class Anomaly(db.Model):
    """Anomaly detection model"""
    __tablename__ = 'anomalies'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    assigned_doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    transferred_from_doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    anomaly_type = db.Column(db.String(200), nullable=False)
    severity = db.Column(db.String(20), nullable=False)  # 'low', 'medium', 'high', 'critical'
    description = db.Column(db.Text)
    risk_score = db.Column(db.Float)
    
    detected_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    assigned_at = db.Column(db.DateTime)
    case_status = db.Column(db.String(50), default='pending')  # 'pending', 'assigned', 'completed', 'transferred'
    
    def __repr__(self):
        return f'<Anomaly {self.id} - {self.anomaly_type}>'

class Alert(db.Model):
    """Alert model for notifications"""
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    alert_type = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False)  # 'low', 'medium', 'high', 'critical'
    is_read = db.Column(db.Boolean, default=False, index=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f'<Alert {self.id} - {self.alert_type}>'

class PatientDoctor(db.Model):
    """Relationship model between patients and doctors"""
    __tablename__ = 'patient_doctors'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    status = db.Column(db.String(20), default='pending')  # 'pending', 'accepted', 'rejected'
    accepted_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<PatientDoctor {self.patient_id} - {self.doctor_id} ({self.status})>'

