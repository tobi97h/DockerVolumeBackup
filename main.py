import yaml
import os
from yaml.loader import SafeLoader
import subprocess
from datetime import datetime
import tarfile
import json

storage_device_to_mount = None
mount_location = None

backup_location = os.getenv("BACKUP_LOC")
backup_owner = os.getenv("BACKUP_OWNER")

# constants
managed_volume_location = "/var/lib/docker/volumes/"


def set_premission(file):
    p = subprocess.Popen(["chown", f"{backup_owner}:{backup_owner}", file], stdout=subprocess.PIPE)
    (output, err) = p.communicate()
    p_status = p.wait()
    print("Command output : ", output.decode())
    print("Command exit status/return code : ", p_status)


def service_cmd(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    (output, err) = p.communicate()
    p_status = p.wait()
    print("Command output : ", output.decode())
    print("Command exit status/return code : ", p_status)
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


def backup_all():
    container_ids = service_cmd(["docker", "ps", "-a", "-q"]).decode("utf-8").split("\n")

    # stop all
    service_cmd(["docker", "stop"] + container_ids)

    backup(container_ids)

    # start all
    service_cmd(["docker", "start"] + container_ids)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    if storage_device_to_mount is not None:
        os.makedirs(mount_location, exist_ok=True)
        service_cmd(["mount", storage_device_to_mount, mount_location])

    os.makedirs(backup_location, exist_ok=True)

    backup_all()

    if storage_device_to_mount is not None:
        service_cmd(["umount", storage_device_to_mount, mount_location])
