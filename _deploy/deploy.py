"""End-to-end deploy на 10.10.10.65.

Шаги:
1) Залить свежий код через SFTP (rsync-style — только изменения, без .env/.git/__pycache__).
2) Подготовить prod-конфиги: nginx.prod.conf, docker-compose.override.yml.
3) Сгенерировать self-signed cert (если ещё нет).
4) Очистить GIGACHAT_CA_BUNDLE_FILE и расширить CORS_ORIGINS в .env на VM.
5) docker compose up -d --build.
6) Проверить https://10.10.10.65/health.
"""
import os
import sys
import time
import stat
from pathlib import Path
import paramiko

HOST = "10.10.10.65"
USER = "root"
PWD = sys.argv[1] if len(sys.argv) > 1 else None
if not PWD:
    print("Usage: deploy.py <password>"); sys.exit(1)

LOCAL_ROOT = Path(__file__).resolve().parent.parent
REMOTE_ROOT = "/root/freetato/freetato-academy"

# Что синхронизировать — целиком (с правильными игнорами).
SYNC_DIRS = ["backend", "frontend", "nginx", "_deploy"]
SYNC_FILES = ["docker-compose.yml", "README.md", ".gitignore"]
EXCLUDE_NAMES = {".git", "__pycache__", ".pytest_cache", ".env", ".env.bak", "node_modules", "_smoke.ps1", "_ai_test.ps1", "_lesson_test.ps1", "_mod_del.ps1"}
EXCLUDE_SUFFIX = {".pyc", ".pyo", ".bak"}

def should_skip(name: str) -> bool:
    if name in EXCLUDE_NAMES:
        return True
    if name.startswith(".env.bak"):
        return True
    if any(name.endswith(s) for s in EXCLUDE_SUFFIX):
        return True
    return False

def sftp_mkdirs(sftp, remote_path):
    parts = remote_path.strip("/").split("/")
    path = ""
    for p in parts:
        path += "/" + p
        try:
            sftp.stat(path)
        except FileNotFoundError:
            sftp.mkdir(path)

def upload_tree(sftp, local_dir: Path, remote_dir: str, uploaded: list):
    for entry in local_dir.iterdir():
        if should_skip(entry.name):
            continue
        rpath = f"{remote_dir}/{entry.name}"
        if entry.is_dir():
            try:
                sftp.stat(rpath)
            except FileNotFoundError:
                sftp.mkdir(rpath)
            upload_tree(sftp, entry, rpath, uploaded)
        else:
            local_mtime = entry.stat().st_mtime
            need = True
            try:
                rstat = sftp.stat(rpath)
                # Сравниваем размер + mtime округлённо
                if rstat.st_size == entry.stat().st_size and abs(rstat.st_mtime - local_mtime) < 2:
                    need = False
            except FileNotFoundError:
                pass
            if need:
                sftp.put(str(entry), rpath)
                sftp.utime(rpath, (local_mtime, local_mtime))
                uploaded.append(rpath)

def run(cli, cmd, label="", timeout=120, check=True):
    print(f"\n>> {label or cmd[:80]}")
    _, out, err = cli.exec_command(cmd, timeout=timeout)
    o = out.read().decode(errors="replace")
    e = err.read().decode(errors="replace")
    rc = out.channel.recv_exit_status()
    if o.strip(): print(o.rstrip())
    if e.strip(): print(f"  (stderr) {e.rstrip()}")
    if check and rc != 0:
        raise RuntimeError(f"command failed (rc={rc}): {cmd}")
    return o, e, rc

print(f"[1/6] connect {USER}@{HOST}")
cli = paramiko.SSHClient(); cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(HOST, username=USER, password=PWD, timeout=15, look_for_keys=False, allow_agent=False)
sftp = cli.open_sftp()

