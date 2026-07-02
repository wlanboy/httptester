# http tester for service mesh

A simple web ui to run http get und nslookup request inside of the cluster.
Perfect to check availability of services, dns entries and hostnames from a pod point of view.

Der `http-tester` läuft als eigener Pod im Mesh und bietet drei Kernfunktionen:

* **GET-Requests absetzen** – beliebige URL vom Pod aus aufrufen und Response-Body sowie -Header sehen. Damit lässt sich prüfen, ob ein Service über Ingress-Gateway, Egress-Gateway oder East-West-Gateway erreichbar ist, ob mTLS/AuthorizationPolicies greifen und wie mesh-interne Antworten aussehen.
* **DNS-Auflösung** – Hostnamen per `nslookup`-Äquivalent aus Pod-Sicht auflösen, um Kubernetes-DNS, ServiceEntries und externe Namensauflösung (z. B. für Egress) zu verifizieren.
* **JSON-Echo** (`/postbody`) – zum Testen von Payload-Weiterleitung, Content-Type-Handling und Proxy-Verhalten (z. B. Header-Manipulation durch EnvoyFilter).

Da alles über eine einfache Web-UI und Swagger (`/docs`) bedienbar ist, braucht man
keinen eigenen `curl`/`dig` im Debug-Container – der Pod selbst ist das Werkzeug.
Typische Einsatzszenarien: Erreichbarkeit von Services vor/nach einem Rollout prüfen,
Istio Ingress-/Egress-/East-West-Gateways verifizieren, oder schnell aus einem
bestimmten Namespace heraus testen, ob eine Zielresource überhaupt sichtbar ist.

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

## lint & type check

```bash
uv run ruff check .
uv run pyright .
```

## endpoints

| Method | Path         | Beschreibung                                          |
|--------|--------------|--------------------------------------------------------|
| GET    | `/`          | HTML-Formular                                          |
| POST   | `/`          | Request gegen `url` (Methode, Timeout, Header konfigurierbar) |
| POST   | `/resolve`   | Löst einen `hostname` per DNS auf                      |
| POST   | `/postbody`  | Echoed einen JSON-Body zurück (`message`, `value`)     |
| GET    | `/healthz`   | Liveness-/Readiness-Check, liefert `{"status": "ok"}`  |
| POST   | `/chain`     | JSON-API: ruft `chain[0]` auf, reicht den Rest weiter und liefert `final_status` + `path` (Hops mit Status/Dauer/Fehler) |
| POST   | `/chain-form`| HTML-Formular-Variante von `/chain` (Tab "Chain" in der UI) |
| GET    | `/docs`      | Swagger UI                                             |

## build

```bash
docker build -t http-tester .
```

Das Image läuft als non-root User (`appuser`, uid 1000) und beendet sich bei
`SIGTERM` sauber über den FastAPI-Shutdown-Event (wichtig für schnelle
Rolling-Updates/Restarts in Kubernetes).

## run local

```bash
docker run -p 5000:5000 http-tester
```

## run as daemon

```bash
docker run -d -p 5000:5000 wlanboy/http-tester
```

## deploy

### kubectl (imperativ)

```bash
kubectl create namespace demo
kubectl label namespace demo istio-injection=enabled
kubectl create deployment tester --image=wlanboy/http-tester:latest -n demo
kubectl expose deployment tester --type=ClusterIP --port=5000 -n demo
kubectl set image deployment/tester 'wlanboy/http-tester:latest' -n demo
```

### Helm chart

Das Chart in [`tester-chart`](tester-chart) deployt `Deployment` + `Service`
mit Liveness-/Readiness-Probes auf `/healthz` sowie optional (per
`ingress.enabled`) ein Istio `Gateway`/`VirtualService`. `deploymentName` und
`namespace` sind vollständig parametrisiert, das Chart lässt sich also
mehrfach mit unterschiedlichem Release-Namen installieren – z. B. um mehrere
Instanzen für einen Chain-Test aufzusetzen.

```bash
kubectl create namespace tester
kubectl label namespace tester istio-injection=enabled --overwrite
helm upgrade --install tester ./tester-chart \
  --namespace tester
```

### Drei Instanzen in drei Namespaces (Chain-Setup)

Um die Chain-Funktion (`/chain`) über mehrere Namespaces/Meshes hinweg zu
testen, wird derselbe Chart dreimal installiert – einmal pro Namespace, mit
eigenem `deploymentName`. Nur die erste Instanz braucht ein Gateway als
Eingang von außen, die anderen beiden sind rein mesh-intern erreichbar:

```bash
kubectl create namespace ns1
kubectl label namespace ns1 istio-injection=enabled --overwrite
helm upgrade --install tester1 ./tester-chart \
  --namespace ns1 \
  --set deploymentName=tester1 --set namespace=ns1

kubectl create namespace ns2
kubectl label namespace ns2 istio-injection=enabled --overwrite
helm upgrade --install tester2 ./tester-chart \
  --namespace ns2 \
  --set deploymentName=tester2 --set namespace=ns2 \
  --set ingress.enabled=false

kubectl create namespace ns3
kubectl label namespace ns3 istio-injection=enabled --overwrite
helm upgrade --install tester3 ./tester-chart \
  --namespace ns3 \
  --set deploymentName=tester3 --set namespace=ns3 \
  --set ingress.enabled=false
```

Damit ergibt sich folgende Kette:

```
Browser/curl → httptester.tp.lan (Gateway ns1)
                  │
                  ▼
            tester1.ns1.svc.cluster.local
                  │  POST /chain { chain: [tester2, tester3] }
                  ▼
            tester2.ns2.svc.cluster.local
                  │  POST /chain { chain: [tester3] }
                  ▼
            tester3.ns3.svc.cluster.local   (Endstation, chain: [])
```

Aufruf gegen `tester1` über das Istio Gateway von außen:

```bash
curl -s -X POST http://httptester.gmk.lan/chain \
  -H "Content-Type: application/json" \
  -d '{
        "message": "hallo aus der kette",
        "chain": [
          "http://tester2.ns2.svc.cluster.local:5000",
          "http://tester3.ns3.svc.cluster.local:5000"
        ]
      }'
```

oder cluster-intern direkt gegen `tester1`:

```bash
curl -s -X POST http://tester1.ns1.svc.cluster.local:5000/chain \
  -H "Content-Type: application/json" \
  -d '{
        "message": "hallo aus der kette",
        "chain": [
          "http://tester2.ns2.svc.cluster.local:5000",
          "http://tester3.ns3.svc.cluster.local:5000"
        ]
      }'
```

oder über den Tab "Chain" in der Web-UI von `tester1` (eine URL pro Zeile:
`http://tester2.ns2.svc.cluster.local:5000` und
`http://tester3.ns3.svc.cluster.local:5000`). Die Antwort enthält
`final_status` sowie den vollständigen `path` mit jedem Hop (Ziel, HTTP-Status,
Dauer in ms, ggf. Fehlermeldung) – so lässt sich genau sehen, an welcher
Namespace-Grenze eine AuthorizationPolicy, NetworkPolicy oder ein fehlendes
`ServiceEntry` die Kette unterbricht.

## test calls

Use swagger ui: http://localhost:5000/docs
![Swagger UI](screenshots/swagger.png)
