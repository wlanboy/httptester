FROM python:3.9-slim-buster

WORKDIR /app
COPY client.py .
COPY eureka_client_lib.py .
COPY services.json .

RUN pip install --no-cache-dir requests

CMD ["python", "client.py"]

EXPOSE 8080
EXPOSE 8443
