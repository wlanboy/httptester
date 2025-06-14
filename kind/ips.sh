#!/bin/bash

ISTIO_DIR=./istio
ISTIO_SYSTEM_NAMESPACE="istio-system"
export PATH=$PWD/$ISTIO_DIR/bin:$PATH

KIND_CLUSTER_EAST="east"
KIND_CLUSTER_WEST="west"

MESH_ID=servicemesh
MESH_NETWORK=servicenetwork

echo "--- Starte Primary-Primary Service Mesh Konfiguration ---"

# External IPs der East-West Gateways ermitteln
echo "Ermittle External IPs der East-West Gateways..."
EAST_WEST_GATEWAY_IP_EAST=$(kubectl --context "kind-$KIND_CLUSTER_EAST" get svc "eastwestgateway" -n "$ISTIO_SYSTEM_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
EAST_WEST_GATEWAY_IP_WEST=$(kubectl --context "kind-$KIND_CLUSTER_WEST" get svc "eastwestgateway" -n "$ISTIO_SYSTEM_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

control_plane_node_name=$(kubectl get nodes --context "kind-$KIND_CLUSTER_WEST" -l node-role.kubernetes.io/control-plane -o custom-columns=NAME:.metadata.name --no-headers)
echo "$control_plane_node_name"
IP_EAST=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "${control_plane_node_name}" 2>/dev/null)

control_plane_node_name=$(kubectl get nodes --context "kind-$KIND_CLUSTER_WEST" -l node-role.kubernetes.io/control-plane -o custom-columns=NAME:.metadata.name --no-headers)
echo "$control_plane_node_name"
IP_WEST=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}}}' "${control_plane_node_name}" 2>/dev/null)

echo "$EAST_WEST_GATEWAY_IP_EAST | $EAST_WEST_GATEWAY_IP_WEST | $IP_EAST | $IP_WEST"
