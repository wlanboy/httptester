# create local primary primary service mesh

## create two clusters with metallb using docker controlled cidrs
```
sh clusters.sh

sh metallb.sh
```

## install istio, istiod, istio ingress, istio gateway, istio eastwest gateway on each cluster
```
sh istio-download.sh

sh istio.sh east
sh istio.sh west
```

## create mesh
```
sh mesh.sh
```

## cleanup
```
sh cleanup.sh
```
