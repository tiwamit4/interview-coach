FROM python:3.12-slim AS backend-base

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home app \
    && mkdir -p /app/data /app/upload \
    && chown -R app:app /app

COPY --chown=app:app backend ./backend
USER app

FROM backend-base AS streamlit
USER root
COPY frontend/requirements.txt ./frontend/requirements.txt
RUN pip install --no-cache-dir -r frontend/requirements.txt
COPY --chown=app:app frontend/__init__.py ./frontend/__init__.py
COPY --chown=app:app frontend/streamlit_ui ./frontend/streamlit_ui
COPY --chown=app:app streamlit_app.py ./streamlit_app.py
USER app
EXPOSE 8501
CMD ["python", "-m", "streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", "--browser.gatherUsageStats=false"]

FROM backend-base AS api
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
