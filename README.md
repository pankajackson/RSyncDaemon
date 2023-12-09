# RSyncDaemon

Python based CLI Remote Syncing Daemon service.

### Features

- Real time Remote syncing
- Used secure shell session for data transfer
- Configurable with custom config

### Installation

```bash
pip install rsyncdaemon
```

### Configuration

configuration file present at `~/.rsyncdaemon/rsyncdaemon.conf`.

- please create configuration file if not present.
- replace values with correct values
- remove configs that does not require

#### default configuration:

```bash
[SyncConfig]
local_dir = ""
remote_dir = ""
ssh_host = "localhost"
ssh_port = 22
ssh_username = "jackson"
ssh_password = ""
ssh_private_key_path = ""
rsync_command = "rsync"
rsync_options = [ "-az", "--delete",]
exclude_patterns = []

[LogConfig]
log_file_path = "/home/jackson/.rsyncdaemon/rsyncdaemon.log"
log_max_size = 10485760
log_backup_count = 5

```

#### minimum configuration:

```bash
[SyncConfig]
local_dir = ""
remote_dir = ""
ssh_host = "localhost"
ssh_port = 22
ssh_username = "jackson"
ssh_password = ""
ssh_private_key_path = ""
```

**_NOTE:_**

- Remember to remove one of the option either `ssh_password` or `ssh_private_key_path`
- configuration supports toml file type/format, i.e. it supports list/object inside config file

### Usage

#### with Default config file

```bash
rsyncdaemon
```

#### with Custom config file

```bash
rsyncdaemon -c <config file path>
eg: rsyncdaemon -c ~/Documents/rsyncdaemon_custom_config.conf
```

##### Help

```bash
rsyncdaemon -h
```

##### Version

```bash
rsyncdaemon -v
```

#### Use as a system service

``NOTE: Required sudo permission``

```bash

# install Package
sudo pip install rsyncdaemon

# Create rsyncdaemon home directory somewhere. for eg /tmp/rsyncdaemon/
mkdir /tmp/rsyncdaemon/

# create config file at /tmp/rsyncdaemon/rsyncdaemon.conf inside rsyncdaemon home directory created above


[SyncConfig]
local_dir = ""
remote_dir = ""
ssh_host = "localhost"
ssh_port = 22
ssh_username = ""
ssh_password = ""
ssh_private_key_path = ""
rsync_command = "rsync"
rsync_options = [ "-az", "--delete",]
exclude_patterns = []

[LogConfig]
log_file_path = "/var/log/rsyncdaemon.log"
log_max_size = 10485760
log_backup_count = 5
# replace with correct values


# create service file at /etc/systemd/system/rsyncdaemon.service  with following content

[Unit]
Description=RSync daemon Service
After=network.target

[Service]
User=root
Group=root
ExecStart=/usr/bin/rsyncdaemon -c /tmp/rsyncdaemon/rsyncdaemon.conf
Restart=always

[Install]
WantedBy=multi-user.target

# Reloading Change to Systemd Unit Files
sudo systemctl daemon-reload

# Start service
sudo systemctl start rsyncdaemon

# Enable service to start on boot
sudo systemctl enable rsyncdaemon

# check status
sudo systemctl status rsyncdaemon

# check logs
sudo tail -f /var/log/rsyncdaemon.log

# To stop service
sudo systemctl stop rsyncdaemon

# To remove service
sudo systemctl disable rsyncdaemon
sudo rm /etc/systemd/system/rsyncdaemon.service

```

### Uninstall

```bash
pip uninstall rsyncdaemon
```

### Who do I talk to?

- Repo owner or admin
- Other community or team contact
