# Use the official Python image as the base
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the application files to the container
COPY server.py /app/

# Copy Init script
COPY init.sh /usr/local/bin/start.sh

# Install dependencies
RUN pip install flask requests

# Expose the port the app runs on
EXPOSE 5000

# Command to run the Flask app
#CMD ["python", "server.py"]
CMD ["/usr/local/bin/init.sh"]
