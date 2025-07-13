# Simple example of external service
is running on the host gmk on port 5000

## start container on gmk.local machine
```
podman run -d --name http-tester -p 5000:5000 wlanboy/http-tester
```

## namespace
```
kubectl create namespace test
kubectl label namespace test istio-injection=enabled
```

## egress gateway
```
kubectl apply -f - <<EOF
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: gmk-egress-gateway
  namespace: test
spec:
  selector:
    istio: egressgateway
  servers:
  - port:
      number: 5000
      name: http
      protocol: HTTP
    hosts:
    - "*.gmk.local"
EOF
```

## ServiceEntry
```
kubectl apply -f - <<EOF
apiVersion: networking.istio.io/v1beta1
kind: ServiceEntry
metadata:
  name: external-gmk
  namespace: test
spec:
  hosts:
  - http.gmk.local
  addresses:
  - 192.168.178.91
  ports:
  - number: 5000
    name: http
    protocol: HTTP
  resolution: DNS
  location: MESH_EXTERNAL
EOF
```

## VirtualService
```
kubectl apply -f - <<EOF
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: direct-gmk-through-egress
  namespace: test
spec:
  hosts:
  - gmk
  gateways:
  - mesh
  - istio-system/egress-gateway
  http:
  - match:
    - gateways:
      - mesh
    route:
    - destination:
        host: http.gmk.local
        port:
          number: 5000
      weight: 100
  - match:
    - gateways:
      - istio-system/egress-gateway
    route:
    - destination:
        host: http.gmk.local
        port:
          number: 5000
      weight: 100
    headers:
      request:
        set:
          authority: http.gmk.local:5000 # Host-Header for gateway
EOF
```

## VirtualService
```
kubectl apply -f - <<EOF
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: egressgateway-for-gmk
  namespace: test
spec:
  host: http.gmk.local
  trafficPolicy:
    portLevelSettings:
    - port:
        number: 5000
      outlierDetection:
        consecutiveErrors: 3
        interval: 1m
        baseEjectionTime: 3m
        maxEjectionPercent: 100
  subsets:
  - name: gmk-egress
    trafficPolicy:
      loadBalancer:
        simple: ROUND_ROBIN
      connectionPool:
        tcp:
          maxConnections: 100
      outlierDetection:
        consecutiveErrors: 3
        interval: 1m
        baseEjectionTime: 3m
        maxEjectionPercent: 100
EOF
```

## deploy http tester
```
kubectl create deployment http-tester --image=wlanboy/http-tester --port=5000 -n test
kubectl expose deployment http-tester --port=80 --target-port=5000 --name=http-tester-service -n test

cat <<EOF | kubectl apply -f -
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: http-tester-gateway
  namespace: test
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "http.ser.local"
EOF

cat <<EOF | kubectl apply -f -
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: http-tester-virtualservice
  namespace: test
spec:
  hosts:
  - "http.ser.local"
  gateways:
  - http-tester-gateway
  http:
  - match:
    - uri:
        prefix: /
    route:
    - destination:
        host: http-tester-service
        port:
          number: 80
EOF
```

## call
- browser url: http://http.ser.local/
- type in the URL of service: http://http-tester-service.test.svc.cluster.local
- see the html form response
- see the logs of the container: podman logs http-tester

