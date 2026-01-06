"""
Heal.io Quantum Deep Learning Model
Final implementation - exact code as provided
"""
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense, GlobalAveragePooling1D
import pennylane as qml

# =====================================================
# CONFIG
# =====================================================
timesteps = 60
n_features = 5
embedding_dim = 128
n_qubits = 4

# =====================================================
# 1️⃣ SCALER (VITAL NORMALIZATION)
# =====================================================
scaler = MinMaxScaler()

# =====================================================
# 2️⃣ EMBEDDING MODEL (Temporal Encoder)
# =====================================================
inputs = Input(shape=(timesteps, n_features))
x = Dense(64, activation="relu")(inputs)
x = Dense(embedding_dim, activation="relu")(x)
x = GlobalAveragePooling1D()(x)
bilstm_model = Model(inputs, x)

# =====================================================
# 3️⃣ PCA FOR QUANTUM COMPRESSION
# =====================================================
pca = PCA(n_components=n_qubits)

# =====================================================
# 4️⃣ QUANTUM DISTANCE FUNCTION
# =====================================================
dev = qml.device("default.qubit", wires=n_qubits)

def quantum_distance(x1, x2):
    @qml.qnode(dev)
    def circuit():
        qml.AngleEmbedding(x1, wires=range(n_qubits))
        qml.adjoint(qml.AngleEmbedding)(x2, wires=range(n_qubits))
        return qml.expval(qml.Projector([0]*n_qubits, wires=range(n_qubits)))
    return 1 - circuit()

# =====================================================
# 5️⃣ CLASSICAL ANOMALY MODEL
# =====================================================
iso_model = IsolationForest(
    n_estimators=300,
    contamination=0.05,
    random_state=42
)

# =====================================================
# 6️⃣ MULTI-DISEASE RISK MODEL
# =====================================================
risk_in = Input(shape=(embedding_dim,))
r = Dense(64, activation="relu")(risk_in)
r = Dense(32, activation="relu")(r)
risk_out = Dense(4, activation="sigmoid")(r)

risk_model = Model(risk_in, risk_out)
risk_model.compile(optimizer="adam", loss="mse")

# =====================================================
# 7️⃣ BASELINE TRAINING (NORMAL DATA ONLY)
# =====================================================
normal_train = np.random.normal(
    loc=[72, 45, 98, 0.19, 0.42],
    scale=[3, 3, 0.5, 0.02, 0.05],
    size=(300, timesteps, n_features)
)

# --- Vital scaling
normal_flat = normal_train.reshape(-1, n_features)
scaler.fit(normal_flat)
normal_scaled = scaler.transform(normal_flat).reshape(300, timesteps, n_features)

# --- Embeddings
embeddings = bilstm_model.predict(normal_scaled, verbose=0)

# --- PCA
pca.fit(embeddings)
emb_q = pca.transform(embeddings)

# =====================================================
# 🔧 QUANTUM ANGLE CALIBRATION (CRITICAL FIX)
# =====================================================
angle_scaler = MinMaxScaler(feature_range=(0, np.pi))
emb_q_angles = angle_scaler.fit_transform(emb_q)

baseline_mean = emb_q_angles.mean(axis=0)

quantum_scores_train = np.array([
    quantum_distance(e, baseline_mean) for e in emb_q_angles
])

quantum_threshold = np.percentile(quantum_scores_train, 97)

# =====================================================
# CLASSICAL CALIBRATION
# =====================================================
iso_model.fit(embeddings)
classical_scores = -iso_model.decision_function(embeddings)
classical_threshold = np.percentile(classical_scores, 95)

# =====================================================
# RISK MODEL TRAINING
# =====================================================
risk_targets = np.random.rand(300, 4)
risk_model.fit(embeddings, risk_targets, epochs=5, verbose=0)

# =====================================================
# 8️⃣ FINAL HEALIO PREDICTION FUNCTION
# =====================================================
def healio_predict(vitals_window):
    vitals_scaled = scaler.transform(vitals_window)
    X = vitals_scaled[np.newaxis, ...]

    embedding = bilstm_model.predict(X, verbose=0)[0]

    # --- Quantum
    emb_q = pca.transform(embedding.reshape(1, -1))
    emb_q = angle_scaler.transform(emb_q)[0]

    q_score = quantum_distance(emb_q, baseline_mean)
    quantum_anomaly = q_score > quantum_threshold

    # --- Classical
    trad_score = -iso_model.decision_function(
        embedding.reshape(1, -1)
    )[0]
    classical_anomaly = trad_score > classical_threshold

    # --- Risk
    risks = risk_model.predict(
        embedding.reshape(1, -1), verbose=0
    )[0]

    # --- Decision Logic
    if quantum_anomaly and classical_anomaly:
        alert = "HIGH RISK"
    elif quantum_anomaly:
        alert = "EARLY WARNING"
    else:
        alert = "NORMAL"

    return {
        "alert": alert,
        "quantum_score": float(q_score),
        "classical_score": float(trad_score),
        "risks": {
            "cardio": float(risks[0]),
            "respiratory": float(risks[1]),
            "metabolic": float(risks[2]),
            "neurological": float(risks[3])
        }
    }

# =====================================================
# 9️⃣ CSV PREDICTION FUNCTION (for Flask integration)
# =====================================================
def predict_from_csv(csv_data, window_size=timesteps):
    """
    Predict disease risk from CSV data - wrapper for CSV upload integration
    
    Args:
        csv_data: numpy array of shape (n_samples, n_features) or pandas DataFrame
                 Expected features: heart_rate, sbp, dbp, spo2, sleep_state
        window_size: Number of timesteps to use for prediction (default: 60)
    
    Returns:
        Dictionary with prediction results
    """
    # Convert to numpy array if needed
    if hasattr(csv_data, 'values'):
        csv_data = csv_data.values
    
    # Ensure we have the right shape
    if len(csv_data.shape) == 1:
        csv_data = csv_data.reshape(1, -1)
    
    # Check if we have enough data
    if csv_data.shape[0] < window_size:
        # Pad with last value or repeat
        last_row = csv_data[-1:]
        padding = np.tile(last_row, (window_size - csv_data.shape[0], 1))
        csv_data = np.vstack([csv_data, padding])
    elif csv_data.shape[0] > window_size:
        # Take the last window_size rows
        csv_data = csv_data[-window_size:]
    
    # Ensure we have 5 features
    if csv_data.shape[1] < n_features:
        # Pad with zeros or default values
        padding = np.zeros((csv_data.shape[0], n_features - csv_data.shape[1]))
        csv_data = np.hstack([csv_data, padding])
    elif csv_data.shape[1] > n_features:
        # Take first 5 features
        csv_data = csv_data[:, :n_features]
    
    # Call the main prediction function
    return healio_predict(csv_data)
