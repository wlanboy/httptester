#!/bin/bash
set -e

start_time_total=$(date +%s)
echo "Script started at $(date)"

# Run clusters.sh
echo "---"
start_time_clusters=$(date +%s)
echo "Starting clusters.sh at $(date)"
./clusters.sh
end_time_clusters=$(date +%s)
duration_clusters=$((end_time_clusters - start_time_clusters))
echo "Finished clusters.sh at $(date). Duration: ${duration_clusters} seconds."

# Run metallb.sh
echo "---"
start_time_metallb=$(date +%s)
echo "Starting metallb.sh at $(date)"
./metallb.sh
end_time_metallb=$(date +%s)
duration_metallb=$((end_time_metallb - start_time_metallb))
echo "Finished metallb.sh at $(date). Duration: ${duration_metallb} seconds."

# Run istio.sh east
echo "---"
start_time_istio_east=$(date +%s)
echo "Starting istio.sh east at $(date)"
./istio.sh east
end_time_istio_east=$(date +%s)
duration_istio_east=$((end_time_istio_east - start_time_istio_east))
echo "Finished istio.sh east at $(date). Duration: ${duration_istio_east} seconds."

# Run istio.sh west
echo "---"
start_time_istio_west=$(date +%s)
echo "Starting istio.sh west at $(date)"
./istio.sh west
end_time_istio_west=$(date +%s)
duration_istio_west=$((end_time_istio_west - start_time_istio_west))
echo "Finished istio.sh west at $(date). Duration: ${duration_istio_west} seconds."

# Run ips.sh
echo "---"
start_time_ips=$(date +%s)
echo "Starting ips.sh at $(date)"
./ips.sh
end_time_ips=$(date +%s)
duration_ips=$((end_time_ips - start_time_ips))
echo "Finished ips.sh at $(date). Duration: ${duration_ips} seconds."

# Run mesh.sh
echo "---"
start_time_mesh=$(date +%s)
echo "Starting mesh.sh at $(date)"
./mesh.sh
end_time_mesh=$(date +%s)
duration_mesh=$((end_time_mesh - start_time_mesh))
echo "Finished mesh.sh at $(date). Duration: ${duration_mesh} seconds."

echo "---"
end_time_total=$(date +%s)
duration_total=$((end_time_total - start_time_total))
echo "Script finished at $(date)."
echo "Total script runtime: ${duration_total} seconds."
