# Oracle Cloud VM Deployment (Ubuntu, 1 GB RAM, AMD)

This is the lightest production setup for your VM:
- No Docker
- Frontend served directly by Nginx
- Backend runs as a `systemd` service from Python `venv`

## 1) Prepare the VM

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git nginx certbot python3-certbot-nginx python3-venv python3-pip
```

## 2) Add swap (critical for 1 GB RAM)

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
```

Optional memory tuning:

```bash
echo 'vm.swappiness=80' | sudo tee /etc/sysctl.d/99-swappiness.conf
sudo sysctl -p /etc/sysctl.d/99-swappiness.conf
```

## 3) Clone project and configure env

```bash
sudo mkdir -p /opt/plagiarism-checker
sudo chown -R $USER:$USER /opt/plagiarism-checker
cd /opt/plagiarism-checker
git clone <your-repo-url> .
cp backend/.env.example backend/.env
```

Edit `backend/.env`:
- `GEMINI_API_KEY=...`
- `FRONTEND_ORIGIN=https://your-domain.com`
- `MAX_CANDIDATE_PAPERS=2` (recommended on 1 GB)

## 4) Create backend venv and install deps

```bash
cd /opt/plagiarism-checker/backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
```

## 5) Configure systemd backend service

```bash
sudo cp /opt/plagiarism-checker/deploy/oracle/plagiarism-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now plagiarism-backend
sudo systemctl status plagiarism-backend --no-pager
```

Quick health check:

```bash
curl -sS http://127.0.0.1:8000/api/health
```

If your VM username is not `ubuntu`, edit `/etc/systemd/system/plagiarism-backend.service` and change `User=` / `Group=`.

## 6) Configure Nginx (frontend + API reverse proxy)

```bash
sudo cp /opt/plagiarism-checker/deploy/oracle/nginx-plagiarism.conf /etc/nginx/conf.d/plagiarism.conf
sudo nano /etc/nginx/conf.d/plagiarism.conf
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx
```

In `server_name`, set your domain:
- `your-domain.com`
- `www.your-domain.com` (optional)

## 7) Oracle ingress + Ubuntu firewall

Open these in Oracle VCN Security List / NSG:
- TCP `80` from `0.0.0.0/0`
- TCP `443` from `0.0.0.0/0`
- TCP `22` only from your IP

If `ufw` is enabled:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

## 8) Enable HTTPS

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

Verify auto-renew:

```bash
sudo systemctl status certbot.timer --no-pager
```

## 9) Day-2 operations

```bash
# Pull latest code
cd /opt/plagiarism-checker
git pull

# Update backend dependencies (if requirements changed)
cd /opt/plagiarism-checker/backend
source .venv/bin/activate
pip install -r requirements.txt
deactivate

# Restart backend after updates
sudo systemctl restart plagiarism-backend

# Logs
sudo journalctl -u plagiarism-backend -f
sudo tail -f /var/log/nginx/error.log
```

## 10) Low-memory guardrails

- Keep `MAX_CANDIDATE_PAPERS` at `2` or `3`.
- Keep a single backend worker (service file already does this).
- Run one analysis at a time.
- If you hit OOM:
  - reduce candidate limit,
  - restart backend: `sudo systemctl restart plagiarism-backend`

## 11) Optional: old Docker-based deployment

Legacy Docker files are still available in `deploy/oracle/` if you ever move to a larger VM, but they are not recommended for your current 1 GB instance.
