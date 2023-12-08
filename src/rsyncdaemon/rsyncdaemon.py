import os
import pwd
import toml
import subprocess
import logging
from logging.handlers import RotatingFileHandler
import time
import fnmatch
import pathlib
import paramiko
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


""" Sample conf file at ~/.rsyncdaemon/rsyncdaemon.conf
[SyncConfig]
local_dir = "/home/jackson/WorkSpace/RemoteSyncDeamon/TestDirectory"
remote_dir = "/tmp/TestDirectory"
ssh_host = "192.168.1.28"
ssh_port = 22
ssh_username = "jackson"
ssh_private_key_path = ""
ssh_password = ""
rsync_command = "rsync"
rsync_options = ["-az", "--delete"]
exclude_patterns = ["exclude_dir", "*.log", "pankaj.txt"]
log_file_path = "/home/jackson/.rsyncdaemon/rsyncdaemon.log"
log_max_size = 10485760
"""


def toml_conf_reader():
    defaults = {
        "local_dir": None,
        "remote_dir": None,
        "ssh_host": "localhost",
        "ssh_port": 22,
        "ssh_user": os.getenv("USER"),
        "ssh_private_key_path": None,
        "ssh_password": None,
        "rsync_command": "rsync",
        "rsync_options": ["-az", "--delete"],
        "exclude": [],
        "config_file_path": str(
            os.path.join(
                os.path.join(pwd.getpwuid(os.getuid()).pw_dir, ".rsyncdaemon"),
                "rsyncdaemon.conf",
            )
        ),
        "log_file_path": str(
            os.path.join(
                os.path.join(pwd.getpwuid(os.getuid()).pw_dir, ".rsyncdaemon"),
                "rsyncdaemon.log",
            )
        ),
        "log_max_size": 10 * 1024 * 1024,  # 10MB
        "log_backup_count": 5,
    }
    # Read configuration from  ~/.rsyncdaemon/rsyncdaemon.conf
    with open(defaults["config_file_path"], "r") as f:
        config = toml.load(f)

    config = {
        "local_dir": config["SyncConfig"].get("local_dir", defaults["local_dir"]),
        "remote_dir": config["SyncConfig"].get("remote_dir", defaults["remote_dir"]),
        "ssh_host": config["SyncConfig"].get("ssh_host", defaults["ssh_host"]),
        "ssh_port": int(config["SyncConfig"].get("ssh_port", defaults["ssh_port"])),
        "ssh_user": config["SyncConfig"].get("ssh_username", defaults["ssh_user"]),
        "ssh_private_key_path": config["SyncConfig"].get(
            "ssh_private_key_path", defaults["ssh_private_key_path"]
        ),
        "ssh_password": config["SyncConfig"].get(
            "ssh_password", defaults["ssh_password"]
        ),
        "rsync_command": config["SyncConfig"].get(
            "rsync_command", defaults["rsync_command"]
        ),
        "rsync_options": config["SyncConfig"].get(
            "rsync_options", defaults["rsync_options"]
        ),
        "exclude_patterns": config["SyncConfig"].get("exclude", defaults["exclude"]),
        "log_file_path": config["SyncConfig"].get(
            "log_file_path", defaults["log_file_path"]
        ),
        "log_max_size": int(
            config["SyncConfig"].get("log_max_size", defaults["log_max_size"])
        ),  # 10 MB
        "log_backup_count": int(
            config["SyncConfig"].get("log_backup_count", defaults["log_backup_count"])
        ),
    }
    return config


def get_config():
    return toml_conf_reader()


config = get_config()
local_dir = config["local_dir"]
remote_dir = config["remote_dir"]
ssh_host = config["ssh_host"]
ssh_port = int(config["ssh_port"])
ssh_user = config["ssh_user"]
ssh_private_key_path = config["ssh_private_key_path"]
ssh_password = config["ssh_password"]
rsync_command = config["rsync_command"]
rsync_options = config["rsync_options"]
exclude_patterns = config["exclude_patterns"]
log_file_path = config["log_file_path"]
log_max_size = int(config["log_max_size"])  # 10 MB
log_backup_count = int(config["log_backup_count"])


# Configure logging
logger = logging.getLogger("")
logger.setLevel(logging.INFO)
file_handler = RotatingFileHandler(
    log_file_path, maxBytes=log_max_size, backupCount=log_backup_count
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
# Add rotating file handler to the root logger
logger.addHandler(file_handler)


# Initialize SSH client
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())


def is_excluded(path):
    """Check if the path matches any exclude pattern."""
    path = pathlib.PurePosixPath(path).relative_to(local_dir)
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(path, pattern):
            return True
    return False


def sync_directories(event):
    exclude_options = [f"--exclude={pattern}" for pattern in exclude_patterns]
    if ssh_private_key_path:
        command = [
            rsync_command,
            *rsync_options,
            *exclude_options,
            "-e",
            f"ssh -i {ssh_private_key_path} -p {ssh_port}",
            f"{local_dir}/",
            f"{ssh_user}@{ssh_host}:{remote_dir}/",
        ]
    elif ssh_password:
        command = [
            "sshpass",
            "-p",
            f"{ssh_password}",
            rsync_command,
            *rsync_options,
            *exclude_options,
            "-e",
            f"ssh -p {ssh_port}",
            f"{local_dir}/",
            f"{ssh_user}@{ssh_host}:{remote_dir}/",
        ]
    else:
        command = [
            rsync_command,
            *rsync_options,
            *exclude_options,
            "-e",
            f"ssh -p {ssh_port}",
            f"{local_dir}/",
            f"{ssh_user}@{ssh_host}:{remote_dir}/",
        ]
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for the process to finish
        process.wait()
        # Check for errors
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, command)

        logging.info(f"SYNC_SUCCESS: {event.event_type}: {event.src_path}.")
    except subprocess.CalledProcessError as e:
        logging.error(f"SYNC_FAILED: {event.event_type}: {event.src_path}.")
        logging.error(f"Error syncing directories: {e}")
    except Exception as e:
        logging.error(f"SYNC_FAILED: {event.event_type}: {event.src_path}.")
        logging.error(f"An unexpected error occurred: {e}")


class FSHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
        if not is_excluded(event.src_path):
            sync_directories(event)

    def on_created(self, event):
        if event.is_directory:
            return
        if not is_excluded(event.src_path):
            sync_directories(event)


def start_sync():
    event_handler = FSHandler()
    observer = Observer()
    observer.schedule(event_handler, path=local_dir, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def main():
    try:
        if ssh_private_key_path:
            ssh.connect(
                ssh_host,
                port=ssh_port,
                username=ssh_user,
                key_filename=ssh_private_key_path,
            )
        elif ssh_password:
            ssh.connect(
                ssh_host, port=ssh_port, username=ssh_user, password=ssh_password
            )
        else:
            ssh.connect(ssh_host, port=ssh_port, username=ssh_user)
        start_sync()
    except Exception as e:
        logging.error(f"Error connecting to the remote host: {e}")
    finally:
        ssh.close()


if __name__ == "__main__":
    main()
