FROM python:3.10-slim

# Prevent python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/code

WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt pyproject.toml /code/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create temporary storage directory with required permissions
RUN mkdir -p /tmp/vkr_storage && chmod 777 /tmp/vkr_storage

# Copy alembic migrations and config
COPY alembic.ini /code/alembic.ini
COPY alembic /code/alembic

# Copy application source code
COPY app /code/app

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
