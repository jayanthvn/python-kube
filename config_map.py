
from kubernetes import client, config

def create_config_map_object(cnt):
    metadata = client.V1ObjectMeta(
        name="game-demo"+str(cnt),
        namespace="default",
    )
    configmap = client.V1ConfigMap(
        api_version="v1",
        kind="ConfigMap",
        data=dict(player_inital_lives="3"),
        metadata=metadata
    )
    return configmap

def create_config_map(v1, configmap):
        v1.create_namespaced_config_map(
            namespace="default",
            body=configmap
        )

def get_config_map(v1):
    print(v1.list_namespaced_config_map(namespace="default"))

def delete_config_map(v1, cnt):
    c_name="game-demo"+str(cnt)
    v1.delete_namespaced_config_map(namespace="default", name=c_name)

def main():
    config.load_kube_config()
    v1 = client.CoreV1Api()
    
    for x in range(20000):    
        config_map = create_config_map_object(x)
        create_config_map(v1, config_map)
        #get_config_map(v1)

    #for x in range(10000):   
    #    delete_config_map(v1, x)
if __name__ == '__main__':
    main()
