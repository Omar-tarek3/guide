MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="BOUNDARY"

--BOUNDARY
Content-Type: text/x-shellscript; charset="us-ascii"

#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

# Install additional packages
yum install -y amazon-ssm-agent
systemctl enable amazon-ssm-agent && systemctl start amazon-ssm-agent
B64_CLUSTER_CA=${B64_CLUSTER_CA}
API_SERVER_URL=${API_SERVER_URL}
NODE_GROUP_NAME=${NODE_GROUP_NAME}
CAPACITY=${CAPACITY}
EC2_AMI=${EC2_AMI}

LABELS="--node-labels=eks.amazonaws.com/nodegroup-image=$EC2_AMI,eks.amazonaws.com/capacityType=${CAPACITY},eks.amazonaws.com/nodegroup=${NODE_GROUP_NAME}"

/etc/eks/bootstrap.sh ${CLUSTER_NAME} --kubelet-extra-args $LABELS --b64-cluster-ca $B64_CLUSTER_CA --apiserver-endpoint $API_SERVER_URL
aws s3 cp s3://mpesa-artifacts-vgsl-mps.cps-infra-prod-eu-west-1-binaries/tenable/NessusAgent-10.5.1-amzn2.x86_64.rpm .
yum install NessusAgent-10.5.1-amzn2.x86_64.rpm -y
sleep 10
/opt/nessus_agent/sbin/nessuscli agent link --key=9a26c30f9161c84f960ac2c376dfdcbcd67a68ca12387a35d472dcae6407bf83 --host=cloud.tenable.com --port=443
/opt/nessus_agent/sbin/nessuscli agent status
systemctl enable nessusagent
systemctl start nessusagent



# Pre-cache commonly used container images
nohup docker pull public.ecr.aws/eks-distro/kubernetes/pause:3.2 &

--BOUNDARY
Content-Type: application/node.eks.aws

apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: ${CLUSTER_NAME}
    apiServerEndpoint: ${API_SERVER_URL}
    certificateAuthority: ${B64_CLUSTER_CA}
    cidr: 172.20.0.0/16
  kubelet:
    config:
        maxPods: 110
    flags:
    - --node-labels=eks.amazonaws.com/nodegroup-image=${EC2_AMI},eks.amazonaws.com/capacityType=${CAPACITY},eks.amazonaws.com/nodegroup=${NODE_GROUP_NAME}

--BOUNDARY--