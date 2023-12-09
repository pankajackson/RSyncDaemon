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
from rsyncdaemon.confbuilder import get_config, defaults


def get_version():
    return pkg_resources.get_distribution("rsyncdaemon").version


# Configure logging
def init_logger(log_file_path, log_max_size, log_backup_count):
    logger = logging.getLogger("")
    logger.setLevel(logging.INFO)
    file_handler = RotatingFileHandler(
        log_file_path, maxBytes=log_max_size, backupCount=log_backup_count
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s")
    )
    # Add rotating file handler to the root logger
    logger.addHandler(file_handler)


# Initialize SSH client
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())


def is_excluded(path, local_dir, exclude_patterns):
    """Check if the path matches any exclude pattern."""
    path = pathlib.PurePosixPath(path).relative_to(local_dir)
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(path, pattern):
            return True
    return False


def sync_directories(event, config):
    exclude_options = [f"--exclude={pattern}" for pattern in config["exclude_patterns"]]
    if config["ssh_private_key_path"]:
        command = [
            config["rsync_command"],
            *config["rsync_options"],
            *config["exclude_options"],
            "-e",
            f"ssh -i {config['ssh_private_key_path']} -p {config['ssh_port']}",
            f"{config['local_dir']}/",
            f"{config['ssh_username']}@{config['ssh_host']}:{config['remote_dir']}/",
        ]
    elif config["ssh_password"]:
        command = [
            "sshpass",
            "-p",
            f"{config['ssh_password']}",
            config["rsync_command"],
            *config["rsync_options"],
            *exclude_options,
            "-e",
            f"ssh -p {config['ssh_port']}",
            f"{config['local_dir']}/",
            f"{config['ssh_username']}@{config['ssh_host']}:{config['remote_dir']}/",
        ]
    else:
        command = [
            config["rsync_command"],
            *config["rsync_options"],
            *exclude_options,
            "-e",
            f"ssh -p {config['ssh_port']}",
            f"{config['local_dir']}/",
            f"{config['ssh_username']}@{config['ssh_host']}:{config['remote_dir']}/",
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
    def __init__(self, config) -> None:
        self.config = config
        super().__init__()

    def on_modified(self, event):
        if event.is_directory:
            return
        if not is_excluded(
            path=event.src_path,
            local_dir=self.config["local_dir"],
            exclude_patterns=self.config["exclude_patterns"],
        ):
            sync_directories(event, self.config)

    def on_created(self, event):
        if event.is_directory:
            return
        if not is_excluded(
            path=event.src_path,
            local_dir=self.config["local_dir"],
            exclude_patterns=self.config["exclude_patterns"],
        ):
            sync_directories(event, self.config)


def start_sync(config):
    event_handler = FSHandler(config=config)
    observer = Observer()
    observer.schedule(event_handler, path=config["local_dir"], recursive=True)
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
    parser = argparse.ArgumentParser(
        prog="rsyncdaemon",
        epilog="Please report bugs at pankajackson@live.co.uk",
        description="Sync local directory to remote directory",
    )
    parser.add_argument(
        "-c",
        "--config",
        required=False,
        type=str,
        help=f"Config file path. default: ~/.rsyncdaemon/rsyncdaemon.conf",
        metavar="<path>",
    )
    parser.add_argument(
        "-v", "--version", required=False, action="store_true", help="Show version"
    )

    args = parser.parse_args()
    if args.version:
        print(f"rsyncdaemon: {get_version()}")
    else:
        config_file_path = defaults["config_file_path"]
        if args.config:
            config_file_path = args.config
        config = get_config(config_file_path)
        try:
            init_logger(
                log_file_path=config["log_file_path"],
                log_max_size=config["log_max_size"],
                log_backup_count=["log_backup_count"],
            )

            if config["ssh_private_key_path"]:
                ssh.connect(
                    config["ssh_host"],
                    port=config["ssh_port"],
                    username=config["ssh_username"],
                    key_filename=config["ssh_private_key_path"],
                )
            elif config["ssh_password"]:
                ssh.connect(
                    config["ssh_host"],
                    port=config["ssh_port"],
                    username=config["ssh_username"],
                    password=config["ssh_password"],
                )
            else:
                ssh.connect(
                    config["ssh_host"],
                    port=config["ssh_port"],
                    username=config["ssh_username"],
                )
            start_sync(config)
        except Exception as e:
            logging.error(f"Error connecting to the remote host: {e}")
            raise Exception(f"Error connecting to the remote host: {e}")


if __name__ == "__main__":
    main()
