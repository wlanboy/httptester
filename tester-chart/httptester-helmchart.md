# Helm Chart: tester

Helm Chart für das Deployment des `http-tester`-Services in Kubernetes mit Istio Service Mesh.

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
- **Gateway** (`templates/gateway.yaml`, optional) – Istio `Gateway` auf Port 80/HTTP für die konfigurierten Hosts.
- **VirtualService** (`templates/virtualservice.yaml`, optional) – Istio `VirtualService`, routet `/`-Traffic vom Gateway (und dem internen `mesh`-Gateway) zum Service.

Gateway und VirtualService werden nur gerendert, wenn `ingress.enabled: true` gesetzt ist.

## Konfiguration (`values.yaml`)

| Key | Beschreibung | Default |
|---|---|---|
| `namespace` | Ziel-Namespace für alle Ressourcen | `tester` |
| `deploymentName` | Name für Deployment, Service, Gateway und VirtualService | `tester` |
| `image.repository` | Container-Image-Repository | `wlanboy/http-tester` |
| `image.tag` | Image-Tag | `latest` |
| `service.port` | Container- und Service-Port (auch für Health-Checks) | `5000` |
| `ingress.enabled` | Istio Gateway/VirtualService aktivieren | `true` |
| `ingress.hosts` | Liste externer Hostnamen für den Ingress | `httptester.tp.lan`, `httptester.gmk.lan`, `httptester.big.lan` |

## Installation

```bash
kubectl create namespace tester
kubectl label namespace tester istio-injection=enabled --overwrite
helm install tester ./tester-chart -n tester --create-namespace
```

## Upgrade

```bash
helm upgrade tester ./tester-chart -n tester
```

Bei geänderten Values (z. B. anderes Image-Tag):

```bash
helm upgrade tester ./tester-chart -n tester --set image.tag=1.2.3
```

## Redeployment nach Neubau des Containers

Da `image.tag` standardmäßig auf `latest` steht, ändert `helm upgrade` allein die Deployment-Spec nicht (kein Diff), daher wird kein neuer Pod ausgerollt. Es gibt keine explizite `imagePullPolicy` im Chart – Kubernetes nutzt für den Tag `latest` automatisch `Always`, ein Neustart der Pods genügt also, um das neue Image zu ziehen:

```bash
kubectl rollout restart deployment/tester -n tester
kubectl rollout status deployment/tester -n tester
```

Alternativ mit Helm (erzwingt ein Redeployment auch ohne Values-Änderung):

```bash
helm upgrade tester ./tester-chart -n tester --set podAnnotations.redeployedAt="$(date +%s)"
```

> Hinweis: `podAnnotations` existiert aktuell nicht im Chart/Values und müsste im `deployment.yaml`-Template ergänzt werden (z. B. unter `spec.template.metadata.annotations`), damit dieser Befehl einen Pod-Neustart auslöst. Ohne diese Ergänzung ist `kubectl rollout restart` der zuverlässige Weg.

## Hinweise

- Der Gateway-Selector erwartet ein Istio Ingress-Gateway mit dem Label `istio: ingressgateway`.
- Der VirtualService exportiert die Route auf `.` (eigener Namespace), `istio-ingress` und `istio-system` und bindet sowohl das eigene Gateway als auch `mesh` (für internen Traffic innerhalb des Meshes) ein.
- Es gibt aktuell keine Ressourcen-Limits/-Requests, HPA oder ConfigMap/Secret-Einbindung im Chart.
