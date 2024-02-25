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
# This is useful when building Docker images to ensure system-wide availability
ENV POETRY_VIRTUALENVS_CREATE=false

# Copy only pyproject.toml and poetry.lock to cache dependencies installation
# Assuming pyproject.toml and poetry.lock are in the same directory as the Dockerfile
COPY ./pyproject.toml ./poetry.lock* /code/

# Set the working directory in the container
WORKDIR /code

# Install dependencies
# Note: You may want to add `--no-dev` if you don't need development dependencies in the final image
RUN poetry install --no-interaction --no-ansi

# Copy the rest of your application code
COPY . /code

CMD ["bash"]