print(f"[2/6] sync code to {REMOTE_ROOT}")
sftp_mkdirs(sftp, REMOTE_ROOT)
uploaded = []
for d in SYNC_DIRS:
    local = LOCAL_ROOT / d
    if not local.exists(): continue
    sftp_mkdirs(sftp, f"{REMOTE_ROOT}/{d}")
    upload_tree(sftp, local, f"{REMOTE_ROOT}/{d}", uploaded)
for f in SYNC_FILES:
    local = LOCAL_ROOT / f
    if not local.exists(): continue
    rpath = f"{REMOTE_ROOT}/{f}"
    need = True
    try:
        if sftp.stat(rpath).st_size == local.stat().st_size:
            need = False
    except FileNotFoundError:
        pass
    if need:
        sftp.put(str(local), rpath)
        uploaded.append(rpath)
print(f"  uploaded {len(uploaded)} files")

print("[3/6] ensure certs dir + self-signed cert (if missing)")
run(cli, f"mkdir -p {REMOTE_ROOT}/nginx/certs", "mkdir certs")
o, _, _ = run(cli, f"test -f {REMOTE_ROOT}/nginx/certs/freetato.crt && echo exists || echo gen", "check cert", check=False)
if "gen" in o:
    gen_cmd = (
        f"cd {REMOTE_ROOT}/nginx/certs && "
        "openssl req -x509 -nodes -newkey rsa:2048 "
        "-keyout freetato.key -out freetato.crt -days 825 "
        "-subj '/C=RU/O=FREETATO/CN=10.10.10.65' "
        "-addext 'subjectAltName=IP:10.10.10.65,DNS:localhost' "
        "&& chmod 600 freetato.key && chmod 644 freetato.crt"
    )
    run(cli, gen_cmd, "openssl gen self-signed")
else:
    print("  cert exists, skipping")

print("[4/6] patch .env: clear GIGACHAT_CA_BUNDLE_FILE + add https origin to CORS")
patch_cmd = (
    f"cd {REMOTE_ROOT} && "
    "cp .env .env.bak.$(date +%s) && "
    "sed -i 's|^GIGACHAT_CA_BUNDLE_FILE=.*|GIGACHAT_CA_BUNDLE_FILE=|' .env && "
    "grep -q 'https://10.10.10.65' .env || "
    "sed -i 's|^CORS_ORIGINS=\\(.*\\)|CORS_ORIGINS=\\1,https://10.10.10.65,http://10.10.10.65|' .env"
)
run(cli, patch_cmd, "patch .env")

print("[5/6] docker compose down + build + up (with prod overlay)")
COMPOSE = "docker compose -f docker-compose.yml -f _deploy/docker-compose.prod.yml"
run(cli, f"cd {REMOTE_ROOT} && {COMPOSE} down", "compose down", timeout=60, check=False)
# Также сносим возможный старый override без флагов на случай, если он был
run(cli, f"cd {REMOTE_ROOT} && docker compose down 2>/dev/null || true", "down (legacy)", timeout=60, check=False)
run(cli, f"cd {REMOTE_ROOT} && {COMPOSE} build app", "compose build app", timeout=600)
run(cli, f"cd {REMOTE_ROOT} && {COMPOSE} up -d", "compose up -d", timeout=120)

print("[6/6] health check")
time.sleep(8)
run(cli, "curl -ks -o /dev/null -w 'HTTP %{http_code}\\n' https://10.10.10.65/health", "GET https://10.10.10.65/health", check=False)
run(cli, "curl -ks -o /dev/null -w 'HTTP %{http_code}\\n' https://10.10.10.65/pages/login.html", "GET https://10.10.10.65/pages/login.html", check=False)
run(cli, "curl -s -o /dev/null -w 'HTTP %{http_code}\\n' http://10.10.10.65/health", "GET http://10.10.10.65/health (should redirect)", check=False)
run(cli, f"cd {REMOTE_ROOT} && {COMPOSE} ps", "container status", check=False)

sftp.close(); cli.close()
print("\n=== DONE ===")
print("Откройте в браузере: https://10.10.10.65")
print("Браузер покажет предупреждение про self-signed cert — добавьте в исключения один раз.")
