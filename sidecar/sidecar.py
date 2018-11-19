from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
from urllib3.exceptions import ProtocolError
import os
import sys
import requests
import re
import shutil
import tempfile
import subprocess
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

prog = re.compile('^(?P<file_name>.+)\.part\d+\.?.*$')
sourceFolder = tempfile.mkdtemp()
transform={}

def writeTextToFile(folder, filename, data):
    with open(folder +"/"+ filename, 'w') as f:
        f.write(data)
        f.close()


def request(url, method, payload):
    r = requests.Session()
    retries = Retry(total = 5,
            connect = 5,
            backoff_factor = 0.2,
            status_forcelist = [ 500, 502, 503, 504 ])
    r.mount('http://', HTTPAdapter(max_retries=retries))
    r.mount('https://', HTTPAdapter(max_retries=retries))
    if url is None:
        print("No url provided. Doing nothing.")
        # If method is not provided use GET as default
    elif method == "GET" or method is None:
        res = r.get("%s" % url, timeout=10)
        print ("%s request sent to %s. Response: %d %s" % (method, url, res.status_code, res.reason))
    elif method == "POST":
        res = r.post("%s" % url, json=payload, timeout=10)
        print ("%s request sent to %s. Response: %d %s" % (method, url, res.status_code, res.reason))


def removeFile(folder, filename):
    completeFile = folder +"/"+filename
    if os.path.isfile(completeFile):
        os.remove(completeFile)
    else:
        print("Error: %s file not found" % completeFile)


def watchForChanges(label, targetFolder, url, method, payload, current):
    v1 = client.CoreV1Api()
    w = watch.Watch()
    stream = None
    partfiles = os.getenv('PARTFILES')
    if partfiles is None:
      partfiles = False
    else:
      partfiles = True

    comment = os.getenv('COMMENT')
    if comment is None:
      comment = False
    else:
      comment = True 

    namespace = os.getenv("NAMESPACE")
    if namespace is None:
        stream = w.stream(v1.list_namespaced_config_map, namespace=current)
    elif namespace == "ALL":
        stream = w.stream(v1.list_config_map_for_all_namespaces)
    else:
        stream = w.stream(v1.list_namespaced_config_map, namespace=namespace)
    for event in stream:
        metadata = event['object'].metadata
        if metadata.labels is None:
            continue
        print(f'Working on configmap {metadata.namespace}/{metadata.name}')
        if label in event['object'].metadata.labels.keys():
            print("Configmap with label found")
            #delete all old files frim config map
            # fixed issue if one file from cm is removed
            cmid="_"+metadata.name+"_"+metadata.namespace
            purge(sourceFolder,'.*'+cmid)

            dataMap=event['object'].data
            if dataMap is None:
                print("Configmap does not have data.")
                # for sure if some one delete data
                if partfiles:
                  processFiles(sourceFolder,targetFolder,comment)
                continue
            eventType = event['type']


            for filename in dataMap.keys():
                print("File in configmap %s %s" % (filename, eventType))
                if (eventType == "ADDED") or (eventType == "MODIFIED"):
                    if partfiles:
                        if prog.match(filename):  #if parts\d+ is in file 
                            writeTextToFile(sourceFolder,filename+cmid , dataMap[filename])
                        else:
                            writeTextToFile(targetFolder,filename, dataMap[filename])
                    else:
                      writeTextToFile(targetFolder, filename, dataMap[filename])

                    
                else:
                    rmFile(sourceFolder,targetFolder,filename)

            if partfiles:
                processFiles(sourceFolder,targetFolder,comment)
            check_config=checkConfig()
            if url is not None and check_config:
                       request(url, method, payload)

# $Env:DATA_NAME_ROUTE="alertmanager-route"
# $Env:DATA_INDENT_ROUTE="2"
# $Env:DATA_FILE_ROUTE="alertmanager.yaml.part1.01routes"

# $Env:DATA_NAME_RECEIVERS="alertmanager-receivers"
# $Env:DATA_INDENT_RECEIVERS="0"
# $Env:DATA_FILE_RECEIVERS="alertmanager.yaml.part6.08receivers"

def getTransform():
  transform = {}
  for k, v in os.environ.items():
    if re.match('DATA_NAME_(.*)',k):
      print("Found :" + k)
      name=re.search('DATA_NAME_(.*)',k).group(1)
      transform[name]={}
      transform[name]['data_name'] = v

      transform[name]['data_file'] = os.getenv("DATA_FILE_"+name)
      if transform[name]['data_file'] is None:
          print("Oups DATA_FILE_" +name+ " is empty")
          quit()
      transform[name]['data_indent'] = int(os.getenv("DATA_INDENT_"+name))
      if transform[name]['data_indent'] is None:
          print("Oups DATA_INDENT_" +name+ " is empty. Set to 0")
          transform[name]['data_indent'] = 0
  print(transform)
  return transform

