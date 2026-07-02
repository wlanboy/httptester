# http tester for service mesh

A simple web ui to run http get und nslookup request inside of the cluster.
Perfect to check availability of services, dns entries and hostnames from a pod point of view.
Used to test Istio Gateway, from Ingress to Eastwest service meshes.

## get uv - makes python life easier

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## run

```bash
uv sync
.venv/bin/uvicorn server:app --reload --host 0.0.0.0 --port 5000
```

## from scratch

```bash
cd httptester
uv sync
uv pip compile pyproject.toml -o requirements.txt
uv pip install -r requirements.txt
.venv/bin/uvicorn server:app --reload --host 0.0.0.0 --port 5000
```

## run behave tests

```bash
.venv/bin/behave features/httptester.feature
```

## build

```bash
docker build -t http-tester .
```

## run local

```bash
docker run -p 5000:5000 http-tester
```

## run as daemon

```bash
docker run -d -p 5000:5000 wlanboy/http-tester
```

## deploy

```bash
kubectl create namespace demo
kubectl label namespace demo istio-injection=enabled
kubectl create deployment tester --image=wlanboy/http-tester:latest -n demo
kubectl expose deployment tester --type=ClusterIP --port=5000 -n demo
kubectl set image deployment/tester 'wlanboy/http-tester:latest' -n demo
```

## test calls

Use swagger ui: http://localhost:5000/docs
![Swagger UI](screenshots/swagger.png)
