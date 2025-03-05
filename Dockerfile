# Use a more feature-rich Python base image from Docker Hub
FROM python:3.13.1-bookworm

# 1) Create a non-root user/group with UID=1000 and GID=1000
RUN groupadd --gid 1000 obd-user && \
    useradd --uid 1000 --gid 1000 --create-home obd-user

# 2) Set the working directory
WORKDIR /app

# 3) Install required system packages (including distutils for building)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cargo \
    libmariadb-dev \
    python3-distutils \
    python3-setuptools \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# 4) Copy ONLY the requirements file first (for efficient caching)
COPY requirements.txt /app/requirements.txt

# 5) Upgrade pip (optional, but recommended) and install dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6) Switch to non-root obd-user
USER obd-user

# 7) Expose the Flask port (if your Flask app runs on port 1337)
EXPOSE 1337

# 8) By default, run your Flask app (the main code can be mounted at runtime)
CMD ["python", "run.py"]