def purge(dir,pattern):
    for f in os.listdir(dir):
        if re.search(pattern, f):
            filePath=os.path.join(dir, f)
            print('rm '+filePath)
            os.remove(filePath)

def rmFile(sourceFolder,targetFolder,file):
  if os.path.exists(targetFolder +"/"+file):
          os.remove(targetFolder+"/"+file)
          print("Delete file: " + targetFolder +"/"+file)
  if os.path.exists(sourceFolder +"/"+file):
          os.remove(sourceFolder +"/"+file)
          print("Delete file: "+ sourceFolder +"/"+file)

def transformFiles(transform,listfiles,path):
  for f in listfiles: 
    for name in transform:
        
      if re.match(transform[name]['data_name'], f):
        
        file_name=re.sub(transform[name]['data_name'],transform[name]['data_file'],f)
        file_name=file_name+"_"+transform[name]['data_name']
  
        
        fromfullpath=os.path.join(path, f)
        fromfile = open(fromfullpath, 'r') 
        tofullpath=os.path.join(path, file_name)
        
        print("Transform file "+ f +" to "+ file_name + " indent:"+ str(transform[name]['data_indent']))
        tofile=open(tofullpath, "w")
        tofile.write(indent(fromfile.read(),transform[name]['data_indent']))
        tofile.close()
        fromfile.close() 
        removeFile(path,f)
	
def appendParts(listfiles,frompath,topath,comment):
  for f in listfiles:
    file_name=f

    result = prog.match(file_name)
    if result:
      file_name=result.group('file_name')
    fromfullpath=os.path.join(frompath, f)
    fromfile = open(fromfullpath, 'r') 
    tofullpath=os.path.join(topath, file_name)
	
    print("Work on "+ file_name +" << "+ f )
    tofile=open(tofullpath, "a+")
    if comment:
      tofile.write('#### source :'+f+"\n") 
    tofile.write(fromfile.read())
    tofile.close()
    fromfile.close()

def indent(text, count_ident=0):
    indent=' ' * count_ident
    return ''.join([indent + l for l in text.splitlines(True)])

def checkConfig():
    print("Start check config")
    command = os.getenv('CHECK_CONFIG_COMMAND')
    if command is None:
      return True

    print("Command:" + command)
    
    ok_exit_codes = os.getenv('OK_EXIT_CODES')
    if ok_exit_codes is None:
      ok_exit_codes='0,127'

    return_code = subprocess.call(command, shell=True)
    print("Return code:"+str(return_code))
    config_ok=False
    for code in ok_exit_codes.split(','):
        if int(code) == int(return_code):
          config_ok=True

        if config_ok:
            print(" Config is ok ")
            return True
        else:
            print("Oups Something wrong ")
            return False


def copyToDest(src,dest):
    src_files = os.listdir(src)
    for file_name in src_files:
      full_file_name = os.path.join(src, file_name)
      if (os.path.isfile(full_file_name)):
        shutil.copy(full_file_name, dest)
        print("Created "+file_name + " in " + dest)

def processFiles(sourcepath,destpath,comment):
  tmppath=tempfile.mkdtemp()
  listall = [f for f in os.listdir(sourcepath)]
  listall.sort()
  transform=getTransform()
  if transform :
      transformFiles(transform,listall,sourcepath)
      listall = [f for f in os.listdir(sourcepath)]
      listall.sort()
  appendParts(listall,sourcepath,tmppath,comment)
  copyToDest(tmppath,destpath)
  shutil.rmtree(tmppath)

def main():
    print("Starting config map collector")
    


    label = os.getenv('LABEL')
    if label is None:
        print("Should have added LABEL as environment variable! Exit")
        return -1
    targetFolder = os.getenv('FOLDER')
    if targetFolder is None:
        print("Should have added FOLDER as environment variable! Exit")
        return -1

    method = os.getenv('REQ_METHOD')
    url = os.getenv('REQ_URL')
    payload = os.getenv('REQ_PAYLOAD')

    if os.path.isfile("/var/run/secrets/kubernetes.io/serviceaccount/namespace"):
      config.load_incluster_config()
      with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
        namespace = f.read()
    else:  
      config.load_kube_config()
      namespace="default"

    print("Namespace: "+namespace)
    print("Config for cluster api loaded...")
      
    
    while True:
        try:
            watchForChanges(label, targetFolder, url, method, payload, namespace)
        except ApiException as e:
            print("ApiException when calling kubernetes: %s\n" % e)
        except ProtocolError as e:
            print("ProtocolError when calling kubernetes: %s\n" % e)
        except:
            raise
        
if __name__ == '__main__':
    main()
