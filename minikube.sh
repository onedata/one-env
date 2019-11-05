#!/bin/bash

VERSION=${1}
sudo minikube delete
if [ -z "${VERSION}" ]
then
	echo "K8s version not specified, using default..."
	sudo minikube start --vm-driver=none --apiserver-ips 127.0.0.1 --apiserver-name localhost --feature-gates "VolumeSubpathEnvExpansion=true"
else 
	echo "Using k8s version ${VERSION}"
	sudo minikube start --vm-driver=none --apiserver-ips 127.0.0.1 --apiserver-name localhost --feature-gates "VolumeSubpathEnvExpansion=true" --kubernetes-version v${VERSION}.0
fi
