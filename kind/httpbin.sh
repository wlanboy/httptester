#!/bin/bash
NAMESPACE_EAST=test-east
NAMESPACE_WEST=test-west
CONTEXT_EAST=kind-east
CONTEXT_WEST=kind-west

ISTIO_DIR=./istio
HTTPBIN_YAML="${ISTIO_DIR}/samples/httpbin/httpbin.yaml"
HTTPBIN_GATEWAY_YAML="${ISTIO_DIR}/samples/httpbin/httpbin.-gatewayyaml"

kubectl create namespace "${NAMESPACE_EAST}" --context "${CONTEXT_EAST}"
kubectl create namespace "${NAMESPACE_WEST}" --context "${CONTEXT_WEST}"

kubectl label namespace "${NAMESPACE_EAST}" istio-injection=enabled --overwrite=true --context "${CONTEXT_EAST}"
kubectl label namespace "${NAMESPACE_WEST}" istio-injection=enabled --overwrite=true --context "${CONTEXT_WEST}"

kubectl apply -n "${NAMESPACE_EAST}" -f "${HTTPBIN_YAML}" --context "${CONTEXT_EAST}"
kubectl apply -n "${NAMESPACE_WEST}" -f "${HTTPBIN_YAML}" --context "${CONTEXT_WEST}"

kubectl apply -n "${NAMESPACE_EAST}" -f "${HTTPBIN_GATEWAY_YAML}" --context "${CONTEXT_EAST}"
kubectl apply -n "${NAMESPACE_WEST}" -f "${HTTPBIN_GATEWAY_YAML}" --context "${CONTEXT_WEST}"

kubectl create namespace test --context "${CONTEXT_EAST}"
kubectl label namespace test istio-injection=enabled --overwrite=true --context "${CONTEXT_EAST}"
kubectl run busybox --image=busybox --namespace=test --restart=Never -- sleep infinity --context "${CONTEXT_EAST}"

kubectl create namespace test --context "${CONTEXT_WEST}"
kubectl label namespace test istio-injection=enabled --overwrite=true --context "${CONTEXT_WEST}"
kubectl run busybox --image=busybox --namespace=test --restart=Never -- sleep infinity --context "${CONTEXT_WEST}"

echo "start exploring the network"
echo "kubectl exec -it -n test busybox --context kind-east -- sh" 
echo "kubectl delete pod busybox -n test --wait=false --context kind-east"
echo "kubectl exec -it -n test busybox --context kind-west -- sh" 
echo "kubectl delete pod busybox -n test --wait=false --context kind-west"
echo "wget -S --spider http://httpbin.test-west.svc.cluster.local:8000"
echo "wget -S --spider http://httpbin.test-east.svc.cluster.local:8000"

#kubectl logs busybox -c istio-proxy -n test --context kind-west
#istioctl proxy-config all busybox -n test --context kind-west
#istioctl analyze --context kind-west
#istioctl analyze --context kind-east