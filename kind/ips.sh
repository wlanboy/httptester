#!/bin/bash

ISTIO_DIR=./istio
ISTIO_SYSTEM_NAMESPACE="istio-system"
export PATH=$PWD/$ISTIO_DIR/bin:$PATH

KIND_CLUSTER_EAST="east"
KIND_CLUSTER_WEST="west"

MESH_ID=servicemesh
MESH_NETWORK=servicenetwork

API_SERVER_EXTERNAL_HOSTNAME_EAST="east.gmk.local"
API_SERVER_EXTERNAL_HOSTNAME_WEST="west.gmk.local"
API_SERVER_SERVICE_NAMESPACE="default"

# External IPs der East-West Gateways und controle-plane ermitteln
echo "Ermittle External IPs der East-West Gateways..."
EAST_WEST_GATEWAY_IP_EAST=$(kubectl --context "kind-$KIND_CLUSTER_EAST" get svc "eastwestgateway" -n "$ISTIO_SYSTEM_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
EAST_WEST_GATEWAY_IP_WEST=$(kubectl --context "kind-$KIND_CLUSTER_WEST" get svc "eastwestgateway" -n "$ISTIO_SYSTEM_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "Ermittle External IPs der East-West Gateways..."
INGRESS_GATEWAY_IP_EAST=$(kubectl --context "kind-$KIND_CLUSTER_EAST" get svc "istio-ingressgateway" -n "$ISTIO_SYSTEM_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
INGRESS_GATEWAY_IP_WEST=$(kubectl --context "kind-$KIND_CLUSTER_WEST" get svc "istio-ingressgateway" -n "$ISTIO_SYSTEM_NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

control_plane_node_name_east=$(kubectl get nodes --context "kind-$KIND_CLUSTER_EAST" -l node-role.kubernetes.io/control-plane -o custom-columns=NAME:.metadata.name --no-headers)
echo "$control_plane_node_name_east"
IP_EAST=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "${control_plane_node_name_east}" 2>/dev/null)

control_plane_node_name_west=$(kubectl get nodes --context "kind-$KIND_CLUSTER_WEST" -l node-role.kubernetes.io/control-plane -o custom-columns=NAME:.metadata.name --no-headers)
echo "$control_plane_node_name_west"
IP_WEST=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "${control_plane_node_name_west}" 2>/dev/null)

echo "EASTWEST GATEWAYS: $EAST_WEST_GATEWAY_IP_EAST | $EAST_WEST_GATEWAY_IP_WEST"
echo "INGRESS GATEWAYS: $INGRESS_GATEWAY_IP_EAST | $INGRESS_GATEWAY_IP_WEST"
echo "NODES: $IP_EAST | $IP_WEST"
