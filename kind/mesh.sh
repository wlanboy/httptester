#!/bin/bash

ISTIO_DIR=./istio
ISTIO_SYSTEM_NAMESPACE="istio-system"
export PATH=$PWD/$ISTIO_DIR/bin:$PATH

KIND_CLUSTER_EAST="east"
KIND_CLUSTER_WEST="west"

MESH_ID=servicemesh
MESH_NETWORK=servicenetwork

GATEWAY_EXTERNAL_HOSTNAME_EAST="east.gmk.local"
GATEWAY_EXTERNAL_HOSTNAME_WEST="west.gmk.local"
API_SERVER_EXTERNAL_HOSTNAME_EAST="eastapi.gmk.local"
API_SERVER_EXTERNAL_HOSTNAME_WEST="westapi.gmk.local"
API_SERVER_SERVICE_NAMESPACE="default"

# External IPs der East-West Gateways und controle-plane ermitteln
echo "Ermittle External IPs der East-West Gateways..."
EAST_WEST_GATEWAY_IP_EAST=$(kubectl --context "kind-$KIND_CLUSTER_EAST" get svc "eastwestgateway" -n "$ISTIO_SYSTEM_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
EAST_WEST_GATEWAY_IP_WEST=$(kubectl --context "kind-$KIND_CLUSTER_WEST" get svc "eastwestgateway" -n "$ISTIO_SYSTEM_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "Ermittle External IPs der Ingress Gateways..."
INGRESS_GATEWAY_IP_EAST=$(kubectl --context "kind-$KIND_CLUSTER_EAST" get svc "istio-ingressgateway" -n "$ISTIO_SYSTEM_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
INGRESS_GATEWAY_IP_WEST=$(kubectl --context "kind-$KIND_CLUSTER_WEST" get svc "istio-ingressgateway" -n "$ISTIO_SYSTEM_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "Ermittle External IPs der Control Plane Nodes..."
control_plane_node_name_east=$(kubectl get nodes --context "kind-$KIND_CLUSTER_EAST" -l node-role.kubernetes.io/control-plane -o custom-columns=NAME:.metadata.name --no-headers)
echo "$control_plane_node_name_east"
IP_EAST=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "${control_plane_node_name_east}" 2>/dev/null)

control_plane_node_name_west=$(kubectl get nodes --context "kind-$KIND_CLUSTER_WEST" -l node-role.kubernetes.io/control-plane -o custom-columns=NAME:.metadata.name --no-headers)
echo "$control_plane_node_name_west"
IP_WEST=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "${control_plane_node_name_west}" 2>/dev/null)


echo "Gateway für API Server EAST"
cat <<EOF | kubectl apply --context "kind-$KIND_CLUSTER_EAST" -f -
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: api-server-gateway
  namespace: ${API_SERVER_SERVICE_NAMESPACE}
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: PASSTHROUGH 
    hosts:
    - "${API_SERVER_EXTERNAL_HOSTNAME_EAST}"
EOF

cat <<EOF | kubectl apply --context "kind-$KIND_CLUSTER_EAST" -f -
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: api-server-vs
  namespace: ${API_SERVER_SERVICE_NAMESPACE}
spec:
  hosts:
  - "${API_SERVER_EXTERNAL_HOSTNAME_EAST}"
  gateways:
  - api-server-gateway
  tls:
  - match:
    - port: 443
      sniHosts:
      - "${API_SERVER_EXTERNAL_HOSTNAME_EAST}"
    route:
    - destination:
        host: kubernetes.default.svc.cluster.local # Der interne Hostname des Kubernetes API-Servers
        port:
          number: 443
      weight: 100
EOF

echo "Gateway für API Server WEST"
cat <<EOF | kubectl apply --context "kind-$KIND_CLUSTER_WEST" -f -
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: api-server-gateway
  namespace: ${API_SERVER_SERVICE_NAMESPACE}
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: PASSTHROUGH 
    hosts:
    - "${API_SERVER_EXTERNAL_HOSTNAME_WEST}"
EOF

cat <<EOF | kubectl apply --context "kind-$KIND_CLUSTER_WEST" -f -
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: api-server-vs
  namespace: ${API_SERVER_SERVICE_NAMESPACE}
spec:
  hosts:
  - "${API_SERVER_EXTERNAL_HOSTNAME_WEST}"
  gateways:
  - api-server-gateway
  tls:
  - match:
    - port: 443
      sniHosts:
      - "${API_SERVER_EXTERNAL_HOSTNAME_WEST}"
    route:
    - destination:
        host: kubernetes.default.svc.cluster.local # Der interne Hostname des Kubernetes API-Servers
        port:
          number: 443
      weight: 100
EOF

echo "--- Primary-Primary Service Secrets EAST ---"
istioctl create-remote-secret \
    --context="kind-${KIND_CLUSTER_EAST}" \
    --name="${KIND_CLUSTER_EAST}" --server "https://${API_SERVER_EXTERNAL_HOSTNAME_EAST}:443" | \
    kubectl apply -f - --context="kind-${KIND_CLUSTER_WEST}" 

echo "--- Primary-Primary Service Secrets WEST ---"
istioctl create-remote-secret \
    --context="kind-${KIND_CLUSTER_WEST}" \
    --name="${KIND_CLUSTER_WEST}" --server "https://${API_SERVER_EXTERNAL_HOSTNAME_WEST}:443" | \
    kubectl apply -f - --context="kind-${KIND_CLUSTER_EAST}" 

sleep 5

echo "--- Primary-Primary Service Mesh Konfiguration EAST/WEST---"
istioctl remote-clusters --context="kind-${KIND_CLUSTER_EAST}"
istioctl remote-clusters --context="kind-${KIND_CLUSTER_WEST}"


echo "--- Primary-Primary Service Mesh Konfiguration Abgeschlossen ---"
echo "Ihre Kind Cluster '$KIND_CLUSTER_EAST' und '$KIND_CLUSTER_WEST' sollten jetzt als Primary-Primary Service Mesh konfiguriert sein."
echo "Verifizieren Sie die Konfiguration mit:"
echo "istioctl remote-clusters --context=kind-$KIND_CLUSTER_EAST"
echo "istioctl remote-clusters --context=kind-$KIND_CLUSTER_WEST"
echo "istioctl proxy-status --context=kind-$KIND_CLUSTER_EAST"
echo "istioctl proxy-status --context=kind-$KIND_CLUSTER_WEST"
echo "Sync Probleme mit logfiles von istiod finden"
echo "kubectl logs -n istio-system -l app=istiod --context=kind-$KIND_CLUSTER_EAST"
echo "kubectl logs -n istio-system -l app=istiod --context=kind-$KIND_CLUSTER_WEST"
