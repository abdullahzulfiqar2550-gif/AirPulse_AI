# 1. Base Image: Lightweight Python 3.11
FROM python:3.11-slim

# 2. Set container working directory
WORKDIR /app

# 3. Cache layer optimization: Copy requirements first
COPY requirements.txt .

# 4. Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy application code and model artifacts
COPY src/ ./src/
COPY models/ ./models/

# 6. Expose default Streamlit port
EXPOSE 8501

# 7. Configure Streamlit environment
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true

# 8. Start the Streamlit application
ENTRYPOINT ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0"]