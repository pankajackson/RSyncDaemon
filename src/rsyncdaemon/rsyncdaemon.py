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
import argparse
import pkg_resources


rsyncdaemon_home = os.path.join(pwd.getpwuid(os.getuid()).pw_dir, ".rsyncdaemon")
config_file_path = os.path.join(rsyncdaemon_home, "rsyncdaemon.conf")

if not os.path.exists(rsyncdaemon_home):
    os.makedirs(rsyncdaemon_home)

version = pkg_resources.get_distribution("rsyncdaemon").version

defaults = {
    "local_dir": None,
    "remote_dir": None,
    "ssh_host": "localhost",
    "ssh_port": 22,
    "ssh_username": os.getenv("USER"),
    "ssh_private_key_path": None,
    "ssh_password": None,
    "rsync_command": "rsync",
    "rsync_options": ["-az", "--delete"],
    "exclude_patterns": [],
    "log_file_path": str(
        os.path.join(
            os.path.join(pwd.getpwuid(os.getuid()).pw_dir, ".rsyncdaemon"),
            "rsyncdaemon.log",
        )
    ),
    "log_max_size": 10 * 1024 * 1024,  # 10MB
    "log_backup_count": 5,
}


def conf_initializer(config_file_path=config_file_path):
    if not os.path.exists(config_file_path):
        file = open(config_file_path, "w")
        config = {
            "SyncConfig": {
                "local_dir": "",
                "remote_dir": "",
                "ssh_host": defaults["ssh_host"],
                "ssh_port": defaults["ssh_port"],
                "ssh_username": defaults["ssh_username"],
                "ssh_password": defaults["ssh_username"],
                "ssh_private_key_path": "",
                "ssh_password": "",
                "rsync_command": defaults["rsync_command"],
                "rsync_options": defaults["rsync_options"],
                "exclude_patterns": defaults["exclude_patterns"],
            },
            "LogConfig": {
                "log_file_path": defaults["log_file_path"],
                "log_max_size": defaults["log_max_size"],
                "log_backup_count": defaults["log_backup_count"],
            },
        }
        toml.dump(config, file)
        file.close()
        print(f"Please configure config file {config_file_path}")
    return config_file_path


conf_initializer()


def toml_conf_reader():
    # Read configuration from  ~/.rsyncdaemon/rsyncdaemon.conf
    with open(config_file_path, "r") as f:
        toml_config = toml.load(f)

    config = {
        "local_dir": toml_config["SyncConfig"].get("local_dir", defaults["local_dir"]),
        "remote_dir": toml_config["SyncConfig"].get(
            "remote_dir", defaults["remote_dir"]
        ),
        "ssh_host": toml_config["SyncConfig"].get("ssh_host", defaults["ssh_host"]),
        "ssh_port": int(
            toml_config["SyncConfig"].get("ssh_port", defaults["ssh_port"])
        ),
        "ssh_username": toml_config["SyncConfig"].get(
            "ssh_username", defaults["ssh_username"]
        ),
        "ssh_private_key_path": toml_config["SyncConfig"].get(
            "ssh_private_key_path", defaults["ssh_private_key_path"]
        ),
        "ssh_password": toml_config["SyncConfig"].get(
            "ssh_password", defaults["ssh_password"]
        ),
        "rsync_command": toml_config["SyncConfig"].get(
            "rsync_command", defaults["rsync_command"]
        ),
        "rsync_options": toml_config["SyncConfig"].get(
            "rsync_options", defaults["rsync_options"]
        ),
        "exclude_patterns": toml_config["SyncConfig"].get(
            "exclude_patterns", defaults["exclude_patterns"]
        ),
        "log_file_path": toml_config["LogConfig"].get(
            "log_file_path", defaults["log_file_path"]
        ),
        "log_max_size": int(
            toml_config["LogConfig"].get("log_max_size", defaults["log_max_size"])
        ),  # 10 MB
        "log_backup_count": int(
            toml_config["LogConfig"].get(
                "log_backup_count", defaults["log_backup_count"]
            )
        ),
    }
    return config


def get_config():
    return toml_conf_reader()


try:
    config = get_config()
    local_dir = config["local_dir"]
    remote_dir = config["remote_dir"]
    ssh_host = config["ssh_host"]
    ssh_port = int(config["ssh_port"])
    ssh_user = config["ssh_username"]
    ssh_private_key_path = config["ssh_private_key_path"]
    ssh_password = config["ssh_password"]
    rsync_command = config["rsync_command"]
    rsync_options = config["rsync_options"]
    exclude_patterns = config["exclude_patterns"]
    log_file_path = config["log_file_path"]
    log_max_size = int(config["log_max_size"])  # 10 MB
    log_backup_count = int(config["log_backup_count"])
except KeyError:
    raise Exception(f"Please configure config file {config_file_path}")


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


def stop_sync():
    # Add any cleanup steps if needed
    observer = Observer()
    observer.stop()
    observer.join()


def main():
    global config_file_path
    parser = argparse.ArgumentParser(
        prog="rsyncdaemon",
        epilog="Please report bugs at pankajackson@live.co.uk",
        description="Sync local directory to remote directory",
    )
    parser.add_argument(
        "-c",
        "--config",
        required=False,
        action="store_true",
        help=f"Config file path. default: {config_file_path}",
    )
    parser.add_argument(
        "-v", "--version", required=False, action="store_true", help="Show version"
    )

    args = parser.parse_args()
    if args.version:
        print(f"rsyncdaemon: {version}")
    else:
        if args.config:
            config_file_path = args.config
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
            raise Exception(f"Error connecting to the remote host: {e}")


if __name__ == "__main__":
    main()
