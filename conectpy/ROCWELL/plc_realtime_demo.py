from pycomm3 import LogixDriver
from datetime import datetime
import threading
import time
import math
import logging
import sqlite3
from flask import Flask, jsonify, render_template_string, request

# ==============================
# CONFIG (IP + NOMBRE + TAGS + ESTADOS)
# ==============================

PLCS = {
    "192.168.11.10": {
        "name": "Costa del Lago - Paraguay",
        "tags": [
            "PT117_R_SCADA", "PT148_R_SCADA", "PT141_R_SCADA", "PT143_R_SCADA", "PT145_R_SCADA",
            "P002_ST_SCADA",  "P006_ST_SCADA", "P007_ST_SCADA"],
        "state_tags": ["P002_ST_SCADA","P006_ST_SCADA", "P007_ST_SCADA", "RETRO_SCADA"],#  (eventos TRUE/FALSE)
    },
    "192.168.16.10": {
        "name": "AVA LAGOONS - Mexico",
        "tags": ["FIT003_R_SCADA", "PT117_R_SCADA", "PT148_R_SCADA", "PT141_R_SCADA", "PT145_R_SCADA","P002_ST_SCADA", "P006_ST_SCADA", "P007_ST_SCADA"],
        "state_tags": ["P002_ST_SCADA", "P006_ST_SCADA", "P007_ST_SCADA","RETRO_SCADA"],
    },
    "192.168.18.10": {
        "name": "ARY - Pakistan",
        "tags": ["WM01_TOT", "PT117_R", "PT119_R", "P005_ST","P002_ST_SCADA", "P006_ST_SCADA", "P007_ST_SCADA"],
        "state_tags": ["P002_ST_SCADA", "P006_ST_SCADA", "P007_ST_SCADA","RETRO_SCADA"], 
    },
}


TAG_LABELS = {
   
    "P002_ST_SCADA": "Bomba de Retrolavado Funcionando",
    "RETRO_SCADA": "Filtros en Retrolavado",
    "P006_ST_SCADA": "Bomba Filtración Funcionando",
    "P007_ST_SCADA": "Bomba Retorno Funcionando",
 
}

READ_INTERVAL = 1.0
RECONNECT_DELAY = 5

MAX_CONSECUTIVE_FAILS = 10
FORCE_RECONNECT_EVERY_SEC = 3600  

# ==============================
# DB (SQLite) - SOLO EVENTOS
# ==============================

DB_PATH = "events.sqlite3"

def db_connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def db_init():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plc_ip TEXT NOT NULL,
            plc_name TEXT NOT NULL,
            tag TEXT NOT NULL,
            tag_label TEXT NOT NULL,
            start_ts TEXT NOT NULL,
            end_ts TEXT,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_plc_tag ON events(plc_ip, tag)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_start_ts ON events(start_ts)")
    conn.commit()
    conn.close()

def db_get_open_events():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT id, plc_ip, tag FROM events WHERE end_ts IS NULL")
    rows = cur.fetchall()
    conn.close()
    # {(plc_ip, tag): event_id}
    return {(r[1], r[2]): r[0] for r in rows}

def db_insert_event(plc_ip, plc_name, tag, tag_label, start_ts):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO events(plc_ip, plc_name, tag, tag_label, start_ts, end_ts, created_at)
        VALUES(?,?,?,?,?,?,?)
    """, (plc_ip, plc_name, tag, tag_label, start_ts, None, now_ts()))
    conn.commit()
    event_id = cur.lastrowid
    conn.close()
    return event_id

def db_close_event(event_id, end_ts):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("UPDATE events SET end_ts=? WHERE id=?", (end_ts, event_id))
    conn.commit()
    conn.close()

def db_list_events(plc_ip=None, limit=200):
    conn = db_connect()
    cur = conn.cursor()

    if plc_ip:
        cur.execute("""
            SELECT plc_ip, plc_name, tag, tag_label, start_ts, end_ts
            FROM events
            WHERE plc_ip=?
            ORDER BY id DESC
            LIMIT ?
        """, (plc_ip, limit))
    else:
        cur.execute("""
            SELECT plc_ip, plc_name, tag, tag_label, start_ts, end_ts
            FROM events
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

    rows = cur.fetchall()
    conn.close()
    return [
        {
            "plc_ip": r[0],
            "plc_name": r[1],
            "tag": r[2],
            "tag_label": r[3],
            "start_ts": r[4],
            "end_ts": r[5],
        }
        for r in rows
    ]

