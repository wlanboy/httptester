#!/bin/bash
set -e

KIND_CLUSTER_EAST="east"
KIND_CLUSTER_WEST="west"
METALLB_VERSION="0.15.2"

METALLB_IP_RANGE_EAST="172.18.100.10-172.18.100.50" # für Cluster East
METALLB_IP_RANGE_WEST="172.18.200.10-172.18.200.50" # für Cluster West

install_metallb() {
    local cluster_name=$1
    local ip_range=$2
    echo "--- Installiere MetalLB auf Cluster: $cluster_name mit IP-Bereich: $ip_range ---"
    kubectl --context "kind-$cluster_name" apply -f "https://raw.githubusercontent.com/metallb/metallb/v${METALLB_VERSION}/config/manifests/metallb-native.yaml"
    kubectl --context "kind-$cluster_name" wait --for=condition=ready pod --all -n metallb-system --timeout=300s
    if [ $? -ne 0 ]; then
        echo "Fehler: MetalLB Pods auf Cluster $cluster_name nicht bereit."
        exit 1
    fi

    # Erstelle ConfigMap für MetalLB
    cat <<EOF | kubectl --context "kind-$cluster_name" apply -f -
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: example
  namespace: metallb-system
spec:
  addresses:
  - $ip_range
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: example
  namespace: metallb-system
spec:
  ipAddressPools:
  - example
EOF
    if [ $? -ne 0 ]; then
        echo "Fehler beim Konfigurieren von MetalLB auf Cluster $cluster_name."
        exit 1
    fi
    echo "MetalLB auf Cluster $cluster_name erfolgreich installiert und konfiguriert."
}

echo "--- Starte Metallb Setup ---"

# MetalLB auf beiden Clustern installieren
install_metallb "$KIND_CLUSTER_EAST" "$METALLB_IP_RANGE_EAST"
install_metallb "$KIND_CLUSTER_WEST" "$METALLB_IP_RANGE_WEST"

echo "--- Metallb done ---"
