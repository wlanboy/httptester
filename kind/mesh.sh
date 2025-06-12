#!/bin/bash

# --- Variablen ---
KIND_CLUSTER_EAST="east"
KIND_CLUSTER_WEST="west"
ISTIO_SYSTEM_NAMESPACE="istio-system"
MESH_ID=servicemesh
MESH_NETWORK=servicenetwork

get_load_balancer_ip() {
    local cluster_name=$1
    local service_name=$2
    local namespace=$3
    local ip=""
    echo "Warte auf External IP für $service_name in Cluster $cluster_name..."
    for i in $(seq 1 60); do # Warte bis zu 5 Minuten
        ip=$(kubectl --context "kind-$cluster_name" get svc "$service_name" -n "$namespace" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
        if [ -n "$ip" ]; then
            echo "External IP für $service_name auf Cluster $cluster_name: $ip"
            echo "$ip"
            return 0
        fi
        echo "Warte auf External IP für $service_name ($i/60)..."
        sleep 5
    done
    echo "Fehler: Konnte keine External IP für $service_name auf Cluster $cluster_name ermitteln."
    return 1
}

echo "--- Starte Primary-Primary Service Mesh Konfiguration ---"

# External IPs der East-West Gateways ermitteln
echo "Ermittle External IPs der East-West Gateways..."
EAST_WEST_GATEWAY_IP_EAST=$(get_load_balancer_ip "$KIND_CLUSTER_EAST" "eastwestgateway" "$ISTIO_SYSTEM_NAMESPACE")
if [ $? -ne 0 ]; then
    echo "Beende Skript aufgrund fehlender East-West Gateway IP auf Cluster $KIND_CLUSTER_EAST."
    exit 1
fi

EAST_WEST_GATEWAY_IP_WEST=$(get_load_balancer_ip "$KIND_CLUSTER_WEST" "eastwestgateway" "$ISTIO_SYSTEM_NAMESPACE")
if [ $? -ne 0 ]; then
    echo "Beende Skript aufgrund fehlender East-West Gateway IP auf Cluster $KIND_CLUSTER_WEST."
    exit 1
fi

echo "--- Primary-Primary Service Secrets ---"
istioctl create-remote-secret \
    --context="kind-${KIND_CLUSTER_EAST}" \
    --name="${KIND_CLUSTER_EAST}" | \
    kubectl apply -f - --context="kind-${KIND_CLUSTER_WEST}"

istioctl create-remote-secret \
    --context="kind-${KIND_CLUSTER_WEST}" \
    --name="${KIND_CLUSTER_WEST}" | \
    kubectl apply -f - --context="kind-${KIND_CLUSTER_EAST}"

echo "--- Primary-Primary Service Mesh Konfiguration ---"
istioctl remote-clusters --context="kind-${KIND_CLUSTER_EAST}"
istioctl remote-clusters --context="kind-${KIND_CLUSTER_WEST}"


echo "--- Primary-Primary Service Mesh Konfiguration Abgeschlossen ---"
echo "Ihre Kind Cluster '$KIND_CLUSTER_EAST' und '$KIND_CLUSTER_WEST' sollten jetzt als Primary-Primary Service Mesh konfiguriert sein."
echo "Verifizieren Sie die Konfiguration mit 'istioctl proxy-config listeners', 'kubectl get svc -n istio-system', etc."