# ==============================
# ESTADO GLOBAL
# ==============================

lock = threading.Lock()
realtime_data = {}

open_event_ids = {}  # {(ip, tag): event_id}   (se rellena desde DB)
last_state = {}      # {(ip, tag): bool}

# ==============================
# UTILS
# ==============================

def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def trunc_4(value):
    """4 decimales TRUNCADOS (sin redondear). Devuelve string."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        factor = 10**4
        truncated = math.trunc(value * factor) / factor
        return f"{truncated:.4f}"
    return str(value)

def trunc_ms_4(ms):
    if ms is None:
        return None
    factor = 10**4
    truncated = math.trunc(ms * factor) / factor
    return f"{truncated:.4f}"

def to_bool(v):
    """Normaliza valores a bool para tags de estado."""
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    # En caso de que devuelvan 0/1
    if isinstance(v, (int, float)):
        if v == 0:
            return False
        if v == 1:
            return True
    # strings tipo "True"/"False"
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("true", "1", "on"):
            return True
        if s in ("false", "0", "off"):
            return False
    return None

def tag_label(tag: str) -> str:
    return TAG_LABELS.get(tag, tag)

# ==============================
# FLASK
# ==============================

app = Flask(__name__)
logging.getLogger("werkzeug").setLevel(logging.ERROR)

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>PLC Realtime Monitor</title>
  <style>
    body { font-family: Arial; background: #0f172a; color: #e5e7eb; }
    .plc { margin-bottom: 16px; padding: 12px; border: 1px solid #334155; border-radius: 10px; }
    .header { display: flex; align-items: baseline; gap: 10px; justify-content: space-between; }
    .left { display:flex; gap:10px; align-items:baseline; }
    .ip { font-weight: 700; font-size: 16px; }
    .name { color: #cbd5e1; font-size: 14px; }
    .meta { color: #94a3b8; font-size: 12px; margin-top: 6px; }
    .tag { margin-left: 10px; padding: 4px 0; }
    small { color: #94a3b8; margin-left: 8px; }
    .row { display: inline-block; min-width: 240px; }
    .ok { color: #86efac; }
    .bad { color: #fca5a5; }
    .down { color: #fcd34d; }
    .pill { padding: 2px 8px; border-radius: 999px; font-size: 12px; border: 1px solid #334155; color:#cbd5e1; text-decoration:none; }
    .stateOn { color:#86efac; font-weight:700; }
    .stateOff { color:#fca5a5; font-weight:700; }
  </style>
</head>
<body>
  <h1>PLC Realtime Data</h1>
  <div id="content"></div>

  <script>
    async function loadData() {
      const res = await fetch('/data');
      const data = await res.json();

      let html = '';
      for (const plc in data) {
        const plcBlock = data[plc] || {};
        const name = plcBlock._name || '';
        const meta = plcBlock._meta || {};
        const quality = meta.quality || "UNKNOWN";
        const qClass = (quality === "OK") ? "ok" : (quality === "DOWN" ? "down" : "bad");

        html += `<div class="plc">`;
        html += `
          <div class="header">
            <div class="left">
              <div class="ip">PLC ${plc}</div>
              <div class="name">${name}</div>
            </div>
            <a class="pill" href="/events?plc=${encodeURIComponent(plc)}" target="_blank">+ eventos</a>
          </div>
          <div class="meta ${qClass}">
            Estado: ${quality}
            | última ronda: ${meta.last_cycle_ms || "-"} ms
            | last_ok: ${meta.last_ok_ts || "-"}
            | fails: ${meta.consecutive_fails ?? "-"}
            | ${meta.last_cycle_ts || "-"}
            ${meta.last_error ? (" | error: " + meta.last_error) : ""}
          </div>
        `;

        for (const tag in plcBlock) {
          if (tag.startsWith("_")) continue;
          const d = plcBlock[tag];
          if (!d || typeof d !== "object") continue;

          const tq = d.quality || "UNKNOWN";
          const tClass = (tq === "OK") ? "ok" : (tq === "DOWN" ? "down" : "bad");
          const label = d.label || tag;

          // estados bonitos
          let valueHtml = `<b class="${tClass}">${d.valor}</b>`;
          if (d.is_state === true) {
            valueHtml = (String(d.valor).toUpperCase() === "TRUE")
              ? `<span class="stateOn">TRUE</span>`
              : `<span class="stateOff">FALSE</span>`;
          }

          html += `
            <div class="tag">
              <span class="row">${label}:</span>
              ${valueHtml}
              <small class="${tClass}">(${d.latencia_ms} ms) ${d.timestamp} | ${tq}</small>
            </div>
          `;
        }

        html += `</div>`;
      }

      document.getElementById('content').innerHTML = html;
    }

    setInterval(loadData, 1000); 
    loadData();
  </script>
</body>
</html>
"""
EVENTS_PAGE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Eventos</title>
  <style>
    body { font-family: Arial; background: #0f172a; color: #e5e7eb; padding: 16px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border-bottom: 1px solid #334155; padding: 8px; text-align: left; }
    th { color: #cbd5e1; }
    .muted { color: #94a3b8; }
  </style>
</head>
<body>
  <h2>Eventos (TRUE -> FALSE)</h2>
  <div class="muted">PLC: {{plc}}</div>
  <br/>
  <table>
    <thead>
      <tr>
        <th>Laguna</th>
        <th>Variable</th>
        <th>Fecha</th>
        <th>Hora Inicio</th>
        <th>Hora Fin</th>
      </tr>
    </thead>
    <tbody>
      {{ rows|safe }}
    </tbody>
  </table>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/data")
def get_data():
    with lock:
        return jsonify(realtime_data)

@app.route("/api/events")
def api_events():
    plc = request.args.get("plc")
    limit = int(request.args.get("limit", "200"))
    return jsonify(db_list_events(plc_ip=plc, limit=limit))

@app.route("/events")
def events_html():
    plc = request.args.get("plc")
    limit = int(request.args.get("limit", "200"))
    events = db_list_events(plc_ip=plc, limit=limit)

    def split_date_time(ts):
        if not ts:
            return ("-", "-")
        # ts format: YYYY-MM-DD HH:MM:SS
        parts = ts.split(" ")
        if len(parts) == 2:
            return parts[0], parts[1]
        return (ts, "-")

    rows_html = ""
    for ev in events:
        d, t_start = split_date_time(ev["start_ts"])
        _, t_end = split_date_time(ev["end_ts"]) if ev["end_ts"] else ("-", "-")
        rows_html += (
            "<tr>"
            f"<td>{ev['plc_name']}</td>"
            f"<td>{ev['tag_label']}</td>"
            f"<td>{d}</td>"
            f"<td>{t_start}</td>"
            f"<td>{t_end}</td>"
            "</tr>"
        )

    return render_template_string(EVENTS_PAGE, plc=plc or "ALL", rows=rows_html)

def run_web():
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

# ==============================
# LECTURA PLC + DETECCION EVENTOS
# ==============================

def read_plc_loop(ip, plc_name, tags, state_tags):
    with lock:
        realtime_data.setdefault(ip, {})
        realtime_data[ip]["_name"] = plc_name
        realtime_data[ip]["_meta"] = {
            "quality": "INIT",
            "last_cycle_ms": None,
            "last_cycle_ts": now_ts(),
            "last_ok_ts": None,
            "last_error": None,
            "consecutive_fails": 0,
        }

    print(f"[START] {ip} ({plc_name})")

    consecutive_fails = 0
    session_start = 0.0

    while True:
        try:
            session_start = time.time()
            with LogixDriver(ip) as plc:
                consecutive_fails = 0

                while True:
                    if (time.time() - session_start) >= FORCE_RECONNECT_EVERY_SEC:
                        raise Exception("FORCE_RECONNECT: session rotation")

                    cycle_start = time.perf_counter()
                    cycle_ts = now_ts()

                    cycle_ok = True
                    last_error = None
                    last_ok_ts = None

                    for tag in tags:
                        t0 = time.perf_counter()
                        try:
                            result = plc.read(tag)
                            t1 = time.perf_counter()

                            lat_ms = (t1 - t0) * 1000.0
                            raw_value = result.value if hasattr(result, "value") else result
                            ts = now_ts()

                            is_state = tag in state_tags
                            label = tag_label(tag)

                            # --- eventos TRUE/FALSE ---
                            if is_state:
                                b = to_bool(raw_value)
                                # si no se puede interpretar, lo tratamos como lectura normal
                                if b is not None:
                                    prev = last_state.get((ip, tag))

                                    # transición False/None -> True => abrir evento
                                    if (prev is False or prev is None) and b is True:
                                        # evita duplicado si ya hay abierto
                                        if (ip, tag) not in open_event_ids:
                                            eid = db_insert_event(ip, plc_name, tag, label, ts)
                                            open_event_ids[(ip, tag)] = eid

                                    # transición True -> False => cerrar evento
                                    if prev is True and b is False:
                                        eid = open_event_ids.get((ip, tag))
                                        if eid:
                                            db_close_event(eid, ts)
                                            open_event_ids.pop((ip, tag), None)

                                    last_state[(ip, tag)] = b

                            with lock:
                                realtime_data.setdefault(ip, {})
                                realtime_data[ip]["_name"] = plc_name
                                realtime_data[ip][tag] = {
                                    "label": label,
                                    "valor": ("TRUE" if to_bool(raw_value) is True else ("FALSE" if to_bool(raw_value) is False else trunc_4(raw_value)))
                                            if (tag in state_tags) else trunc_4(raw_value),
                                    "latencia_ms": trunc_ms_4(lat_ms),
                                    "timestamp": ts,
                                    "quality": "OK",
                                    "error": None,
                                    "is_state": is_state,
                                }

                            last_ok_ts = ts

                        except Exception as e:
                            cycle_ok = False
                            last_error = str(e)

                            with lock:
                                realtime_data.setdefault(ip, {})
                                realtime_data[ip]["_name"] = plc_name
                                prev = realtime_data[ip].get(tag)
                                if prev and isinstance(prev, dict):
                                    realtime_data[ip][tag] = {
                                        **prev,
                                        "quality": "BAD",
                                        "error": last_error,
                                        "timestamp": now_ts(),
                                    }
                                else:
                                    realtime_data[ip][tag] = {
                                        "label": tag_label(tag),
                                        "valor": None,
                                        "latencia_ms": None,
                                        "timestamp": now_ts(),
                                        "quality": "BAD",
                                        "error": last_error,
                                        "is_state": (tag in state_tags),
                                    }

                    cycle_elapsed_ms = (time.perf_counter() - cycle_start) * 1000.0

                    if cycle_ok:
                        consecutive_fails = 0
                        meta_quality = "OK"
                    else:
                        consecutive_fails += 1
                        meta_quality = "BAD"

                    with lock:
                        realtime_data.setdefault(ip, {})
                        prev_meta = realtime_data[ip].get("_meta", {})
                        realtime_data[ip]["_meta"] = {
                            "quality": meta_quality,
                            "last_cycle_ms": trunc_ms_4(cycle_elapsed_ms),
                            "last_cycle_ts": cycle_ts,
                            "last_ok_ts": last_ok_ts or prev_meta.get("last_ok_ts"),
                            "last_error": last_error,
                            "consecutive_fails": consecutive_fails,
                        }

                    if consecutive_fails >= MAX_CONSECUTIVE_FAILS:
                        raise Exception(f"Too many consecutive fails ({consecutive_fails}) — reconnect")

                    elapsed = time.perf_counter() - cycle_start
                    sleep_for = READ_INTERVAL - elapsed
                    if sleep_for > 0:
                        time.sleep(sleep_for)

        except Exception as e:
            msg = str(e)
            print(f"[RECONNECT] {ip} ({plc_name}) -> {msg} | sleep {RECONNECT_DELAY}s")

            with lock:
                realtime_data.setdefault(ip, {})
                meta = realtime_data[ip].get("_meta", {})
                realtime_data[ip]["_meta"] = {
                    **meta,
                    "quality": "DOWN",
                    "last_cycle_ts": now_ts(),
                    "last_error": msg,
                }

            time.sleep(RECONNECT_DELAY)

# ==============================
# MAIN
# ==============================

if __name__ == "__main__":
    db_init()
    # recuperar eventos abiertos por si reiniciaste el script
    open_event_ids = db_get_open_events()

    t_web = threading.Thread(target=run_web, daemon=True)
    t_web.start()

    threads = []
    for ip, cfg in PLCS.items():
        t = threading.Thread(
            target=read_plc_loop,
            args=(ip, cfg["name"], cfg["tags"], cfg.get("state_tags", [])),
            daemon=True
        )
        t.start()
        threads.append(t)

    for t in threads:
        t.join()
