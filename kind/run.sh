#!/bin/bash
set -e

./clusters.sh
./metallb.sh
./istio.sh east
./istio.sh west
./ips.sh 
./mesh.sh 
