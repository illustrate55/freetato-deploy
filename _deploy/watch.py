"""Watch-режим: следит за frontend/ и сразу заливает изменения на 10.10.10.65.

Использование (запустить и оставить открытым):
    python _deploy/watch.py <пароль_root>

Что делает:
- Раз в 1.5 сек обходит frontend/, сравнивает mtime/size.
- Любой изменившийся файл закидывает по SFTP в /root/freetato/freetato-academy/frontend/.
- Nginx раздаёт frontend через bind-mount, поэтому пересборка контейнера не нужна.
- В браузере достаточно жёсткой перезагрузки (Ctrl+F5) или инкогнито.

Для бэкенда (backend/*.py) этот скрипт НЕ подходит — там нужна
пересборка контейнера: запускай python _deploy/deploy.py <пароль>.
"""
import sys
import time
from pathlib import Path
import paramiko

HOST = "10.10.10.65"
USER = "root"
PWD = sys.argv[1] if len(sys.argv) > 1 else None
if not PWD:
    print("Usage: watch.py <password>"); sys.exit(1)

LOCAL_ROOT = Path(__file__).resolve().parent.parent
LOCAL_FRONTEND = LOCAL_ROOT / "frontend"
REMOTE_FRONTEND = "/root/freetato/freetato-academy/frontend"
POLL_INTERVAL = 1.5

EXCLUDE_NAMES = {".git", "__pycache__", "node_modules"}
EXCLUDE_SUFFIX = {".pyc", ".bak", ".swp", ".tmp"}

def should_skip(name: str) -> bool:
    if name in EXCLUDE_NAMES:
        return True
    if any(name.endswith(s) for s in EXCLUDE_SUFFIX):
        return True
    if name.startswith("."):
        return True
    return False

def ensure_remote_dir(sftp, rpath: str, known: set):
    if rpath in known:
        return
    parts = rpath.strip("/").split("/")
    path = ""
    for p in parts:
        path += "/" + p
        if path in known:
            continue
        try:
            sftp.stat(path)
        except FileNotFoundError:
            sftp.mkdir(path)
        known.add(path)

def scan(local_root: Path):
    snapshot = {}
    for p in local_root.rglob("*"):
        if any(should_skip(part) for part in p.relative_to(local_root).parts):
            continue
        if p.is_file():
            st = p.stat()
            snapshot[p] = (st.st_size, int(st.st_mtime))
    return snapshot

def main():
    print(f"[watch] connect {USER}@{HOST}")
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(HOST, username=USER, password=PWD, timeout=15,
                look_for_keys=False, allow_agent=False)
    sftp = cli.open_sftp()
    known_dirs = set()
    ensure_remote_dir(sftp, REMOTE_FRONTEND, known_dirs)

    print(f"[watch] following {LOCAL_FRONTEND} -> {HOST}:{REMOTE_FRONTEND}")
    print("[watch] Ctrl+C для выхода\n")

    prev = scan(LOCAL_FRONTEND)
    print(f"[watch] baseline: {len(prev)} files tracked")

    try:
        while True:
            time.sleep(POLL_INTERVAL)
            curr = scan(LOCAL_FRONTEND)
            changed = []
            for p, sig in curr.items():
                if prev.get(p) != sig:
                    changed.append(p)
            for p in changed:
                rel = p.relative_to(LOCAL_FRONTEND).as_posix()
                rpath = f"{REMOTE_FRONTEND}/{rel}"
                rdir = rpath.rsplit("/", 1)[0]
                ensure_remote_dir(sftp, rdir, known_dirs)
                try:
                    sftp.put(str(p), rpath)
                    sftp.utime(rpath, (p.stat().st_mtime, p.stat().st_mtime))
                    ts = time.strftime("%H:%M:%S")
                    print(f"[{ts}] uploaded {rel} ({curr[p][0]} bytes)")
                except Exception as e:
                    print(f"  ERR {rel}: {e}")
            prev = curr
    except KeyboardInterrupt:
        print("\n[watch] stopped")
    finally:
        sftp.close(); cli.close()

if __name__ == "__main__":
    main()
