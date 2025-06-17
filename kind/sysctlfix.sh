#!/bin/bash

set -e

echo "see: https://kind.sigs.k8s.io/docs/user/known-issues/#pod-errors-due-to-too-many-open-files"

sudo sysctl fs.inotify.max_user_watches=524288
sudo sysctl fs.inotify.max_user_instances=512

# and check ipv4 forwarding
sudo sysctl -w net.ipv4.ip_forward=1

