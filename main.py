import yaml
import os
from yaml.loader import SafeLoader
import subprocess
from datetime import datetime
import tarfile

storage_device_to_mount = None
compose_locations = [
    "/home/tobi/Documents/WebServices/docker-compose.yaml",
    "/home/tobi/Documents/WebServicesJitcom/docker-compose.yaml",
]
mount_location = "/mnt/temp_compose_backup_mount" # set to none if not needed and just backup to disk
backup_location = "/home/tobi/backups"
backup_owner = "tobi"

# constants
managed_volume_location = "/var/lib/docker/volumes/"

# arapiscaffold_vmysql

class BackupCompose:

    def __init__(self, parsed_compose, compose_file_path):
        self.parsed_compose = parsed_compose
        self.compose_file_path = compose_file_path
        self.folder_file_path = os.path.dirname(self.compose_file_path)
        self.project_folder_name = os.path.basename(self.folder_file_path)

    def backup(self):
        # stop all services
        self.service_cmd(["docker", "compose", "stop"])

        for service_name in self.parsed_compose["services"]:
            print(service_name)
            self.backup_service(service_name)

        # start them again
        self.service_cmd(["docker", "compose", "start"])

    def service_cmd(self, cmd):
        p = subprocess.Popen(cmd, cwd=self.folder_file_path, stdout=subprocess.PIPE)
        (output, err) = p.communicate()
        p_status = p.wait()
        print("Command output : ", output.decode())
        print("Command exit status/return code : ", p_status)

    def backup_folder(self, folder, service_name):
        backup_name = f"{self.project_folder_name}-{service_name}-{datetime.now().strftime('%Y%m%d')}.tar.gz"
        backup_file = os.path.join(backup_location, backup_name)
        with tarfile.open(backup_file, "w:gz") as tar:
            for fn in os.listdir(folder):
                p = os.path.join(folder, fn)
                tar.add(p, arcname=fn)

        self.set_premission(backup_file)

    def set_premission(self, file):
        p = subprocess.Popen(["chown", f"{backup_owner}:{backup_owner}", file], stdout=subprocess.PIPE)
        (output, err) = p.communicate()
        p_status = p.wait()
        print("Command output : ", output.decode())
        print("Command exit status/return code : ", p_status)

    def backup_service(self, service_name):
        service = self.parsed_compose["services"][service_name]
        print(service)

        # backup any volumes that the service might have
        if "volumes" in service:
            volumes = service["volumes"]
            for volume in volumes:
                self.backup_volume(volume, service_name)

    def backup_volume(self, volume, service_name):
        # stop the service
        vol_name = volume.split(":")[0]
        print(volume)
        if volume.startswith("./"):
            # locally bindet volume
            print("saving folder mapped volume")
            self.backup_folder(os.path.join(self.folder_file_path, vol_name[2:]), service_name)
        elif "docker.sock" not in volume:
            # dont save mapped socket
            print("saving managed volume")
            self.backup_folder(os.path.join(managed_volume_location, f"{self.project_folder_name.lower()}_{vol_name}"),
                               service_name)

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    if storage_device_to_mount is not None:
        os.makedirs(mount_location, exist_ok=True)
        p = subprocess.Popen(["mount", storage_device_to_mount, mount_location], stdout=subprocess.PIPE)
        (output, err) = p.communicate()
        p_status = p.wait()
        print("Command output : ", output.decode())
        print("Command exit status/return code : ", p_status)

    os.makedirs(backup_location, exist_ok=True)

    for compose in compose_locations:
        base_location = os.path.dirname(compose)
        with open(compose) as c:
            yaml_compose = yaml.load(c, Loader=SafeLoader)
            BackupCompose(yaml_compose, compose).backup()

    if storage_device_to_mount is not None:
        p = subprocess.Popen(["umount", storage_device_to_mount, mount_location], stdout=subprocess.PIPE)
        (output, err) = p.communicate()
        p_status = p.wait()
        print("Command output : ", output.decode())
        print("Command exit status/return code : ", p_status)