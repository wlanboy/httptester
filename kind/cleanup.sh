#!/bin/bash

set -e

#helm uninstall istio-base -n istio-system --kube-context kind-east
#helm uninstall istiod -n istio-system --kube-context kind-east
#helm uninstall istio-ingressgateway -n istio-system --kube-context kind-east
#helm uninstall eastwestgateway -n istio-system -n istio-system --kube-context kind-east

kind delete clusters east
kind delete clusters west
