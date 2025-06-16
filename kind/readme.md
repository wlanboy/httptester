# create local primary primary service mesh

## sysctl fix
```
sh sysctlfix.sh
```

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
sh ips.sh                 # check ips and dns records beforehand
sh mesh.sh
```

## result
```
istioctl remote-clusters --context=kind-'east'
NAME     SECRET                                    STATUS     ISTIOD
east                                               synced     istiod-7b964997d4-mngrl
west     istio-system/istio-remote-secret-west     synced     istiod-7b964997d4-mngrl

istioctl remote-clusters --context=kind-'west'
NAME     SECRET                                    STATUS      ISTIOD
west                                               synced      istiod-7d597df9d-mdpxv
east     istio-system/istio-remote-secret-east     synced      istiod-7d597df9d-mdpxv
```

## cleanup
```
sh cleanup.sh
```
