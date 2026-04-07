# Collector Python - Crystal Lagoons

Collector SCADA en Python para leer tags de PLCs (Rockwell y Siemens) y enviarlos por HTTP.

## Estado actual

- Lee tags en ciclo continuo (`poll_seconds`).
- Soporta `source: rockwell` y `source: siemens`.
- Soporta modo single o multi PLC por `collectors.yml` + `include`.
- Normaliza `WM01_TOT_SCADA` -> `WM01_TOT_DELTA_SCADA`.
- Usa envio HTTP asincrono por laguna con cola en memoria (lectura desacoplada del POST).
- Reutiliza conexiones HTTP con `requests.Session` + pool.
- Si el backend falla o la cola se llena, puede persistir payloads en `data/buffer.jsonl`.
- Lectura Siemens en batch (`client.get_values`) en un solo roundtrip por ciclo.
- Mapeo Rockwell optimizado (`plc_tag -> logical_tag`) para reducir CPU con muchos tags.

## Requisitos

- Python 3.10+.
- Red con acceso a PLCs y backend.
- Variable de entorno `COLLECTOR_API_KEY`.

## Instalacion

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Configuracion

### Variables de entorno

`.env`:

```env
COLLECTOR_API_KEY=tu-api-key
```

### Ejemplo single PLC

```yaml
lagoon_id: "aquavista"
source: "siemens"
poll_seconds: 1
timezone: "America/Mexico_City"

backend:
  url: "http://localhost:8000/ingest/scada"
  timeout_sec: 3
  pool_connections: 50
  pool_maxsize: 200
  send_events: false

runtime:
  send_queue_maxsize: 1000
  send_queue_full_policy: "drop_newest"   # drop_newest | drop_oldest | block
  spool_on_send_fail: true
  startup_jitter_max_sec: 0.25
  log_every_n_cycles: 10
  log_every_n_sends: 100
  enable_state_events: true

siemens:
  opc_server_url: "opc.tcp://192.168.17.10:4840"
  timeout_sec: 1

tags:
  Tags_01_Real: "ns=4;i=3"
```

### Ejemplo master

```yaml
backend:
  url: "http://localhost:8000/ingest/scada"

runtime:
  send_queue_maxsize: 1000
  send_queue_full_policy: "drop_newest"
  spool_on_send_fail: true
  log_every_n_cycles: 10

plcs:
  - include: "config/lagoon_aquavista.yml"
  - include: "config/lagoon_costadellago.yml"
  - include: "config/Ava_lagoons.yml"
```

## Campos importantes

- `lagoon_id` (requerido): identificador de laguna.
- `source` (requerido): `rockwell` o `siemens`.
- `timezone` (requerido): zona IANA valida.
- `tags` (requerido): mapa `tag_logica -> tag_plc`.
- `poll_seconds` (default `1`).
- `backend.url` (practicamente requerido para envio).
- `backend.timeout_sec`, `backend.pool_connections`, `backend.pool_maxsize`.
- `runtime.send_queue_maxsize`, `runtime.send_queue_full_policy`.
- `runtime.spool_on_send_fail` para escribir JSONL local.
- `runtime.startup_jitter_max_sec` para evitar picos sincronizados.
- `runtime.log_every_n_cycles` y `runtime.log_every_n_sends`.
- `runtime.enable_state_events` para detector de estados enteros.
- `event_tags` (opcional) para eventos booleanos `OPEN/CLOSE`.

## Ejecucion

```powershell
python main.py --config collectors.yml
```

o:

```powershell
python main.py --config config\Ava_lagoons.yml
```

Tambien puedes usar:

```powershell
run_collector.bat
```

## Payload HTTP

Body base:

```json
{
  "lagoon_id": "ava_lagoons",
  "source": "rockwell",
  "timestamp": "2026-02-25T18:32:00.000000+00:00",
  "tags": {
    "PT117_R_SCADA": 12.34
  }
}
```

Si `backend.send_events: true` y existen eventos, se agrega `events`.

## Observabilidad

Logs principales:

- `START source=<source> lagoon=<id> poll=<sec> queue=<n> policy=<policy>`
- `OK source=<source> lagoon=<id> utc=<ts> local=<ts> tags=<n> events=<n> cycle=<ms> queue=<n> dropped=<n>`
- `EMPTY source=<source> lagoon=<id>`
- `SEND lagoon=<id> sent=<n> failed=<n> queue=<n>`
- `ERR source=<source> lagoon=<id> err=<msg>`

## Limitaciones actuales

- `storage/pg_writer.py` sigue sin implementacion.
- No existe replay automatico del `buffer.jsonl` hacia backend (solo spool local).

## Arquitectura

Detalle en [ARQUITECTURA.md](ARQUITECTURA.md).
