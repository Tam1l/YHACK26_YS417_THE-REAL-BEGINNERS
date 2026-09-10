FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
COPY requirements-cpu.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu torch==2.7.1+cpu \
    && pip install --no-cache-dir -r requirements-cpu.txt \
    && pip install --no-cache-dir --no-deps ultralytics==8.4.146
COPY . .
EXPOSE 8000 8501
