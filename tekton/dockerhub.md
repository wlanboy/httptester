# create docker hub secret
```bash
kubectl create secret docker-registry regcred \
  --docker-username=user \
  --docker-password=key \
  --docker-email=email@github.com \
  --docker-server=https://index.docker.io/v1/
```