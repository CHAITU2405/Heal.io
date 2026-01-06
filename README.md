# Heal.io

**An Integrated System for Early Disease Detection, Assistive Communication, and Affordable Precision Smartwatch Design**

[![GitHub](https://img.shields.io/badge/GitHub-Repository-blue)](https://github.com/CHAITU2405/Heal.io)

## 📋 Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Solution](#solution)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [Quantum Deep Learning Model](#quantum-deep-learning-model)
- [CSV Format](#csv-format)
- [Database Schema](#database-schema)
- [API Endpoints](#api-endpoints)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

Heal.io is a comprehensive healthcare platform that combines **quantum-enhanced deep learning** for early disease detection with assistive communication features and an affordable smartwatch design. The system enables real-time monitoring of vital signs, early anomaly detection, and seamless doctor-patient communication.

## 🔍 Problem Statement

### Early Disease Detection Challenge
Early detection of diseases remains a critical challenge due to the difficulty of identifying subtle micro-level patterns in physiological vital signals collected through wearable devices. These early deviations often occur before visible symptoms appear, making timely intervention difficult.

### Communication Barriers
Individuals with limited physical mobility or speech impairments face challenges in communicating health emergencies effectively, which can lead to delayed medical assistance.

### Cost and Accessibility
Existing wearable devices that offer advanced health monitoring and communication capabilities are often expensive, limiting accessibility for a large population.

## 💡 Solution

Heal.io provides an integrated system that:

1. **Early Disease Detection**: Uses quantum-enhanced deep learning to accurately detect early disease risks from wearable vital signals by identifying subtle micro-level patterns in physiological data
2. **Assistive Communication**: Enables alternative communication mechanisms for physically challenged users to effectively communicate health emergencies
3. **Affordable Smartwatch Design**: Supports the development of a cost-effective, precision smartwatch architecture suitable for large-scale adoption

## ✨ Key Features

### For Patients
- **Real-time Vital Monitoring**: Upload CSV files containing vital signs data for analysis
- **Quantum DL Disease Prediction**: Advanced quantum-enhanced deep learning model predicts disease risks (Cardiovascular, Respiratory, Metabolic, Neurological)
- **Anomaly Detection**: Automatic detection of health anomalies with severity classification
- **Doctor Connection**: Connect with doctors, request consultations, and manage health records
- **Health Dashboard**: Visual dashboard with health scores, trends, and alerts
- **Emergency Alerts**: Quick alert system for health emergencies
- **Vital Trends**: Interactive charts for Heart Rate (BPM) and Oxygen Saturation (SpO2)

### For Doctors
- **Patient Management**: View connected patients, their vitals, and health history
- **Anomaly Review**: Review and assign anomalies, transfer cases between doctors
- **Case Management**: Track patient cases, update status, and provide recommendations
- **Patient Analytics**: Access detailed patient vitals and trends

### Technical Features
- **Quantum-Enhanced ML**: Hybrid quantum-classical deep learning model for superior pattern recognition
- **Multi-Disease Risk Prediction**: Simultaneous prediction of 4 disease categories
- **Real-time Processing**: Fast CSV upload and processing with immediate predictions
- **Scalable Architecture**: Flask-based web application with SQLite database
- **Secure Authentication**: Role-based access control (Patient/Doctor)

## 🛠 Technology Stack

### Backend
- **Flask** - Web framework
- **Flask-SQLAlchemy** - ORM for database operations
- **SQLite** - Database (can be upgraded to PostgreSQL for production)

### Machine Learning & Quantum Computing
- **TensorFlow/Keras** - Deep learning models (BiLSTM embeddings, risk prediction)
- **PennyLane** - Quantum computing framework for quantum distance calculations
- **scikit-learn** - Classical ML (Isolation Forest, PCA, MinMaxScaler)

### Data Processing
- **Pandas** - CSV processing and data manipulation
- **NumPy** - Numerical computations

### Visualization & Reporting
- **Chart.js** - Interactive charts for vitals trends
- **Matplotlib** - Data visualization
- **ReportLab** - PDF report generation

### Frontend
- **HTML5/CSS3** - Modern, responsive UI
- **JavaScript** - Interactive dashboard and charts
- **Material Icons** - Icon library

## 📁 Project Structure

```
heal.io/
├── app.py                 # Main Flask application with all routes
├── models.py              # SQLAlchemy database models
├── healio_model.py        # Quantum Deep Learning model implementation
├── requirements.txt       # Python dependencies
├── README.md              # This file
│
├── instance/
│   └── healio.db          # SQLite database (created automatically)
│
├── templates/             # Jinja2 HTML templates
│   ├── layout.html        # Base template
│   ├── login.html         # Login page
│   ├── register.html      # Registration page
│   ├── patient/           # Patient-specific templates
│   │   ├── dashboard.html
│   │   ├── vitals.html    # Vitals upload and visualization
│   │   ├── anomalies.html
│   │   └── doctors.html
│   └── doctor/            # Doctor-specific templates
│       ├── dashboard.html
│       ├── patients.html
│       ├── patient_detail.html
│       └── cases.html
│
├── static/                 # Static files
│   ├── css/
│   │   └── style.css      # Custom styles
│   └── js/                # JavaScript files
│
└── research&dl/           # Research and development materials
    ├── Quantum_Healio.ipynb    # Quantum model research notebook
    ├── comparison.ipynb        # Model comparison analysis
    ├── circuit.png             # Quantum circuit diagram
    ├── code.cpp                # Hardware implementation code
    ├── watch.png               # Smartwatch design image
    └── Screenshot*.png         # Additional research screenshots
```

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Clone the Repository

```bash
git clone https://github.com/CHAITU2405/Heal.io.git
cd Heal.io
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: The installation may take several minutes as it includes TensorFlow and PennyLane, which are large packages.

### Step 4: Initialize Database

The database will be created automatically on first run. To manually initialize:

```python
from app import app, db
with app.app_context():
    db.create_all()
```

### Step 5: Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## 📖 Usage

### Initial Setup

1. **Register an Account**
   - Navigate to `/register`
   - Choose account type: Patient or Doctor
   - Fill in required information
   - Create your account

2. **Login**
   - Go to `/login`
   - Enter your email and password
   - You'll be redirected to your dashboard based on account type

### For Patients

#### Upload Vitals CSV

1. Navigate to **Vitals** page (`/patient/vitals`)
2. Click **"Upload Vitals CSV for Quantum DL Analysis"**
3. Select a CSV file with your vital signs data
4. Click **"Upload & Run Quantum DL Prediction"**
5. View prediction results including:
   - Alert status (NORMAL, EARLY WARNING, HIGH RISK)
   - Quantum Anomaly Score
   - Classical Anomaly Score
   - Disease Risk Probabilities (Cardiovascular, Respiratory, Metabolic, Neurological)

#### View Vitals Trends

1. On the Vitals page, use the dropdown to select:
   - **Heart Rate (BPM)**
   - **Oxygen Saturation (SpO2)**
2. Use date filters to view specific time ranges
3. Charts update automatically based on your data

#### Connect with Doctors

1. Go to **Doctors** page (`/patient/doctors`)
2. Browse available doctors
3. Send connection requests
4. Once accepted, doctors can view your health data

#### View Anomalies

1. Navigate to **Anomalies** page (`/patient/anomalies`)
2. Review detected anomalies
3. Assign anomalies to connected doctors
4. Track case status

### For Doctors

#### View Patients

1. Go to **Patients** page (`/doctor/patients`)
2. View all connected patients
3. Click on a patient to view detailed information

#### Review Patient Details

1. Select a patient from the patients list
2. View:
   - Current vitals
   - Vitals history and trends
   - Detected anomalies
   - Health alerts

#### Manage Cases

1. Go to **Cases** page (`/doctor/cases`)
2. Review assigned anomalies
3. Update case status
4. Transfer cases to other doctors if needed

## 🧠 Quantum Deep Learning Model

### Architecture

The Heal.io model uses a **hybrid quantum-classical deep learning** approach:

1. **Data Preprocessing**
   - MinMaxScaler: Normalizes vital signals to [0, 1] range
   - Handles 5 input features: Heart Rate, Systolic BP, Diastolic BP, SpO2, Sleep State

2. **Temporal Embedding (BiLSTM-like)**
   - Dense layers (64 → 128 units)
   - GlobalAveragePooling1D for temporal aggregation
   - Output: 128-dimensional embedding vector

3. **Quantum Compression**
   - PCA: Reduces 128D embedding to 4 qubits
   - Angle Scaler: Maps to [0, π] for quantum gates

4. **Quantum Anomaly Detection**
   - Quantum Distance Function using PennyLane
   - AngleEmbedding for quantum state preparation
   - Compares against baseline normal patterns
   - Threshold: 97th percentile of training scores

5. **Classical Anomaly Detection**
   - Isolation Forest (300 estimators, 5% contamination)
   - Threshold: 95th percentile

6. **Multi-Disease Risk Prediction**
   - Neural network: 128 → 64 → 32 → 4
   - Outputs probabilities for:
     - Cardiovascular risk
     - Respiratory risk
     - Metabolic risk
     - Neurological risk

### Model Configuration

```python
timesteps = 60          # 60 data points (1 hour at 1-minute intervals)
n_features = 5          # Heart Rate, SBP, DBP, SpO2, Sleep State
embedding_dim = 128     # BiLSTM embedding dimension
n_qubits = 4            # Quantum circuit qubits
```

### Prediction Output

```json
{
  "alert": "NORMAL" | "EARLY WARNING" | "HIGH RISK",
  "quantum_score": 0.1234,
  "classical_score": -0.0456,
  "risks": {
    "cardio": 0.45,
    "respiratory": 0.32,
    "metabolic": 0.28,
    "neurological": 0.19
  }
}
```

### Decision Logic

- **HIGH RISK**: Both quantum and classical anomalies detected
- **EARLY WARNING**: Only quantum anomaly detected
- **NORMAL**: No anomalies detected

## 📄 CSV Format

### Required Columns

The model requires **5 core features** for prediction:

| Column Name | Alternatives | Description | Example |
|------------|--------------|------------|---------|
| Heart Rate | `heart_rate`, `hr`, `heart rate`, `pulse`, `bpm` | Beats per minute | 72 |
| Systolic BP | `blood_pressure_systolic`, `sbp`, `systolic`, `systolic_bp` | mmHg | 120 |
| Diastolic BP | `blood_pressure_diastolic`, `dbp`, `diastolic`, `diastolic_bp` | mmHg | 80 |
| Oxygen Saturation | `oxygen_saturation`, `spo2`, `sp_o2`, `oxygen`, `o2_sat` | Percentage | 98 |
| Sleep Hours | `sleep_hours`, `sleep`, `sleep hours`, `sleep_time` | Hours | 7.5 |

### Optional Columns (Stored in Database)

These columns are saved but not used for model prediction:

- `respiratory_rate` or `rr` - Respiratory rate (breaths/min)
- `body_temperature` or `temp` - Body temperature (°F)
- `steps` - Step count
- `energy_level` - Energy level (text)

### CSV Requirements

- **Minimum Rows**: 60 rows recommended for optimal prediction
- **Format**: CSV (comma-separated values)
- **Encoding**: UTF-8
- **Headers**: First row should contain column names
- **Data Types**: Numeric values (integers or floats)

### Example CSV

```csv
heart_rate,sbp,dbp,spo2,sleep_hours,respiratory_rate,body_temperature,steps
72,120,80,98,7.5,16,98.6,5000
73,121,81,98,7.5,16,98.6,5100
71,119,79,97,7.4,15,98.5,4900
...
```

**Note**: Column names are case-insensitive and support various formats (spaces, underscores, hyphens).

## 🗄 Database Schema

### Users Table

Stores both patients and doctors.

```python
- id (Primary Key)
- email (Unique)
- password_hash
- first_name
- last_name
- user_type ('patient' or 'doctor')
- phone
- date_of_birth

# Doctor-specific fields
- license_number
- specialization
- persons_treated

# Patient-specific fields
- is_non_verbal
- emergency_contact_name
- emergency_contact_phone
```

### Vitals Table

Stores vital signs data.

```python
- id (Primary Key)
- patient_id (Foreign Key → Users)
- heart_rate
- blood_pressure_systolic
- blood_pressure_diastolic
- oxygen_saturation
- respiratory_rate
- body_temperature
- steps
- sleep_hours
- energy_level
- recorded_at (DateTime, Indexed)
```

### Anomalies Table

Stores detected health anomalies.

```python
- id (Primary Key)
- patient_id (Foreign Key → Users)
- assigned_doctor_id (Foreign Key → Users, Nullable)
- transferred_from_doctor_id (Foreign Key → Users, Nullable)
- anomaly_type
- severity ('low', 'medium', 'high', 'critical')
- description
- risk_score
- detected_at (DateTime, Indexed)
- assigned_at (DateTime, Nullable)
- case_status ('pending', 'assigned', 'completed', 'transferred')
```

### Alerts Table

Stores health alerts and notifications.

```python
- id (Primary Key)
- patient_id (Foreign Key → Users)
- alert_type
- message
- severity ('low', 'medium', 'high', 'critical')
- is_read (Boolean, Indexed)
- created_at (DateTime, Indexed)
```

### PatientDoctor Table

Manages patient-doctor relationships.

```python
- id (Primary Key)
- patient_id (Foreign Key → Users)
- doctor_id (Foreign Key → Users)
- status ('pending', 'accepted', 'rejected')
- accepted_at (DateTime, Nullable)
```

## 🔌 API Endpoints

### Authentication

- `GET /` - Home page (redirects based on login status)
- `GET /login` - Login page
- `POST /login` - Process login
- `GET /register` - Registration page
- `POST /register` - Process registration
- `GET /logout` - Logout user

### Patient Routes

- `GET /patient/dashboard` - Patient dashboard
- `GET /patient/vitals` - Vitals page with charts
- `POST /patient/upload-vitals-csv` - Upload CSV and run prediction
- `GET /patient/anomalies` - View anomalies
- `GET /patient/doctors` - Browse and connect with doctors
- `POST /patient/anomaly/<id>/assign-doctor/<doctor_id>` - Assign anomaly to doctor

### Doctor Routes

- `GET /doctor/dashboard` - Doctor dashboard
- `GET /doctor/patients` - View connected patients
- `GET /doctor/patient/<patient_id>` - View patient details
- `GET /doctor/cases` - View assigned cases
- `POST /doctor/case/<case_id>/update-status` - Update case status
- `POST /doctor/case/<case_id>/transfer/<doctor_id>` - Transfer case

## 🧪 Model Testing

To test the model directly:

```python
from healio_model import healio_predict, predict_from_csv
import numpy as np
import pandas as pd

# Test with numpy array
test_data = np.random.normal(
    loc=[72, 45, 98, 0.19, 0.42],  # Normal values
    scale=[2, 2, 0.4, 0.015, 0.04],
    size=(60, 5)  # 60 timesteps, 5 features
)
result = healio_predict(test_data)
print(result)

# Test with CSV data
df = pd.read_csv('your_vitals.csv')
result = predict_from_csv(df)
print(result)
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file (optional):

```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///instance/healio.db
FLASK_ENV=development
```

### Model Parameters

Edit `healio_model.py` to adjust:

- `timesteps`: Number of data points (default: 60)
- `n_features`: Number of input features (default: 5)
- `embedding_dim`: Embedding dimension (default: 128)
- `n_qubits`: Quantum qubits (default: 4)

## 🐛 Troubleshooting

### Model Import Issues

If you encounter import errors:

```bash
# Ensure all dependencies are installed
pip install --upgrade -r requirements.txt

# Verify PennyLane installation
python -c "import pennylane as qml; print(qml.__version__)"
```

### Database Issues

To reset the database:

```python
from app import app, db
with app.app_context():
    db.drop_all()
    db.create_all()
```

### CSV Upload Issues

- Ensure CSV has proper headers
- Check column names match supported formats
- Verify data types are numeric
- Minimum 60 rows recommended

## 📊 Performance

- **Model Training**: ~13-15 seconds on first import (lazy loading)
- **Prediction Time**: ~2-3 seconds per CSV upload
- **Database**: SQLite (suitable for development, use PostgreSQL for production)

## 🔒 Security

- Password hashing using Werkzeug
- Session-based authentication
- Role-based access control
- SQL injection protection via SQLAlchemy ORM

## 🚧 Future Enhancements

- [ ] Real-time WebSocket connections for live vitals streaming
- [ ] Mobile app integration
- [ ] Advanced analytics and reporting
- [ ] Multi-language support
- [ ] Integration with wearable device APIs
- [ ] Cloud deployment configuration
- [ ] PostgreSQL support for production
- [ ] API rate limiting
- [ ] Email notifications

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add comments for complex logic
- Update README.md for new features
- Test your changes thoroughly

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Authors

- **Project Team** - Initial work

## 🙏 Acknowledgments

- PennyLane team for quantum computing framework
- TensorFlow team for deep learning capabilities
- Flask community for excellent documentation

## 📞 Support

For issues, questions, or contributions, please open an issue on [GitHub](https://github.com/CHAITU2405/Heal.io/issues).

## 🔗 Repository

[GitHub Repository](https://github.com/CHAITU2405/Heal.io)

---

**Built with ❤️ for better healthcare accessibility**
