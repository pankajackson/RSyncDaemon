import os
import pwd
import toml

defaults = {
    "AppConfig": {
        "app_home": os.path.join(pwd.getpwuid(os.getuid()).pw_dir, ".rsyncdaemon"),
        "app_config_file_path": os.path.join(
            os.path.join(pwd.getpwuid(os.getuid()).pw_dir, ".rsyncdaemon"),
            "rsyncdaemon.conf",
        ),
    },
    "SyncConfig": {
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
    },
    "LogConfig": {
        "log_file_path": str(
            os.path.join(
                os.path.join(pwd.getpwuid(os.getuid()).pw_dir, ".rsyncdaemon"),
                "rsyncdaemon.log",
            )
        ),
        "log_max_size": 10 * 1024 * 1024,  # 10MB
        "log_backup_count": 5,
    },
}


def conf_initializer(config_file_path):
    if not os.path.exists(config_file_path):
        file = open(config_file_path, "w")
        config = {
            "SyncConfig": {
                "local_dir": "",
                "remote_dir": "",
                "ssh_host": defaults["SyncConfig"]["ssh_host"],
                "ssh_port": defaults["SyncConfig"]["ssh_port"],
                "ssh_username": defaults["SyncConfig"]["ssh_username"],
                "ssh_password": defaults["SyncConfig"]["ssh_username"],
                "ssh_private_key_path": "",
                "ssh_password": "",
                "rsync_command": defaults["SyncConfig"]["rsync_command"],
                "rsync_options": defaults["SyncConfig"]["rsync_options"],
                "exclude_patterns": defaults["SyncConfig"]["exclude_patterns"],
            },
            "LogConfig": {
                "log_file_path": defaults["LogConfig"]["log_file_path"],
                "log_max_size": defaults["LogConfig"]["log_max_size"],
                "log_backup_count": defaults["LogConfig"]["log_backup_count"],
            },
        }
        toml.dump(config, file)
        file.close()
        print(f"Please configure config file {config_file_path}")
    return config_file_path


def get_value_of(key, config_file_path):
    # Read configuration from  ~/.rsyncdaemon/rsyncdaemon.conf
    with open(config_file_path, "r") as f:
        toml_config = toml.load(f)

    if key.startswith("log_"):
        try:
            return toml_config["LogConfig"][key]
        except KeyError:
            return defaults["LogConfig"][key]
    elif key.startswith("app_"):
        try:
            return toml_config["AppConfig"][key]
        except KeyError:
            return defaults["AppConfig"][key]
    else:
        try:
            return toml_config["SyncConfig"][key]
        except KeyError:
            return defaults["SyncConfig"][key]


def toml_conf_reader(config_file_path):
    config = {
        "local_dir": get_value_of("local_dir", config_file_path),
        "remote_dir": get_value_of("remote_dir", config_file_path),
        "ssh_host": get_value_of("ssh_host", config_file_path),
        "ssh_port": int(
            get_value_of("ssh_port", config_file_path),
        ),
        "ssh_username": get_value_of("ssh_username", config_file_path),
        "ssh_private_key_path": get_value_of("ssh_private_key_path", config_file_path),
        "ssh_password": get_value_of("ssh_password", config_file_path),
        "rsync_command": get_value_of("rsync_command", config_file_path),
        "rsync_options": get_value_of("rsync_options", config_file_path),
        "exclude_patterns": get_value_of("exclude_patterns", config_file_path),
        "log_file_path": get_value_of("log_file_path", config_file_path),
        "log_max_size": int(
            get_value_of("log_max_size", config_file_path),
        ),  # 10 MB
        "log_backup_count": int(
            get_value_of("log_backup_count", config_file_path),
        ),
    }
    return config


def get_config(config_file_path=defaults["AppConfig"]["app_config_file_path"]):
    if not os.path.exists(defaults["AppConfig"]["app_home"]):
        os.makedirs(defaults["AppConfig"]["app_home"])

    conf_initializer(config_file_path)
    return toml_conf_reader(config_file_path)
