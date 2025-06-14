#!/bin/bash

ISTIO_SYSTEM_NAMESPACE="istio-system"
MESH_ID=servicemesh
MESH_NETWORK=servicenetwork
ISTIO_DIR=./istio

if [ -z "$1" ]; then
    echo "Verwendung: $0 <cluster_name>"
    exit 1
fi

export PATH=$PWD/$ISTIO_DIR/bin:$PATH

CLUSTER_NAME="$1"
KUBECTL_CONTEXT="kind-$CLUSTER_NAME"

install_istio_helm() {
    echo "--- Installiere Istio Komponenten auf Cluster: $CLUSTER_NAME mit Helm ---"

    # 1. Helm Repository hinzufügen
    echo "Füge Istio Helm Repository hinzu..."
    helm repo add istio https://istio-release.storage.googleapis.com/charts
    if [ $? -ne 0 ]; then
        echo "Fehler beim Hinzufügen des Istio Helm Repositories. Beende Skript."
        exit 1
    fi
    helm repo update

    # 2. Istio System Namespace erstellen
    echo "Erstelle Namespace '$ISTIO_SYSTEM_NAMESPACE' auf Cluster $CLUSTER_NAME..."
    kubectl --context "$KUBECTL_CONTEXT" create namespace "$ISTIO_SYSTEM_NAMESPACE" || true
    if [ $? -ne 0 ]; then
        echo "Fehler beim Erstellen des Namespaces '$ISTIO_SYSTEM_NAMESPACE'. Beende Skript."
        exit 1
    fi

    # 3. Istio Base installieren
    echo "Installiere Istio Base auf Cluster $CLUSTER_NAME..."
    helm install istio-base istio/base \
        -n "$ISTIO_SYSTEM_NAMESPACE" \
        --kube-context "$KUBECTL_CONTEXT" \
        --wait
    if [ $? -ne 0 ]; then
        echo "Fehler beim Installieren von Istio Base. Beende Skript."
        exit 1
    fi
    echo "Istio Base erfolgreich installiert."

    # 4. Istiod (Control Plane) installieren
    echo "Installiere Istiod (Control Plane) auf Cluster $CLUSTER_NAME..."
    helm install istiod istio/istiod \
        -n "$ISTIO_SYSTEM_NAMESPACE" \
        --kube-context "$KUBECTL_CONTEXT" \
        --set global.meshID=$MESH_ID \
        --set global.multiCluster.clusterName=$CLUSTER_NAME \
        --set global.network=$MESH_NETWORK \
        --wait
    if [ $? -ne 0 ]; then
        echo "Fehler beim Installieren von Istiod. Beende Skript."
        exit 1
    fi
    echo "Istiod erfolgreich installiert."

    # 5. Istio Ingress Gateway installieren
    echo "Installiere Istio Ingress Gateway auf Cluster $CLUSTER_NAME..."
    # Die Standardeinstellungen des istio/gateway Charts verwenden LoadBalancer und sind meist passend
    helm install istio-ingressgateway istio/gateway \
        -n "$ISTIO_SYSTEM_NAMESPACE" \
        --kube-context "$KUBECTL_CONTEXT" \
        --wait
    if [ $? -ne 0 ]; then
        echo "Fehler beim Installieren von Istio Ingress Gateway. Beende Skript."
        exit 1
    fi
    echo "Istio Ingress Gateway erfolgreich installiert."

    # 6. Istio East-West Gateway installieren
    echo "Installiere Istio East-West Gateway auf Cluster $CLUSTER_NAME..."
    # Hier werden spezifische Werte für den East-West Gateway übergeben
    cat <<EOF | helm install eastwestgateway istio/gateway \
        -n "$ISTIO_SYSTEM_NAMESPACE" \
        --kube-context "$KUBECTL_CONTEXT" \
        -f - \
        --wait
labels:
  istio: eastwestgateway
  app: eastwestgateway
  istio.io/rev: default # Wichtig für Multi-Cluster
service:
  type: LoadBalancer
  ports:
    - name: status-port
      port: 15021
      targetPort: 15021
    - name: tls
      port: 15012
      targetPort: 15012
    - name: tls-istiod
      port: 15010
      targetPort: 15010
    - name: mtls
      port: 15011
      targetPort: 15011
    - name: https
      port: 15443
      targetPort: 15443
EOF
    if [ $? -ne 0 ]; then
        echo "Fehler beim Installieren von Istio East-West Gateway. Beende Skript."
        exit 1
    fi
    echo "Istio East-West Gateway erfolgreich installiert."

    echo "Alle Istio Komponenten auf Cluster $CLUSTER_NAME erfolgreich mit Helm installiert."
}

install_istio_helm 
