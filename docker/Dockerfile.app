FROM python:3.14-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS build
ARG POETRY_VERSION=2.2.1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1
WORKDIR /app
RUN python -m pip install --no-cache-dir "poetry==${POETRY_VERSION}"
COPY pyproject.toml poetry.lock poetry.toml ./
RUN poetry install --only main --no-root

FROM python:3.14-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    FAROL_CONTAINER=1 FAROL_DATA_DIR=/app/data
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 farol \
    && useradd --uid 1000 --gid 1000 --create-home farol \
    && mkdir -p /app/data && chown 1000:1000 /app/data
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY --chown=1000:1000 poc ./poc
COPY --chown=1000:1000 static ./static
COPY --chown=1000:1000 run.py ./
COPY --chown=1000:1000 ["Cadastro de Inadimplentes.pdf", "./Cadastro de Inadimplentes.pdf"]
USER 1000:1000
EXPOSE 5000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s \
  CMD ["/app/.venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health',timeout=3).read()"]
CMD ["/app/.venv/bin/python", "run.py"]
