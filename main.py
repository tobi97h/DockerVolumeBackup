import yaml
import os
from yaml.loader import SafeLoader
import subprocess
from datetime import datetime
import tarfile
import json
import time
import logging
import logging_loki


# logging
logging.basicConfig(level = logging.INFO)
loki_url = os.getenv("LOKI_URL")
loki_user = os.getenv("LOKI_USER")
loki_password = os.getenv("LOKI_PWD")

logger = logging.getLogger("VolumeBackup")

if loki_url is not None:
    handler = logging_loki.LokiHandler(
        url=loki_url+"/loki/api/v1/push",
        tags={"application": "VolumeBackup"},
        auth=(loki_user, loki_password),
        version="1",
    )
    logger.addHandler(handler)
    logger.info("added loki handler")


# conf
backup_location = os.getenv("BACKUP_LOC")
backup_owner = os.getenv("BACKUP_OWNER")

containers_to_exclude = os.getenv("CONTAINER_EXCLUDE")
print(containers_to_exclude)

# constants
managed_volume_location = "/var/lib/docker/volumes/"

class Deleter:
    def __init__(self, path, days):
        self.path = path
        self.days = days

    def delete(self):
        now = time.time()
        cutoff = now - (self.days * 86400)

        for root, dirs, files in os.walk(self.path, topdown=False):
            for file in files:
                file_path = os.path.join(root, file)
                file_modified_time = os.path.getmtime(file_path)
                if file_modified_time < cutoff:
                    os.remove(file_path)


def set_premission(file):
    p = subprocess.Popen(["chown", f"{backup_owner}:{backup_owner}", file], stdout=subprocess.PIPE)
    (output, err) = p.communicate()
    p_status = p.wait()
    logger.info("Command output : " +  output.decode())
    logger.info("Command exit status/return code : " +  str(p_status))


def service_cmd(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    (output, err) = p.communicate()
    p_status = p.wait()
    logger.info("Command output : " + output.decode())
    logger.info("Command exit status/return code : " + str(p_status))
    return output


def backup_folder(folder, service_name, vol_name):
    backup_name = f"{service_name}-{vol_name}-{datetime.now().strftime('%Y%m%d')}.tar.gz"
    backup_file = os.path.join(backup_location, backup_name)
    with tarfile.open(backup_file, "w:gz") as tar:
        for fn in os.listdir(folder):
            p = os.path.join(folder, fn)
            tar.add(p, arcname=fn)

    set_premission(backup_file)


def backup_container(info):
    name = info["Name"][1:]
    print("backup container: " + name)
    print(info["Mounts"])
    for mount in info["Mounts"]:
        mount_type = mount["Type"]
        if mount_type == "volume":
            # stored in generic location
            backup_folder(mount["Source"], name, mount["Name"])
        elif mount_type == "bind" and "docker.sock" not in mount["Source"]:
            source = mount["Source"]
            backup_folder(source, name, source.split("/")[-1])


def backup(containerIds):
    infos = json.loads(service_cmd(["docker", "inspect"] + containerIds).decode("utf-8"))
    for info in infos:
        backup_container(info)


def backup_main():

    container_ids = service_cmd(["docker", "ps", "-a", "-q"]).decode("utf-8").split("\n")
    logger.info("all containers: " + ", ".join(container_ids))

    container_ids_to_exclude = []

    if containers_to_exclude is not None:
        for container_name in containers_to_exclude.split(","):
            container_ids_to_exclude.append(service_cmd(["docker", "ps", "-aqf", f"name=^{container_name}$"]).decode("utf-8"))

    logger.info("containers to exclude: " + ", ".join(container_ids_to_exclude))
    # exclude what needs to be excluded
    container_ids = [i for i in container_ids if i not in container_ids_to_exclude]


    logger.info("containers that will be stopped: " + ", ".join(container_ids))

    # stop all
    service_cmd(["docker", "stop"] + container_ids)

    try:
        backup(container_ids)
    except Exception as e:
        logger.error(str(e))

    # start all
    service_cmd(["docker", "start"] + container_ids)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    os.makedirs(backup_location, exist_ok=True)

    backup_main()

    # delete backups older than 30 days from fetch location
    Deleter(backup_location, 30).delete()
