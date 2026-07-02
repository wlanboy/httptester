#!/usr/bin/env bash
set -euo pipefail

kubectl create namespace ns1
kubectl label namespace ns1 istio-injection=enabled --overwrite
helm upgrade --install tester1 ./tester-chart \
  --namespace ns1 \
  --set deploymentName=tester1 --set namespace=ns1

kubectl create namespace ns2
kubectl label namespace ns2 istio-injection=enabled --overwrite
helm upgrade --install tester2 ./tester-chart \
  --namespace ns2 \
  --set deploymentName=tester2 --set namespace=ns2 \
  --set ingress.enabled=false

kubectl create namespace ns3
kubectl label namespace ns3 istio-injection=enabled --overwrite
helm upgrade --install tester3 ./tester-chart \
  --namespace ns3 \
  --set deploymentName=tester3 --set namespace=ns3 \
  --set ingress.enabled=false
