# Requirements

* python3
* pip3

```
apt install python3-pip
pip3 install --upgrade pip

crontab -e
0 0 * * 0 python3 /path/to/main.py
```

This will setup the cron job to run once every week on sunday at 00:00.
https://crontab.guru/every-week

