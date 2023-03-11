# Project

This project will dynamically shut down all docker containers, find their mapped volumes and back them up to a select location.

# Init / Structure


Install the following dependencies:
```
apt install python3-pip
pip3 install --upgrade pip
```

Setup the cron job:

```
crontab -e
BACKUP_LOC=
BACKUP_OWNER=
0 0 * * 0 python3 /path/to/main.py
```

This will setup the cron job to run once every week on sunday at 00:00.
https://crontab.guru/every-week

