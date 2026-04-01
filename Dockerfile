FROM python:3.11-slim

# Prevent Python from writing pyc files and buffer logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_DEBUG=False \
    FLASK_ENV=production \
    PORT=5000

# Set working directory to the admin system app
WORKDIR /app/admin_system

# Create unprivileged runtime user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Install Python dependencies first (better layer caching)
COPY admin_system/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY admin_system/ ./

# Ensure app files are owned by non-root user
RUN chown -R appuser:appgroup /app

# Drop privileges
USER appuser

# Expose Flask/Gunicorn port
EXPOSE 5000

# Run with Gunicorn in production mode
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} --workers ${GUNICORN_WORKERS:-2} --threads ${GUNICORN_THREADS:-4} --timeout ${GUNICORN_TIMEOUT:-120} --access-logfile - --error-logfile - app:app"]
