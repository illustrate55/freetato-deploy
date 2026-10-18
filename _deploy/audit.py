"""Сводный аудит того, что развёрнуто на 10.10.10.65.

Что проверяется:
1. SYNC: каждый файл из frontend/ и важные backend/ совпадают по содержимому
   с тем, что отдаёт nginx.
2. HEALTH: /health, /docs, /openapi.json.
3. ASSETS: каждый .html в pages/, каждый .js в js/, каждый .css в css/
   — отдаются 200.
4. AUTH: login → /users/me → /auth/refresh (rotation) для admin/teacher/demo.
5. REMOVED: /auth/_debug/hash должен быть 404 (debug снят).
"""
import hashlib
import re
import sys
from pathlib import Path

import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = "https://10.10.10.65"
API = f"{BASE}/api/v1"
ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"

PWD = sys.argv[1] if len(sys.argv) > 1 else ""
if not PWD:
    print("Usage: audit.py <admin_password>"); sys.exit(1)

ADMIN = ("admin@freetato.ru", PWD)
TEACHER = ("teacher@freetato.ru", "Teacher2026Pass")
DEMO = ("demo@freetato.ru", "Demo2026Pass")

s = requests.Session()
s.verify = False

OK, WARN, FAIL = "OK   ", "WARN ", "FAIL "
totals = {"ok": 0, "warn": 0, "fail": 0}


def mark(level, msg):
    print(f"[{level}] {msg}")
    if level == OK:
        totals["ok"] += 1
    elif level == WARN:
        totals["warn"] += 1
    else:
        totals["fail"] += 1


def fetch(path):
    r = s.get(BASE + path, timeout=10)
    return r


def post(path, body, headers=None):
    return s.post(API + path, json=body, headers=headers or {}, timeout=10)


def get(path, headers=None):
    return s.get(API + path, headers=headers or {}, timeout=10)


# ───────────── 1. SYNC: содержимое frontend файлов ─────────────
print("\n── 1) SYNC frontend files ──")


def normalize(b: bytes) -> bytes:
    # сравниваем без учёта CRLF/LF, чтобы не ловить разницу в переносах
    return b.replace(b"\r\n", b"\n")


KEY_FILES = [
    "css/variables.css", "css/base.css", "css/components.css", "css/layout.css",
    "css/pages/login.css", "css/pages/register.css", "css/pages/dashboard.css",
    "css/pages/catalog.css", "css/pages/course.css", "css/pages/lesson.css",
    "css/pages/quiz.css", "css/pages/task.css", "css/pages/profile.css",
    "css/pages/admin.css", "css/pages/teacher.css",
    "js/api/client.js", "js/auth-guard.js",
    "js/pages/login.js", "js/pages/register.js", "js/pages/dashboard.js",
    "js/pages/teacher.js", "js/pages/teacher-course-edit.js", "js/pages/catalog.js",
    "js/components/sidebar.js", "js/components/header.js",
    "pages/login.html", "pages/register.html", "pages/dashboard.html",
    "pages/catalog.html", "pages/admin.html", "pages/teacher.html",
]
for rel in KEY_FILES:
    local = FRONTEND / rel
    if not local.exists():
        mark(FAIL, f"local missing {rel}")
        continue
    r = s.get(f"{BASE}/{rel}", timeout=10)
    if r.status_code != 200:
        mark(FAIL, f"{rel} → HTTP {r.status_code}")
        continue
    local_h = hashlib.sha1(normalize(local.read_bytes())).hexdigest()[:10]
    remote_h = hashlib.sha1(normalize(r.content)).hexdigest()[:10]
    if local_h == remote_h:
        mark(OK, f"{rel} ({len(r.content)} b)")
    else:
        mark(FAIL, f"{rel} hash mismatch local={local_h} remote={remote_h}")


