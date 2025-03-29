# http tester for service mesh

# build
docker build -t http-tester .
# run local
docker run -p 5000:5000 http-tester

# publish
docker login
docker tag http-tester wlanboy/http-tester:latest
docker push wlanboy/http-tester:latest

# run
docker run -d -p 5000:5000 wlanboy/http-tester

# deploy
kubectl create namespace demo
kubectl label namespace demo istio-injection=enabled
kubectl create deployment tester --image=wlanboy/http-tester:latest -n demo
kubectl expose deployment tester --type=ClusterIP --port=5000 -n demo
kubectl set image deployment/tester 'wlanboy/http-tester:latest' -n demo

# curl
curl -X POST -d "url=http://helloworld.sample.svc:5000/hello" tester.demo.svc:5000
