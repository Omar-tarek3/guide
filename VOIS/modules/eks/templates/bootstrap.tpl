#!/bin/bash
B64_CLUSTER_CA=${B64_CLUSTER_CA}
API_SERVER_URL=${API_SERVER_URL}
NODE_GROUP_NAME=${NODE_GROUP_NAME}
#NODE_COLOR=${NODE_COLOR}
#ACTIVE_COLOR=${ACTIVE_COLOR}
#KUBELET_EXTRA_ARGS="--node-labels=color=${NODE_COLOR}"
# if [ "${NODE_COLOR}" != "${ACTIVE_COLOR}" ]; then
#   KUBELET_EXTRA_ARGS="$KUBELET_EXTRA_ARGS --register-with-taints=standby=true:NoSchedule"
# fi

/etc/eks/bootstrap.sh ${CLUSTER_NAME} --kubelet-extra-args "$KUBELET_EXTRA_ARGS"