kubectl create namespace demo
kubectl label namespace demo istio-injection=enabled
kubectl create deployment tester --image=wlanboy/http-tester:latest -n demo
kubectl expose deployment tester --type=ClusterIP --port=5000 -n demo
kubectl set image deployment/tester 'wlanboy/http-tester:latest' -n demo

kubectl describe pod tester -n demo

kubectl label namespace demo istio-discovery=enabled
kubectl label namespace client istio-discovery=enabled

istioctl proxy-status

kubectl get all -n demo
kubectl describe svc tester -n demo
kubectl get svc istio-ingress -n istio-ingress

curl tester.demo.svc:5000
curl http.demo:5000
curl tester.local:5000
curl helloworld.sample.svc:5000/hello
curl -X POST -d "url=http://helloworld.sample.svc:5000/hello" tester.demo.svc:5000
curl -X POST -d "url=http://tester.local:5000/" tester.demo.svc:5000

istioctl proxy-status

cat <<EOF > workloadentry.yaml
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: tester-svc
spec:
  serviceAccount: clientserviceaccount
  address: 192.168.100.19
  labels:
    app: client
    instance-id: debian-client"
EOF

cat <<EOF > virtualvmservice.yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: tester-svc
spec:
  hosts:
  - tester.local
  location: MESH_INTERNAL
  ports:
  - number: 5000
    name: http
    protocol: HTTP
    targetPort: 5000
  resolution: DNS
  workloadSelector:
    labels:
      app: client"
EOF

kubectl label namespace client istio-injection=enabled
kubectl apply -f virtualvmservice.yaml -n client
kubectl describe serviceentry tester-svc -n client
kubectl delete serviceentry tester-svc -n client


kubectl apply -f workloadentry.yaml -n client
kubectl describe workloadentry tester-svc -n client
kubectl delete workloadentry tester-svc -n client
