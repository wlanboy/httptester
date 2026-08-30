# Helm Chart: tester

Helm Chart für das Deployment des `http-tester`-Services in Kubernetes. Der
Chart unterstützt wahlweise Istio (Standard) oder Traefik als Ingress-Weg,
gesteuert über den Schalter `ingress.controller`.

## Überblick

| Eigenschaft | Wert |
|---|---|
| Chart-Name | `tester` |
| Chart-Version | 0.1.0 |
| App-Version | `latest` |
| Typ | `application` |

## Komponenten

Das Chart rendert folgende Kubernetes-Ressourcen:

- **Deployment** (`templates/deployment.yaml`) – 1 Replica des Containers `wlanboy/http-tester`, mit Liveness- und Readiness-Probe auf `/healthz`.
- **Service** (`templates/service.yaml`) – ClusterIP-Service, leitet Traffic an die Pods weiter.
- **Gateway** (`templates/gateway.yaml`, nur bei `ingress.controller: istio`) – Istio `Gateway` auf Port 80/HTTP für die konfigurierten Hosts.
- **VirtualService** (`templates/virtualservice.yaml`, nur bei `ingress.controller: istio`) – Istio `VirtualService`, routet `/`-Traffic vom Gateway (und dem internen `mesh`-Gateway) zum Service.
- **IngressRoute** (`templates/traefik-ingressroute.yaml`, nur bei `ingress.controller: traefik`) – Traefik `IngressRoute`, routet die konfigurierten Hosts direkt zum Service.

Welche Ingress-Ressource gerendert wird, steuert `ingress.controller`
(`istio` | `traefik` | `none`). Zusätzlich zum Werte-Schalter prüft jedes
Ingress-Template über `.Capabilities.APIVersions.Has`, ob die passende CRD im
Zielcluster überhaupt vorhanden ist – ein `helm install`/`helm template`
schlägt also nicht fehl, nur weil die CRDs des jeweils anderen Controllers
fehlen.

## Konfiguration (`values.yaml`)

| Key | Beschreibung | Default |
|---|---|---|
| `namespace` | Ziel-Namespace für alle Ressourcen | `httptester` |
| `deploymentName` | Name für Deployment, Service, Gateway/VirtualService/IngressRoute | `tester` |
| `image.repository` | Container-Image-Repository | `wlanboy/http-tester` |
| `image.tag` | Image-Tag | `latest` |
| `service.port` | Container- und Service-Port (auch für Health-Checks) | `5000` |
| `ingress.controller` | Aktiver Ingress-Weg: `istio`, `traefik` oder `none` | `istio` |
| `ingress.hosts` | Liste externer Hostnamen für den Ingress (gilt für beide Controller) | `httptester.tp.lan`, `httptester.gmk.lan`, `httptester.big.lan`, `httptester.localhost` |
| `istio.gateway.selector` | Selector für das Istio Ingress-Gateway | `istio: ingressgateway` |
| `traefik.entryPoints` | Traefik Entrypoints für die IngressRoute | `[web, websecure]` |

Für die Wahl des Controllers stehen zwei schlanke Override-Dateien bereit,
statt `ingress.controller` von Hand setzen zu müssen:
[values-istio.yaml](values-istio.yaml) und
[values-traefik.yaml](values-traefik.yaml).

## Installation

> Wichtig: `-n <namespace>` muss mit `.Values.namespace` (Default: `httptester`)
> übereinstimmen. Die Templates setzen `metadata.namespace` explizit auf
> `.Values.namespace`, nicht auf `.Release.Namespace` – bei einem
> abweichenden `-n` legt `--create-namespace` den falschen Namespace an und
> `helm install` schlägt mit `namespaces "..." not found` fehl. Wird ein
> anderer Namespace gebraucht, `namespace` in den Values entsprechend
> überschreiben (z. B. `--set namespace=<name>`).

Mit Istio (Standard):

```bash
kubectl create namespace httptester
kubectl label namespace httptester istio-injection=enabled --overwrite
helm install tester ./tester-chart -n httptester --create-namespace -f tester-chart/values-istio.yaml
```

