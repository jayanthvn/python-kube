#
# Ref: https://github.com/kubernetes-client/python
# pip install kubernetes
#

import yaml
import time
import operator
from kubernetes import client, config

def scale_up_replicas(k8s_apps_v1, n):
    print("Scaling up replicas...", n)
    patch = {"spec": {"replicas": n}}
    k8s_apps_v1.patch_namespaced_deployment(name="my-nginx", namespace="default", body=patch)

def scale_down_replicas(k8s_apps_v1, n):
    print("Scaling down replicas...", n)
    patch = {"spec": {"replicas": n}}
    k8s_apps_v1.patch_namespaced_deployment(name="my-nginx", namespace="default", body=patch)

def check_dup_ip(v1):
    print("Checking dup ip...")
    ret = v1.list_namespaced_pod("default")
    ip_counts = dict()
    for i in ret.items:
        ip = i.status.pod_ip
        ip_counts[ip] = ip_counts.get(ip, 0) + 1
        print("DEBUG: "+str(ip)+" : ",ip_counts[ip])
        if ip_counts.get(ip) > 1:
            print("TADA found duplicate ip" + ip_counts[ip])

def cleanup(k8s_apps_v1):
    print("Cleaning up deployment")
    k8s_apps_v1.delete_namespaced_deployment(name="my-nginx", namespace="default")

def resting_time(n):
    print("Sleeping ...", n)
    time.sleep( n )

def restart_aws_node(k8s_apps_v1, flag):
    if flag == True :
        val = 1
    else:
        val = 2
    print("Patching AWS node, this will restart IPAMD")
    #print(k8s_apps_v1.read_namespaced_daemon_set(name="aws-node",
    #    namespace="kube-system"))
    patch = {"spec":{"template":{"spec":{"containers":[{"name": "aws-node", "env" :[{"name":"WARM_ENI_TARGET","value":str(val)}]}]}}}}
    k8s_apps_v1.patch_namespaced_daemon_set(name="aws-node",
            namespace="kube-system", body=patch)

def main():
    # Configs can be set in Configuration class directly or using helper utility
    config.load_kube_config()
    v1 = client.CoreV1Api()

    with open("/local/home/varavaj/eks_workshop/run-my-nginx.yaml") as f:
        dep = yaml.safe_load(f)
        k8s_apps_v1 = client.AppsV1Api()
        resp = k8s_apps_v1.create_namespaced_deployment(
            body=dep, namespace="default")
        print("Deployment created. status='%s'" % resp.metadata.name)
    
    resting_time(10)
    print("Listing pods with their IPs:")
    # ret = v1.list_pod_for_all_namespaces(watch=False)
    ret = v1.list_namespaced_pod("default")
    for i in ret.items:
        print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
    
    flag = True
    for x in range(10):    
        print("****RUN***",x)
        scale_up_replicas(k8s_apps_v1, 30)
        resting_time(20)
        check_dup_ip(v1)
        scale_down_replicas(k8s_apps_v1, 1)
        resting_time(20)
        check_dup_ip(v1)
        restart_aws_node(k8s_apps_v1, flag)
        resting_time(5)
        flag = operator.not_(flag)

    restart_aws_node(k8s_apps_v1, flag)
    cleanup(k8s_apps_v1)
    
if __name__ == '__main__':
    main()
