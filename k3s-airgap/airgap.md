## install k3s with airgap

### get release
- https://github.com/k3s-io/k3s/releases
- e.g. https://github.com/k3s-io/k3s/releases/download/v1.32.3%2Bk3s1/k3s-airgap-images-amd64.tar.gz

## import images
```
docker image load k3s-airgap-images-amd64.tar.zst
```

## use private registry as pull through cache
- file: /etc/rancher/k3s/registries.yaml
```
mirrors:
  docker.io:
    endpoint:
      - "https://registry.example.com:443"
   rewrites:
     "^rancher/(.*)": "artefactory-project/rancher-images/$1"
```
- Then pulling docker.io/rancher/mirrored-pause:3.6 will transparently pull the image as registry.example.com:5000/rancher/mirrored-pause:3.6

## download images
```
sudo mkdir -p /var/lib/rancher/k3s/agent/images/
sudo curl -L -o /var/lib/rancher/k3s/agent/images/k3s-airgap-images-amd64.tar.zst "https://github.com/k3s-io/k3s/releases/download/v1.29.1-rc2%2Bk3s1/k3s-airgap-images-amd64.tar.zst"
```

## get install binary and shell script
```
https://github.com/k3s-io/k3s/releases/download/v1.32.3%2Bk3s1/k3s
https://get.k3s.io/
INSTALL_K3S_SKIP_DOWNLOAD=true K3S_KUBECONFIG_MODE="644" INSTALL_K3S_EXEC="--disable=traefik --node-ip=x.x.x.x" ./install.sh
INSTALL_K3S_SKIP_DOWNLOAD=true K3S_URL=https://<SERVER_IP>:6443 K3S_TOKEN=<YOUR_TOKEN> ./install.sh
```