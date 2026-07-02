#!/usr/bin/env bash
set -euo pipefail

helm uninstall tester1 --namespace ns1
helm uninstall tester2 --namespace ns2
helm uninstall tester3 --namespace ns3

kubectl delete namespace ns1 ns2 ns3
