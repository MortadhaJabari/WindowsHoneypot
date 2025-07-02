FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for packages that need compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev libssl-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock* ./

# Install pip + uv and sync deps
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir uv \
    && uv sync

# Copy the rest of the project
COPY . .

# Expose ports
EXPOSE 2222 53/udp 2121 7000 8080 1445

# Set Python env var
ENV PYTHONUNBUFFERED=1

# Start app using uv
CMD ["uv", "run", "main.py"]
