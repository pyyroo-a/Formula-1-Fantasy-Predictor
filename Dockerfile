# Portable container for the PitWall FastAPI backend.
FROM python:3.13-slim

# libgomp1 is XGBoost's OpenMP runtime. Without it `import xgboost` fails on slim.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Run as a non-root user. Files must be owned by that user or the app can't
# write prices.json / locked_team.json / the FastF1 cache at runtime.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /home/user/app

# Requirements first so a code change doesn't reinstall the whole ML stack.
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY --chown=user . .

# FastF1 writes into data/cache; it starts empty here and warms on first use.
RUN mkdir -p data/cache data/processed

EXPOSE 8080

# Shell form so $PORT is expanded at runtime — Render injects its own port.
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
