# Use an official lightweight Python image from Docker Hub
FROM python:3.13.1-bookworm

# 1) Create a non-root user with UID=1000 and GID=1000
RUN groupadd --gid 1000 obd-user && \
    useradd --uid 1000 --gid 1000 --create-home obd-user

# 2) Set the working directory
WORKDIR /app

# 3) Install required system packages
RUN apt-get update && apt-get install -y \
    build-essential \
    cargo \
    libmariadb-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 4) Copy ONLY the requirements, so we can install dependencies
COPY requirements.txt /app/requirements.txt

# 5) Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 6) Switch to non-root obd-user user
USER obd-user

# 7) Expose the Flask port
EXPOSE 1337

# 8) By default, run your Flask app (the code itself will be mounted at runtime)
CMD ["python", "run.py"]