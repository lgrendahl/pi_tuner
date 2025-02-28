# Project Setup Instructions

---

## 1. Install Python 3.11

```bash
# Update packages
sudo apt-get update
sudo apt-get upgrade -y

# Install prerequisites for PPAs
sudo apt-get install -y software-properties-common

# Add the deadsnakes PPA and update again
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update

# Install Python 3.11, plus venv & distutils
sudo apt-get install -y python3.11 python3.11-venv python3.11-distutils
```

## 2. Create a New Virtual Environment

```bash
# Create a hidden directory for storing virtual environments
mkdir -p ~/.virtualenvs

# Create a virtual environment
python3.11 -m venv ~/.virtualenvs/pi_tuner
```

## 3. Clone this Project

```bash
# Optional: go to a workspace folder
mkdir -p ~/projects && cd ~/projects

# Clone the GitHub repository
git clone https://github.com/lgrendahl/pi_tuner.git
```

## 4. Install Requirements

```bash
# Activate the virtual environment
source ~/.virtualenvs/pi_tuner/bin/activate

# Make sure we're in the newly cloned project directory
cd ~/projects/pi_tuner

# Set up and update pip
pip install --upgrade pip setuptools wheel

# Now install the project's dependencies
pip install -r requirements.txt
```