#!/bin/bash
set -e

KIND_CLUSTER_EAST="east"
KIND_CLUSTER_WEST="west"

cat <<EOF >"./east-kind.conf"
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
networking:
  ipFamily: ipv4
  apiServerAddress: 0.0.0.0
  apiServerPort: 6443
  kubeProxyMode: "iptables"
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  kubeadmConfigPatchesJSON6902:
  - group: kubeadm.k8s.io
    version: v1beta3
    kind: ClusterConfiguration
    patch: |
      - op: add
        path: /apiServer/certSANs/-
        value: east-control-plane
      - op: add
        path: /apiServer/certSANs/-
        value: gmk.local
      - op: add
        path: /apiServer/certSANs/-
        value: 127.0.0.1
- role: worker
EOF

cat <<EOF >"./west-kind.conf"
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
networking:
  ipFamily: ipv4
  apiServerAddress: 0.0.0.0
  apiServerPort: 7443
  kubeProxyMode: "iptables"
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  kubeadmConfigPatchesJSON6902:
  - group: kubeadm.k8s.io
    version: v1beta3
    kind: ClusterConfiguration
    patch: |
      - op: add
        path: /apiServer/certSANs/-
        value: west-control-plane
      - op: add
        path: /apiServer/certSANs/-
        value: gmk.local
      - op: add
        path: /apiServer/certSANs/-
        value: 127.0.0.1
- role: worker
EOF

create_kind_clusters() {
    echo "--- Erstelle Kind Clusters:  ---"

    kind create cluster --name "${KIND_CLUSTER_EAST}" --config=./east-kind.conf
    if [ $? -ne 0 ]; then
        echo "Fehler beim Erstellen von Cluster. Beende Skript."
        exit 1
    fi

    kind create cluster --name "${KIND_CLUSTER_WEST}" --config=./west-kind.conf
    if [ $? -ne 0 ]; then
        echo "Fehler beim Erstellen von Cluster. Beende Skript."
        exit 1
    fi

    echo "Clusters erfolgreich erstellt."
}

echo "--- Starte Initiales Kind Setup ---"

# Kind Cluster aufsetzen
create_kind_clusters

echo "--- Initiales Kind/Istio done ---"
