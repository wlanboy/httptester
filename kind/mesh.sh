#!/bin/bash

ISTIO_DIR=./istio
ISTIO_SYSTEM_NAMESPACE="istio-system"
export PATH=$PWD/$ISTIO_DIR/bin:$PATH

KIND_CLUSTER_EAST="east"
KIND_CLUSTER_WEST="west"

MESH_ID=servicemesh
MESH_NETWORK=servicenetwork

# External IPs der East-West Gateways und controle-plane ermitteln
echo "Ermittle External IPs der East-West Gateways..."
EAST_WEST_GATEWAY_IP_EAST=$(kubectl --context "kind-$KIND_CLUSTER_EAST" get svc "eastwestgateway" -n "$ISTIO_SYSTEM_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
EAST_WEST_GATEWAY_IP_WEST=$(kubectl --context "kind-$KIND_CLUSTER_WEST" get svc "eastwestgateway" -n "$ISTIO_SYSTEM_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

control_plane_node_name_east=$(kubectl get nodes --context "kind-$KIND_CLUSTER_EAST" -l node-role.kubernetes.io/control-plane -o custom-columns=NAME:.metadata.name --no-headers)
echo "$control_plane_node_name_east"
IP_EAST=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "${control_plane_node_name_east}" 2>/dev/null)

control_plane_node_name_west=$(kubectl get nodes --context "kind-$KIND_CLUSTER_WEST" -l node-role.kubernetes.io/control-plane -o custom-columns=NAME:.metadata.name --no-headers)
echo "$control_plane_node_name_west"
IP_WEST=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "${control_plane_node_name_west}" 2>/dev/null)

echo "$EAST_WEST_GATEWAY_IP_EAST | $EAST_WEST_GATEWAY_IP_WEST | $IP_EAST | $IP_WEST"

echo "--- Primary-Primary Service Secrets ---"
istioctl create-remote-secret \
    --context="kind-${KIND_CLUSTER_EAST}" \
    --name="${KIND_CLUSTER_EAST}" --server "https://${control_plane_node_name_east}:6443" | \
    kubectl apply -f - --context="kind-${KIND_CLUSTER_WEST}" 

istioctl create-remote-secret \
    --context="kind-${KIND_CLUSTER_WEST}" \
    --name="${KIND_CLUSTER_WEST}" --server "https://${control_plane_node_name_west}:6443" | \
    kubectl apply -f - --context="kind-${KIND_CLUSTER_EAST}" 

sleep 5

echo "--- Primary-Primary Service Mesh Konfiguration ---"
istioctl remote-clusters --context="kind-${KIND_CLUSTER_EAST}"
istioctl remote-clusters --context="kind-${KIND_CLUSTER_WEST}"


echo "--- Primary-Primary Service Mesh Konfiguration Abgeschlossen ---"
echo "Ihre Kind Cluster '$KIND_CLUSTER_EAST' und '$KIND_CLUSTER_WEST' sollten jetzt als Primary-Primary Service Mesh konfiguriert sein."
echo "Verifizieren Sie die Konfiguration mit:"
echo "istioctl remote-clusters --context=kind-'$KIND_CLUSTER_EAST'"
echo "istioctl remote-clusters --context=kind-'$KIND_CLUSTER_WEST'"
echo "get logfiles of istiod"
echo "kubectl logs -n istio-system -l app=istiod --context=kind-'$KIND_CLUSTER_EAST'"
echo "kubectl logs -n istio-system -l app=istiod --context=kind-'$KIND_CLUSTER_WEST'"
