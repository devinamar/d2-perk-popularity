# The app's image: Python, the pinned packages and the code. `docker build .`
# (or compose.yaml) builds it, and `docker build --target test .` runs the
# tests in it.

# The base is a tag, so a build with --pull takes its
# latest patch release; pin a digest (python:3.13-slim@sha256:...) to freeze it.
FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
# The packages first: this layer is reused until requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir --disable-pip-version-check --root-user-action=ignore \
    -r requirements.txt
COPY . .

# The tests, run in the image as built; a failure fails the build.
FROM base AS test
RUN pip install --no-cache-dir --disable-pip-version-check --root-user-action=ignore pytest \
    && python -m pytest -q -p no:cacheprovider

# What runs, the default target: the scheduler, as an unprivileged user (uid 568).
FROM base AS app
USER 568:568
CMD ["python", "service.py"]
