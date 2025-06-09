# Eureka service registering all services in services.json
Goal of this project is a simple and small client to provide a migration path for everyone stuck with Spring Eureka.
The microservices that are your own responsibility should be freed from the burden of running a Eureka client that is no longer in use but is still needed for your customers. 
In a Cloud Native world, the microservices are hidden behind one or more load balancers. Therefore, we need a client that handles the registration of the microservices and uses the load balancer addresses as the destination url.

## pip dependencies
```
pip install requests
```

## simple client
- client.py running the registras
- eureka_client_lib.py request client for the eureka api

## client with metriks
- client_with_metrics.py running the registras and webserver for metrics endpoints
- eureka_client_lib.py request client for the eureka api
- metrics_exporter.py prometheus client publishing metrics about the registras

## run simple client
```
export EUREKA_SERVER_URL="http://gmk:8761/eureka/v2/apps/"
python3 client.py
```

## run client with metrics
```
export EUREKA_SERVER_URL="http://gmk:8761/eureka/v2/apps/" \
export METRICS_SERVER_HOST="192.168.1.100" \
export METRICS_SERVER_PORT="8080" \
python client_wm.py
```