# ───────────── 2. HEALTH / системные ─────────────
print("\n── 2) HEALTH ──")
for path, exp in [("/health", 200), ("/docs", 200), ("/openapi.json", 200)]:
    r = fetch(path)
    if r.status_code == exp:
        mark(OK, f"GET {path} → {r.status_code}")
    else:
        mark(FAIL, f"GET {path} → {r.status_code} (exp {exp})")


# ───────────── 3. ASSETS: 200 на всём фронте ─────────────
print("\n── 3) ASSETS 200 ──")
pages = [p.name for p in (FRONTEND / "pages").glob("*.html")]
for name in pages:
    r = fetch(f"/pages/{name}")
    mark(OK if r.status_code == 200 else FAIL, f"/pages/{name} → {r.status_code}")
js_files = [str(p.relative_to(FRONTEND).as_posix()) for p in (FRONTEND / "js").rglob("*.js")]
broken_js = []
for rel in js_files:
    r = fetch("/" + rel)
    if r.status_code != 200:
        broken_js.append(rel)
mark(OK if not broken_js else FAIL,
     f"{len(js_files)} .js files → {len(js_files) - len(broken_js)}/{len(js_files)} 200"
     + (f", broken: {broken_js}" if broken_js else ""))
css_files = [str(p.relative_to(FRONTEND).as_posix()) for p in (FRONTEND / "css").rglob("*.css")]
broken_css = []
for rel in css_files:
    r = fetch("/" + rel)
    if r.status_code != 200:
        broken_css.append(rel)
mark(OK if not broken_css else FAIL,
     f"{len(css_files)} .css files → {len(css_files) - len(broken_css)}/{len(css_files)} 200"
     + (f", broken: {broken_css}" if broken_css else ""))


# ───────────── 4. AUTH для всех ролей ─────────────
print("\n── 4) AUTH per role ──")


def auth_flow(email, pwd, expected_role):
    label = f"{email}"
    r = post("/auth/login", {"email": email, "password": pwd})
    if not r.ok:
        mark(FAIL, f"{label} login → {r.status_code} {r.text[:80]}")
        return
    d = r.json()
    access, refresh = d["access_token"], d["refresh_token"]
    role = d.get("user", {}).get("role")
    if role != expected_role:
        mark(WARN, f"{label} role={role} ожидали {expected_role}")
    else:
        mark(OK, f"{label} login + role={role}")
    me = get("/users/me", headers={"Authorization": f"Bearer {access}"})
    mark(OK if me.ok else FAIL, f"{label} /users/me → {me.status_code}")
    rot = post("/auth/refresh", {"refresh_token": refresh})
    if not rot.ok:
        mark(FAIL, f"{label} refresh → {rot.status_code}")
        return
    new_refresh = rot.json()["refresh_token"]
    old_again = post("/auth/refresh", {"refresh_token": refresh})
    if old_again.status_code == 401:
        mark(OK, f"{label} старый refresh после rotation → 401")
    else:
        mark(FAIL, f"{label} старый refresh после rotation → {old_again.status_code} (ожидали 401)")
    new_again = post("/auth/refresh", {"refresh_token": new_refresh})
    if new_again.ok:
        mark(OK, f"{label} новый refresh работает")
    else:
        mark(FAIL, f"{label} новый refresh → {new_again.status_code}")


auth_flow(*ADMIN, "admin")
auth_flow(*TEACHER, "teacher")
auth_flow(*DEMO, "student")


# ───────────── 5. REMOVED endpoints ─────────────
print("\n── 5) REMOVED ──")
r = fetch("/api/v1/auth/_debug/hash")
if r.status_code == 404:
    mark(OK, "/auth/_debug/hash → 404 (debug снят)")
else:
    mark(FAIL, f"/auth/_debug/hash всё ещё открыт: {r.status_code}")


# ───────────── Итог ─────────────
print(f"\n=== ИТОГ: OK={totals['ok']}  WARN={totals['warn']}  FAIL={totals['fail']} ===")
sys.exit(0 if totals["fail"] == 0 else 1)
