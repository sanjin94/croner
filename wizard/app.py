import subprocess
import logging
import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler("script.log"), logging.StreamHandler()]
)

app = FastAPI()

class Message(BaseModel):
    text: str

# listening for pod creation message
@app.post("/create_pod")
async def creation(message: Message):
    if "create_pod," in message.text.lower():
        logging.info(f"Recieved following message: {message}")
        receipt = message.split(",")
        #  collect deployment info to inject it in yaml file
        #+ for sending the message after task complete
        deployment_info = collect_deployment_info()
        #  template yaml file update with received instructions and
        #+ deployment info (service where FastAPI is listening)
        inject_receipt_to_yaml(receipt[1:], deployment_info)
        logging.info(f"Commands injected: {[receipt[i] for i in range(2,len(receipt))]}")
        # applying updated yaml template
        kubectl_apply()
        logging.info(f"Pod {receipt[1]} created: {message}")
    else:
        # raise an exception for unknown messages
        raise HTTPException(status_code=400, detail="Unknown message")

@app.post("/terminate_pod")
async def termination(message: Message):
    if "terminate_pod," in message.text.lower():
        logging.info(f"Recieved following message: {message}")
        # parsing pod name from message and calling delete method
        kubectl_delete(message.split(",")[1])
        logging.info(f"Pod {message.split(',')[1]} deleted")
    else:
        # raise an exception for unknown messages
        raise HTTPException(status_code=400, detail="Unknown message")

def collect_deployment_info():
    svc_raw = subprocess.check_output(["kubectl", "get", "services"]).strip()
    svc_str = svc_raw.decode("utf-8")
    svc_list = [line.split() for line in svc_str.splitlines()]
    target_list = [row for row in svc_list if row[0].startswith("croner-wizard")][0]
    #  needed information is cluster-ip and port so the service can send termination
    #+ message after job is complete... returning ['cluster-ip', 'port_number']
    logging.info(f"Application service {target_list[0]} can be accessed on {target_list[2]}:{target_list[2].split(':')[0].split('/')[0]}")
    return [target_list[2], target_list[2].split(':')[0].split('/')[0]]

def inject_receipt_to_yaml(receipt, deployment_info):
    with open("templates/temp_pod.yaml", "r") as f:
        yaml_template = f.read()
    # termination message to be sent after task is finished
    message = f"terminate_pod,{receipt[0]}"
    yaml_dict = yaml.safe_load(yaml_template)
    # defining pod name
    yaml_dict['metadata']['name'] = receipt[0]
    # injection of commands that will run in pod
    yaml_dict['spec']['containers'][0]['args'] = [
                                                    " ".join(receipt[1:]), 
                                                    f"curl -XPOST -d {message} {deployment_info[0]}:{deployment_info[1]}"
                                                ]
    # saving template so it can be applyed
    with open("templates/temp_pod.yaml", "w") as f:
       f.write(yaml.dump(yaml_dict))

def kubectl_apply():
    # creating new pod based on injected specification in template pod 
    subprocess.run(["kubectl", "apply", "-f", "templates/temp_pod.yaml"])

def kubectl_delete(pod_name):
    # deleting pod after it is done
    subprocess.run(["kubectl", "delete", "pod", pod_name])
