FROM python:3.11

# Install system dependencies
RUN \
  set -eux; \
  apt-get update; \
  DEBIAN_FRONTEND="noninteractive" apt-get install -y --no-install-recommends \
  build-essential \
  python3-venv \
  ffmpeg \
  git \
  curl \
  ; \
  rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Ensure Poetry and Python binaries are in PATH
ENV PATH="/root/.local/bin:$PATH"

# Disable virtualenv creation from poetry to use the system python
ENV POETRY_VIRTUALENVS_CREATE=false

# Copy only pyproject.toml and poetry.lock to cache dependencies installation
COPY ./pyproject.toml ./poetry.lock* /app/

# Set the working directory in the container
WORKDIR /app

# Install dependencies
RUN poetry install --no-interaction --no-ansi

# Copy the application code
COPY ./src /app

CMD ["bash"]
