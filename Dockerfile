FROM python:3.14-slim

WORKDIR /app

# Create the non-root user upfront so COPY can chown directly
RUN useradd --no-create-home --uid 1000 appuser

# Install dependencies before copying the code, so code changes reuse this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser server.py /app/
COPY --chown=appuser:appuser static/ static/

USER appuser

EXPOSE 5000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "5000"]
