from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
import os,sys
import re
import argparse
parser = argparse.ArgumentParser(sys.argv[0])
#parser.add_argument("--configmap", help="Create configmap  (default: 'Secret')", action='store_true',default=False)
parser.add_argument("--name", help="Name of Secret/Configmap", type=str,required=True)
parser.add_argument("--namespace", help="Name of Namespace", type=str)
parser.add_argument("--dir", help="Source directory path", type=str,required=True)
parser.add_argument("--file_pattern", help="File pattern for match files (default: '.*'", type=str,default=".*")
args = parser.parse_args()

#print(args.configmap)
print("name: "+ args.name)
if args.namespace:
  print("namespace: "+args.namespace)
print("dir: "+args.dir)
print("file_pattern: "+args.file_pattern)



def get_default_labels(name=None):
    default_labels = {
        'operated-by': 'k8s-sidecar-cm-to-file'
        }
    return default_labels


def get_secret_object(name, namespace, string_data):
    
    secret = client.V1Secret()

    # Metadata
    secret.metadata = client.V1ObjectMeta(
        name=name,
        namespace=namespace,
        labels=get_default_labels()
        )

    secret.string_data = string_data
    return secret

def create_secret(name,namespace,data):

    v1 = client.CoreV1Api()
    body = get_secret_object(name,
         namespace,
         data
         )
   # print(body)
    secret={}
    try:
        secret = v1.create_namespaced_secret(namespace, body)
    except client.rest.ApiException as e:
        if e.status == 409:
            # Secret already exists
            print("Secret replace:")
            try:
              secret=v1.replace_namespaced_secret(name, namespace, body, pretty=True)
            except client.rest.ApiException as e:
                print(e)
                return False

        else:
            print(e)
            return False
    print("Secret Ok")
    return secret


def filesToMap(path,pattern):
    myMap = {}
    for file_name in os.listdir(path):
        if re.search(pattern, file_name):
          filePath=os.path.join(path, file_name)
          file = open(filePath, "r") 
          myMap[file_name] = file.read()
          file.close()
    return myMap

def main():
    print("Starting ..")
    if os.path.isfile("/var/run/secrets/kubernetes.io/serviceaccount/namespace"):
      config.load_incluster_config()
      with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
        namespace = f.read()
    else:  
      config.load_kube_config()
      namespace="default"

    print("Namespace: "+namespace)
    print("Config for cluster api loaded...")

    tmp_namespace = namespace
    if args.namespace:
        tmp_namespace=args.namespace
    data=filesToMap(args.dir,args.file_pattern)
    create_secret(args.name,tmp_namespace,data)
 


if __name__ == '__main__':
    main()