Mit Traefik:

```bash
kubectl create namespace httptester
helm install tester ./tester-chart -n httptester --create-namespace -f tester-chart/values-traefik.yaml
```

Das `istio-injection`-Label wird nur benötigt, wenn `ingress.controller:
istio` aktiv ist. Legt Argo/CI den Namespace per `--create-namespace` an,
muss das Label separat gepflegt werden, da ein Helm-Template ein bereits
existierendes Namespace-Objekt nicht zuverlässig patchen kann.

## Upgrade

```bash
helm upgrade tester ./tester-chart -n httptester
```

Bei geänderten Values (z. B. anderes Image-Tag):

```bash
helm upgrade tester ./tester-chart -n httptester --set image.tag=1.2.3
```

## Redeployment nach Neubau des Containers

Da `image.tag` standardmäßig auf `latest` steht, ändert `helm upgrade` allein die Deployment-Spec nicht (kein Diff), daher wird kein neuer Pod ausgerollt. Es gibt keine explizite `imagePullPolicy` im Chart – Kubernetes nutzt für den Tag `latest` automatisch `Always`, ein Neustart der Pods genügt also, um das neue Image zu ziehen:

```bash
kubectl rollout restart deployment/tester -n httptester
kubectl rollout status deployment/tester -n httptester
```

Alternativ mit Helm (erzwingt ein Redeployment auch ohne Values-Änderung):

```bash
helm upgrade tester ./tester-chart -n httptester --set podAnnotations.redeployedAt="$(date +%s)"
```

> Hinweis: `podAnnotations` existiert aktuell nicht im Chart/Values und müsste im `deployment.yaml`-Template ergänzt werden (z. B. unter `spec.template.metadata.annotations`), damit dieser Befehl einen Pod-Neustart auslöst. Ohne diese Ergänzung ist `kubectl rollout restart` der zuverlässige Weg.

## Hinweise

- Der Gateway-Selector (`istio.gateway.selector`) erwartet standardmäßig ein Istio Ingress-Gateway mit dem Label `istio: ingressgateway`.
- Der VirtualService exportiert die Route auf `.` (eigener Namespace), `istio-ingress` und `istio-system` und bindet sowohl das eigene Gateway als auch `mesh` (für internen Traffic innerhalb des Meshes) ein.
- Bei `ingress.controller: traefik` wird kein Mesh-Routing für internen Traffic benötigt – die IngressRoute deckt nur externen Traffic über die konfigurierten Hosts ab.
- Die IngressRoute setzt kein eigenes `tls`-Feld – `websecure` in `traefik.entryPoints` reicht aus, sofern der Cluster den Entrypoint per `--entryPoints.websecure.http.tls=true` und eine `TLSStore` mit `defaultCertificate` bereitstellt (so im Cluster dieses Repos konfiguriert). In Clustern ohne Default-Zertifikat schlägt der TLS-Handshake fehl bzw. es wird ein selbstsigniertes Traefik-Zertifikat verwendet.
- Bei `ingress.controller: none` wird keine Ingress-Ressource gerendert; Deployment und Service laufen weiter.
- Es gibt aktuell keine Ressourcen-Limits/-Requests, HPA oder ConfigMap/Secret-Einbindung im Chart.

## Testen

```bash
# Istio-Pfad rendern
helm template tester ./tester-chart -f tester-chart/values-istio.yaml --show-only templates/virtualservice.yaml

# Traefik-Pfad rendern
helm template tester ./tester-chart -f tester-chart/values-traefik.yaml --show-only templates/traefik-ingressroute.yaml

# sicherstellen, dass bei controller=none keine Ingress-Ressourcen entstehen
helm template tester ./tester-chart --set ingress.controller=none | grep -E "IngressRoute|VirtualService|Gateway"

helm lint ./tester-chart -f tester-chart/values-istio.yaml
helm lint ./tester-chart -f tester-chart/values-traefik.yaml
```
