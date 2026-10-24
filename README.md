# AirPulse AI: Pakistan PM2.5 Air Quality Monitoring and Forecasting Pipeline
AirPulse AI is an end-to-end data engineering and predictive machine learning system developed to address the seasonal smog and PM2.5 air pollution crisis across urban centers in Pakistan. The project integrates an automated ETL pipeline, relational database storage, exploratory data analysis, classical machine learning benchmarking, deep learning optimization with MLflow tracking, and an interactive real-time forecasting dashboard.
---
## Academic Group & Contributors
This project was developed as part of the academic curriculum for artificial intelligence and machine learning.
| Contributor Name | Roll Number | Role / Contribution Area |
| :--- | :--- | :--- |
| **Muhammad Abdullah** | **2025-AI-348** | Model Architecture, MLOps Tracking & Streamlit UI |
| **Muhammad Azan Faraz** | **2025-AI-341** | ETL Pipeline, OpenAQ API Ingestion & Validation |
| **Haseeb Ul Hassan** | **2025-AI-362** | Database Schema Design, MySQL Integration & EDA |
| **Anas Ilyas** | **2025-AI-364** | Feature Engineering, Time-Series Benchmark & Testing |
---
## Project Overview & Objectives
1. **Automated ETL Pipeline (Project 1):** Ingest historical and real-time hourly PM2.5 concentrations from the OpenAQ API v3 across 20 ground sensors in five major Pakistani cities (Lahore, Karachi, Islamabad, Peshawar, and Rawalpindi).
2. **Data Integrity & Relational Storage:** Validate schemas using Pydantic, sanitize outlier values (0–1000 µg/m³ threshold), and load clean transformed datasets into MySQL.
3. **Exploratory Data Analysis (EDA):** Analyze diurnal smog patterns, winter thermal inversions, rush hour traffic correlations, and sensor variances.
4. **Predictive Modeling (Project 2):** Benchmark multiple regression models using strictly temporal splits (TimeSeriesSplit) to forecast next-hour PM2.5 concentrations.
5. **Deep Learning & MLOps (Project 3):** Implement a PyTorch multi-layer perceptron (MLP), tune hyperparameters via Optuna (10 trials), and log experiments, metrics, and model artifacts using MLflow.
6. **Deployment & UI:** Deliver a real-time web dashboard using Streamlit and containerize the service using Docker and Docker Compose.
---
## System Architecture
```text
  [ OpenAQ API v3 ] (20 Sensors across 5 Cities)
          │
          ▼
  [ Data Ingestion & Validation ] (Pydantic & Pandas Range Checks)
          │
          ├─────────────────────────────────────────┐
          ▼                                         ▼
  [ MySQL Database: airpulseai ]          [ Processed CSV Dataset ]
          │                                         │
          ▼                                         ▼
  [ 8 Statistical EDA Visuals ]           [ Time-Series Feature Engineering ]
  (Diurnal, Seasonal Smog Spikes)         (Lags: 1h, 2h | Rolling Mean: 6h)
                                                    │
          ┌─────────────────────────────────────────┴───────────────────────┐
          ▼                                                                 ▼
  [ Project 2: Scikit-Learn Benchmark ]                   [ Project 3: PyTorch + MLOps ]
  • Ridge Regression                                      • 3-Layer PM25NeuralNet (MLP)
  • LinearSVR                                             • Optuna HPO (10 Trials)
  • Random Forest Regressor                               • MLflow Experiment Tracking
  • HistGradientBoosting (Winner: R²=0.9279)              • Model Artifact Logging
          │                                                                 │
          └─────────────────────────────────────────┬───────────────────────┘
                                                    │
                                                    ▼
                                  [ Streamlit Interactive Dashboard ]
                                  (DashMaster KPI Cards & Spline Curves)
                                                    │
                                                    ▼
                                  [ Containerization: Docker & Compose ]

  

  
Model Benchmark & Evaluation Results
All models were evaluated on the exact same held-out future test set using time-series validation to ensure zero lookahead data leakage.
  
Model Architecture Framework Hyperparameter Optimization Test R² Score	Test RMSE (µg/m³)	Status
HistGradientBoosting scikit-learn	RandomizedSearchCV	0.9279	23.94	Production Model (.joblib)
Random Forest	scikit-learn	100 Estimators	0.9248	24.45	Strong Tabular Baseline
Deep Neural Net (MLP)	PyTorch	Optuna (10 Trials)	0.9178	25.57	Logged to MLflow
Ridge Regression	scikit-learn	L2 Regularized (𝛼=1.0,	0.9150	26.00)	Linear Baseline
LinearSVR	scikit-learn	Epsilon-SVR	(0.9129	26.31)	Support Vector Baseline

Key Analytical Insight:
Tree-based ensemble models (HistGradientBoosting and Random Forest) performed slightly better on tabular time-series features than the neural network. This is consistent with empirical machine learning literature, as localized step-function splits capture non-linear lag thresholds effectively without requiring excessive network depth.

Repository Structure

text
AirPulse_AI/
├── models/
│   └── best_pm25_pipeline.joblib     # Serialized production pipeline
├── raw_data/                         # Raw ingested API data (gitignored)
├── src/
│   ├── 1.collect_data.py             # OpenAQ API ingestion script
│   ├── 2.validate_pakistan_data.py   # Pydantic schema validation
│   ├── 3.transform_pakistan_data.py  # Feature engineering & lag calculation
│   ├── 4.upload_to_sql.py            # MySQL database ingestion
│   ├── app.py                        # Streamlit dashboard application
│   └── ml_dl_optuna_mlflow.ipynb     # PyTorch, Optuna & MLflow training notebook
├── Dockerfile                        # Container build specification
├── docker-compose.yml                # Multi-service orchestration configuration
├── requirements.txt                  # Pinned environment dependencies
├── LICENSE                           # MIT License
└── README.md                         # Project documentation

Local Setup & Quickstart Guide
Prerequisites
Python 3.11 or higher
Git
(Optional) Docker and Docker Compose
1. Clone the Repository
bash
git clone https://github.com/abdullahzulfiqar2550-gif/AirPulse_AI.git
cd AirPulse_AI
2. Environment Setup
bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
pip install -r requirements.txt

3. Run the Interactive Streamlit Dashboard  
bash
streamlit run src/app.py
Open your browser and navigate to http://localhost:8501.

4. Run via Docker Compose (Optional)  
bash
docker compose up -d
Access the application at http://localhost:8501. To stop the container:

bash
docker compose down
 
License
This project is licensed under the MIT License - see the LICENSE file for details.
