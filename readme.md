# http tester for service mesh
A simple web ui to run http get und nslookup request inside of the cluster.
Perfect to check availability of services, dns entries and hostnames from a pod point of view.
Used to test Istio Gateway, from Ingress to Eastwest service meshes.

## subprojects
* /eurekaclient - a server that reads a configlist of services and publishes them with their istio gateway vip to eureka
* /accesslogs - a server which is replacing any service and just logs the accesslogs to have a tool to find users of a depricated api
* /kind - a simple script based, step by step setup, for dual kind clusters with metallb to create a Istio based service mesh based on vips.

And the build steps for the http tester itself:
## get uv - makes python life easier
```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## run
```
uv sync
uv run main.py
```

### from scratch
- cd httptester
- uv sync
- uv pip compile pyproject.toml -o requirements.txt
- uv pip install -r requirements.txt
- uv run main.pys

## build
```
docker build -t http-tester .
```

## run local
```
docker run -p 5000:5000 http-tester
```

## publish
```
docker login
docker tag http-tester wlanboy/http-tester:latest
docker push wlanboy/http-tester:latest
```

## run
```
docker run -d -p 5000:5000 wlanboy/http-tester
```

## deploy
```
kubectl create namespace demo
kubectl label namespace demo istio-injection=enabled
kubectl create deployment tester --image=wlanboy/http-tester:latest -n demo
kubectl expose deployment tester --type=ClusterIP --port=5000 -n demo
kubectl set image deployment/tester 'wlanboy/http-tester:latest' -n demo
```

## curl
```
curl -X POST -d "url=http://helloworld.sample.svc:5000/hello" tester.demo.svc:5000
```
