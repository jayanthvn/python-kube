#
# Ref: https://github.com/kubernetes-client/python
# pip install kubernetes
#

import yaml
import time
import operator
import sys
import threading
from kubernetes import client, config, watch
from collections import defaultdict

threadLock = threading.Lock()
threads = []

class myThread (threading.Thread):
   def __init__(self, threadID, name, client_v1):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
      self.client_v1 = client_v1
   def run(self):
      print("Starting " + self.name)
      #threadLock.acquire()
      watch_pods(self.name, self.client_v1)
      #threadLock.release()

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
    pod_ip_name = defaultdict(list) 
    for i in ret.items:
        ip = i.status.pod_ip
        podname = i.metadata.name
        if(str(ip) != "None" and i.status.phase == "Running"):
            if pod_ip_name[ip]:
                for p in pod_ip_name[ip]:
                    ret_p = v1.read_namespaced_pod(namespace="default",name=p)
                    if(ret_p.status.phase != "Running"):
                        print("Pod is not running "+p)
                        ip_counts[ip] = ip_counts[ip] - 1
                        pod_ip_name[ip].remove(p)
                
            pod_ip_name[ip].append(podname)
            count = ip_counts[ip] = ip_counts.get(ip, 0) + 1
            print("DEBUG: "+str(ip)+" : ",ip_counts[ip])
            if count > 1 :
                print("TADA found duplicate ip " + str(ip_counts[ip]))
                sys.exit()

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

def patch_aws_node(k8s_apps_v1, ver):
    print("Patching AWS node, this will restart IPAMD")
    if ver == "1.6.4" :
        patch = {"spec":{"template":{"spec":{"containers":[{"name": "aws-node", "image" : "602401143452.dkr.ecr.us-west-2.amazonaws.com/amazon-k8s-cni:v1.6.4"}]}}}}
    elif ver == "1.6.3" :    
        patch = {"spec":{"template":{"spec":{"containers":[{"name": "aws-node", "image" : "602401143452.dkr.ecr.us-west-2.amazonaws.com/amazon-k8s-cni:v1.6.3"}]}}}}
    elif ver == "1.5.7" :
        patch = {"spec":{"template":{"spec":{"containers":[{"name": "aws-node", "image" : "602401143452.dkr.ecr.us-west-2.amazonaws.com/amazon-k8s-cni:v1.5.7"}]}}}}
    elif ver == "1.7.0" :
        patch = {"spec":{"template":{"spec":{"containers":[{"name": "aws-node", "image" : "602401143452.dkr.ecr.us-west-2.amazonaws.com/amazon-k8s-cni:v1.7.0-rc2"}]}}}}

    k8s_apps_v1.patch_namespaced_daemon_set(name="aws-node",
            namespace="kube-system", body=patch)
    
def watch_pods(threadname, client_v1):
    w = watch.Watch()
    start_time = time.time()
    print("watch pods - "+threadname)
    for event in w.stream(func=client_v1.list_namespaced_pod,
                       namespace="kube-system",
                       field_selector="metadata.name="+threadname):
        print(threadname+" Status - "+event["object"].status.phase)               
        if event["object"].status.phase == "Terminating":
               w.stop()
               end_time = time.time()
               print("AWS NODE terminating in %0.2f sec",end_time-start_time)
               return
        if event["type"] == "DELETED":
            print("deleted", threadname)
            w.stop()
            return  
    print(threadname+" no events to watch")
    w.stop()
    return


def watch_aws_node(client_v1):
    ret = client_v1.list_namespaced_pod("kube-system", label_selector="k8s-app=aws-node")
    
    k = 0
    for i in ret.items:
        exec(f'thread{k} = myThread(k, i.metadata.name, client_v1)')
        exec(f'thread{k}.start()')
        exec(f'threads.append(thread{k})')
        k = k+1
        print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
     
    for t in threads:
        t.join()
    print("done upgrade/downgrade Exiting WATCH AWS NODE")
    
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
    ret = v1.list_namespaced_pod("default")
    for i in ret.items:
        print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
    
    print("****RUN***")
    print("AWS NODE - 1.7")
    scale_up_replicas(k8s_apps_v1, 6)
    resting_time(10)
    check_dup_ip(v1)
    
    print("DOWNGRADE AWS NODE - 1.6.4")
    patch_aws_node(k8s_apps_v1, "1.6.4")
    watch_aws_node(v1)
    scale_up_replicas(k8s_apps_v1, 16)
    resting_time(10)
    check_dup_ip(v1)
    
    print("UPGRADE AWS NODE - 1.7")
    patch_aws_node(k8s_apps_v1, "1.7.0")
    watch_aws_node(v1)
    scale_up_replicas(k8s_apps_v1, 25)
    resting_time(10)
    check_dup_ip(v1)
    
    cleanup(k8s_apps_v1)
    
if __name__ == '__main__':
    main()
