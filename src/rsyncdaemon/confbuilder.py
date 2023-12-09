import os
import pwd
import toml

defaults = {
    "app_home": os.path.join(pwd.getpwuid(os.getuid()).pw_dir, ".rsyncdaemon"),
    "config_file_path": os.path.join(
        os.path.join(pwd.getpwuid(os.getuid()).pw_dir, ".rsyncdaemon"),
        "rsyncdaemon.conf",
    ),
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


def conf_initializer(config_file_path):
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


def toml_conf_reader(config_file_path):
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


def get_config(config_file_path=defaults["config_file_path"]):
    if not os.path.exists(defaults["app_home"]):
        os.makedirs(defaults["app_home"])

    conf_initializer(config_file_path)
    return toml_conf_reader(config_file_path)
