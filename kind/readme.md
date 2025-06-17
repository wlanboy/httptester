# create local primary primary service mesh
We create two kind based kubernetes clusters. We then install metallb on a docker routable subnets to provide vips for the Istio Ingress Gateway and the Istio Eastwest Gateway.

## sysctl fix
We have to increase the fs.inotify.max_user* and net.ipv4.ip_forward sysctl settings.
```
sh sysctlfix.sh
```

## create two clusters with metallb using docker controlled cidrs
Create two kind clusters "east" and "west". Install metallb with two subnets on the docker/podman kind bridge subnet.
```
sh clusters.sh

sh metallb.sh
```

## install istio, istiod, istio ingress gateway, istio eastwest gateway on each cluster
```
sh istio-download.sh

sh istio.sh east
sh istio.sh west
```

## create mesh
First we check the vip and dns status of all gateways on all nodes.
Afterwards we install the Istio service mesh and check its sync status.
```
sh ips.sh                 
sh mesh.sh
```

## result istioctl remote-custers
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

## result istioctl remote-custers
```
istioctl proxy-status --context=kind-east
NAME                                                  CLUSTER     CDS                LDS                EDS                RDS               ECDS        ISTIOD                      VERSION
eastwestgateway-6f4b896fb5-fl9fw.istio-system         east        SYNCED (3m12s)     SYNCED (3m12s)     SYNCED (3m12s)     IGNORED           IGNORED     istiod-7b964997d4-mngrl     1.26.1
httpbin-686d6fc899-nt85m.test-east                    east        SYNCED (14m)       SYNCED (14m)       SYNCED (14m)       SYNCED (14m)      IGNORED     istiod-7b964997d4-mngrl     1.26.1
istio-ingressgateway-bc4786fff-w77j8.istio-system     east        SYNCED (2m7s)      SYNCED (2m7s)      SYNCED (2m7s)      SYNCED (2m7s)     IGNORED     istiod-7b964997d4-mngrl     1.26.1

istioctl proxy-status --context=kind-west
NAME                                                  CLUSTER     CDS              LDS              EDS              RDS              ECDS        ISTIOD                     VERSION
eastwestgateway-6f4b896fb5-lz24v.istio-system         west        SYNCED (19m)     SYNCED (19m)     SYNCED (19m)     IGNORED          IGNORED     istiod-7d597df9d-mdpxv     1.26.1
httpbin-686d6fc899-54tqc.test-west                    west        SYNCED (27m)     SYNCED (27m)     SYNCED (27m)     SYNCED (27m)     IGNORED     istiod-7d597df9d-mdpxv     1.26.1
istio-ingressgateway-bc4786fff-px78j.istio-system     west        SYNCED (12m)     SYNCED (12m)     SYNCED (12m)     SYNCED (12m)     IGNORED     istiod-7d597df9d-mdpxv     1.26.1
```

## cleanup
```
sh cleanup.sh
```
