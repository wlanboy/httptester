# Use the official Python image as the base
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Create the non-root user upfront so COPY can chown directly
RUN useradd --no-create-home --uid 1000 appuser

# Copy the application files to the container
COPY --chown=appuser:appuser server.py /app/
COPY --chown=appuser:appuser templates/index.html templates/index.html

# Copy Init script
#COPY init.sh /usr/local/bin/start.sh

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Run as a non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 5000

# Command to run the Flask app
#CMD ["python", "server.py"]
#CMD ["/usr/local/bin/init.sh"]
#./.venv/bin/waitress-serve --listen=0.0.0.0:5000 server:app
#CMD ["waitress-serve", "--listen=0.0.0.0:5000", "server:app"]
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "5000"]