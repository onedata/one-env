# one-env

*one-env* is a collection of scripts used to start and configure onedata
deployments, for development and testing
(integration, acceptance, stress and performance).


First run
=========
Deploying environment with one-env requires access to kubernetes cluster.
This can be either local cluster created using minikube or remote cluster.

## 1. Configuring helm and k8s
The first thing you should check is whether appropriate k8s context is set.
You can check this in k8s config file (by default `~/.kube/config`). The name
of the currently used context is stored under `current-context` key.

### 1. Local cluster
When you start kubernetes cluster for the first time (or after you have
deleted old cluster), you have to follow these steps:
1. Initialize helm - this can be done using command: \
`helm init` \
In order to check that helm is ready to use, you can list system pods using: \
`kubectl get pods -n kube-system` \
There should be tiller pod up and running.
2. Create cluster role bindings - this can be done using command:
```
kubectl create clusterrolebinding serviceaccounts-cluster-admin --clusterrole=cluster-admin \
--group=system:serviceaccounts
```

### 2. Remote cluster
Using remote cluster is similar to using local cluster. There is however chance
that k8s and helm configuration has already been done in cluster.
1. Make sure helm is running - you can check this by listing system pods using: \
`kubectl get pods -n kube-system` \
If tiller pod is present and running, it means that helm is ready to use.
Otherwise initialize helm using command: \
`helm init`
2. Make sure cluster role binding is present - you can check this using command: \
`kubectl get clusterrolebinding serviceaccounts-cluster-admin` \
If there is no cluster role binding create one using command:
```
kubectl create clusterrolebinding serviceaccounts-cluster-admin --clusterrole=cluster-admin \
--group=system:serviceaccounts  
```

## 2. Configuring one-env
To initialize one-env, you should run command: \
`./onenv init` \
This will create `~/.one-env` directory which will contain data for future
deployments. Moreover the configuration file will be present in path
`~/.one-env/config`. Please make sure that configuration is correct.
The most important parts are:
```
hostHomeDir: /home/user     
kubeHostHomeDir: /home/user
```

where:
* `hostHomeDir` - should point to home directory on your computer.
* `kubeHostHomeDir` - should point to directory in which your home directory
will be stored in virtual machine. If you're using minikube with option
`--vm-driver-none` or kubeadm you probably don't have to change that path.
Otherwise please refer to minikube documentation:
https://kubernetes.io/docs/setup/minikube for correct path.

The other options are:
* `currentNamespace` - name of namespace in which current deployment has been
started. It is modified by `./onenv up` script to which you can pass option
allowing to set namespace. Otherwise default namespace is used.
* `defaultNamespace` - name of default namespace.
* `currentHelmDeploymentName` - name of current helm deployment name in which
deployment has been started. It is modified by `./onenv up` script
to which you can pass option allowing to set helm deployment name.
Otherwise default name is used.
* `defaultHelmDeploymentName` - default helm deployment name.
* `maxPersistentHistory` - specifies number of historical deployments for which
data should be stored.

## 3. Running one-env
When all configuration is done, you can start deployment using `./onenv up` 
command, for example:

```
./onenv up -f test_env_config.yaml -s
```

where:
* `-f` - forces deletion of the old deployment
* `test_env_config.yaml` - is the file to path containing deployment
description (see `Deployment configuration -> Configuraion on start`
section for more details)
* `-s` - forces services to be started from compiled sources


Deployment configuration
=================================
Deployment can be configured in two phases: on start and after
deployment is running. In the first case you can configure whether services
should be started from packages or using compiled sources, images that should
be used for each pod, onedata environment, etc. In the second case you can
only configure onedata environment, i. e. groups, spaces, users, etc.

### 1. Configuration on start
There are two ways to configure deployment on start:
* through `.yaml` file that is passed to `./onenv up` script - deployment
description examples can be found in `example_config.yaml` file.
* through command line options that overrides configuration passed via `.yaml`
file. Note that command line options are available only for the most common
configuration elements like specification of images to use.

### 2. Configuring onedata environment on running deployment 
Once deployment is up and running you can configure onedata environment using
`./onenv patch` script, by passing `.yaml` file containing environment
description to it. The example of such description can be found in
`patch_example.yaml` file.

### 3. Starting oneclients on running deployment
Additionally to previous configuration modes, you can start oneclients
using `./onenv oneclient` script. Again you can configure
oneclient options using either `.yaml` file passed to script (example can
be found in `example_client_values.yaml`) or using command line options. Note
that you can specify if oneclient should be started from packages or from
compiled sources.


Updating service's sources
==========================
When you choose to start services from compiled sources, they are rsynced to
the appropriate container in pod. Then, when you make changes and recompile
sources, you may want to update sources in pod. To do this you can use
`./onenv update` script. If you want to dynamically look for changes in sources
and rsync files that have changed you can use `./onenv watch` script. Note that
for both of this scripts you can specify if sources for each pod should be
updated or only for specified ones. Moreover you can specify which onedata
services should be updated.


Logs
====
`./onenv logs` script allows to display logs from pods. For each pod you can
display entrypoint's logs. Moreover for oneprovider and onezone services,
you can display logs from worker, cluster-manager and onepanel (you can also
specify which log file should be displayed). \
To export logs you can use `./onenv export` script.


Requirements
============
Required Python packages are listed in `requirements.txt` and can be
installed using e.g. `pip`:

`pip3 install -r requirements.txt`

Other requirements:
* rsync version 3.1.x
* helm
* kubectl


Common problems
================
1. Problem: deployment starts correctly, but cross-support-jobs fails with
`Init:Error`. \
Solution: make sure that cluster role binding is created
(see `First Run -> Configuring helm and k8s` section).
2. Problem: services from sources does not start correctly. \
Solution: make sure `hostHomeDir` and `kubeHostHomeDir` are set correctly in
`~/.one-env/config` (see `First run -> Configuring one-env` section).
3. Problem: rsync command fails with error similar to
`protocol version mismatch -- is your shell clean?` \
Solution: make sure you are using `-dev` images.
4. Problem: `./onenv watch` command fails with error similar to
`limit of inotify watches reached`. \
Solution: increase the inotify file watch limit. On linux you can do this using 
following commands:
* temporarily:

```
sudo sysctl fs.inotify.max_user_watches=10000
sudo sysctl -p
```

* permanently

```
echo fs.inotify.max_user_watches=10000 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```