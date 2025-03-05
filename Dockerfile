# Use Python 3.11 instead of 3.13
FROM python:3.11-bookworm

# 1) Create a non-root user with UID=1000 and GID=1000
RUN groupadd --gid 1000 obd-user && \
    useradd --uid 1000 --gid 1000 --create-home obd-user

# 2) Set the working directory
WORKDIR /app

# 3) Install required system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cargo \
    libmariadb-dev \
    python3-distutils \
    python3-setuptools \
    python3-wheel \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# 4) Copy ONLY the requirements first
COPY requirements.txt /app/requirements.txt

# 5) Upgrade pip/setuptools/wheel, then install dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# 6) Switch to non-root user
USER obd-user

# 7) Expose the Flask port (example: 1337)
EXPOSE 1337

# 8) By default, run your Flask app (the code can be mounted at runtime)
CMD ["python", "run.py"]