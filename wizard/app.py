import subprocess
import logging
import yaml
import time
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
        receipt = message.text.split(",")
        #  template yaml file update with received instructions 
        inject_receipt_to_yaml(receipt[1:])
        logging.info(f"Commands injected: {[receipt[i] for i in range(2,len(receipt))]} to start pod {receipt[1]}")
        # applying updated yaml template
        subprocess.run(["KUBECONFIG=config"])
        kubectl_apply()
        logging.info(f"Pod {receipt[1]} created!")
        clean(receipt[1])
        logging.info(f"Pod {receipt[1]} deleted!")
    else:
        # raise an exception for unknown messages
        raise HTTPException(status_code=400, detail="Unknown message")

def clean(pod_name):
    while True:
        svc_raw = subprocess.check_output(["kubectl", "get", "pods"]).strip()
        svc_str = svc_raw.decode("utf-8")
        svc_list = [line.split() for line in svc_str.splitlines()]
        target_list = [row for row in svc_list if row[0].startswith(pod_name)][0]
        if target_list[2] == "Completed":
            kubectl_delete(pod_name)
            return
        else:
            time.sleep(60)

def inject_receipt_to_yaml(receipt):
    with open("templates/temp_pod.yaml", "r") as f:
        yaml_template = f.read()
    # termination message to be sent after task is finished
    yaml_dict = yaml.safe_load(yaml_template)
    # defining pod name
    yaml_dict['metadata']['name'] = receipt[0]
    # injection of commands that will run in pod
    yaml_dict['spec']['containers'][0]['args'] = [" ".join(receipt[1:])]
    # saving template so it can be applyed
    with open("templates/temp_pod.yaml", "w") as f:
       f.write(yaml.dump(yaml_dict))

def kubectl_apply():
    # creating new pod based on injected specification in template pod 
    subprocess.run(["kubectl", "apply", "-f", "templates/temp_pod.yaml"])

def kubectl_delete(pod_name):
    # deleting pod after it is done
    subprocess.run(["kubectl", "delete", "pod", pod_name])
