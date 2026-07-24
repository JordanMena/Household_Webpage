# BeagleBone deployment

This deployment targets Debian 11 and Python 3.9. The Flask development server
in `run.py` remains available for development; the system service uses Gunicorn
through `wsgi.py`.

The commands below assume:

- the Linux account is `debian`;
- the repository is `/home/debian/Household_Webpage`;
- the site should be available on LAN port `8000`.

If your username or repository location differs, change `User`, `Group`,
`WorkingDirectory`, and `ExecStart` in `deploy/household-webpage.service` before
installing it.

## 1. Back up the existing data

Stop the old application first if it is running, then create a backup directory:

```sh
cd /home/debian/Household_Webpage
mkdir -p "$HOME/household-webpage-backup"
cp -p home_page/site.db "$HOME/household-webpage-backup/site.db"
cp -a home_page/static/profile_pics "$HOME/household-webpage-backup/"
cp -a home_page/static/recipe_photos "$HOME/household-webpage-backup/"
```

The database and uploaded images are intentionally ignored by Git, so pulling
code will not back them up or replace them.

## 2. Create the Python environment

Install the Debian packages needed to create the environment and compile older
Python dependencies:

```sh
sudo apt update
sudo apt install python3-venv python3-dev build-essential libffi-dev
cd /home/debian/Household_Webpage
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade "pip<25"
.venv/bin/python -m pip install -r requirements-production.txt
```

Confirm that the application imports:

```sh
.venv/bin/python -c "from wsgi import app; print(app.url_map)"
```

## 3. Configure and test Gunicorn

Run Gunicorn in the foreground:

```sh
cd /home/debian/Household_Webpage
.venv/bin/gunicorn --workers 1 --bind 0.0.0.0:8000 wsgi:app
```

From another device on the LAN, open:

```text
http://BEAGLEBONE_IP_ADDRESS:8000
```

Press `Ctrl+C` after confirming that the page loads.

## 4. Install the system service

Review the service paths before copying it:

```sh
cd /home/debian/Household_Webpage
nano deploy/household-webpage.service
```

Install the service and its configuration:

```sh
sudo cp deploy/household-webpage.service /etc/systemd/system/
sudo cp deploy/household-webpage.env.example /etc/default/household-webpage
sudo nano /etc/default/household-webpage
sudo systemctl daemon-reload
sudo systemctl enable --now household-webpage
```

Check its status and recent logs:

```sh
systemctl status household-webpage
journalctl -u household-webpage -n 100 --no-pager
```

Follow logs while troubleshooting:

```sh
journalctl -u household-webpage -f
```

Existing installations that use `/etc/config.json` remain supported. Values
from `/etc/default/household-webpage` take precedence, and local development
falls back to `home_page/site.db` when neither configuration file exists.

## Updating the application

After pulling tested code, install any dependency changes and restart:

```sh
cd /home/debian/Household_Webpage
git pull --ff-only
.venv/bin/python -m pip install -r requirements-production.txt
sudo systemctl restart household-webpage
systemctl status household-webpage
```

## Common service commands

```sh
sudo systemctl start household-webpage
sudo systemctl stop household-webpage
sudo systemctl restart household-webpage
sudo systemctl disable household-webpage
```
