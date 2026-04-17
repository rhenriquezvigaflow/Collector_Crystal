# Collector Python - Crystal Lagoons

Collector SCADA en Python para leer tags desde PLCs Rockwell o Siemens y publicar telemetria al backend por HTTP.

## Estado actual

- Soporta modo single PLC y modo multi-laguna usando un archivo master con `plcs[].include`.
- Mantiene una hebra lectora por PLC y, cuando hay backend configurado, una hebra sender por laguna.
- Desacopla lectura y envio con `Queue`, para que la latencia HTTP no bloquee el ciclo del PLC.
- Normaliza `WM01_TOT_SCADA` a `WM01_TOT_DELTA_SCADA`.
- Detecta eventos booleanos (`OPEN`/`CLOSE`) y cambios de estado enteros (`STATE_CHANGE`).
- Reutiliza conexiones HTTP con `requests.Session` y pool configurable.
- Si el backend falla, hace spool por laguna en `data/spool/<lagoon_id>.jsonl`.
- Reproduce automaticamente el spool cuando la cola en memoria queda vacia.
- Migra automaticamente el buffer legacy `data/buffer.jsonl` al formato por laguna al arrancar.

## Estructura importante

- `main.py`: orquestacion, carga YAML, readers, queue y sender threads.
- `workers/get_rockwell.py`: lectura batch de tags Rockwell.
- `workers/get_siemens.py`: lectura batch OPC-UA para Siemens.
- `common/sender.py`: cliente HTTP con `X-Api-Key` y pool de conexiones.
- `storage/jsonl_buffer.py`: spool, replay y migracion del buffer legacy.
- `normalizer/tot_delta_normalizer.py`: calcula delta del tag TOT.
- `supervisor.py`: wrapper para reiniciar `main.py` si el proceso cae.

## Requisitos

- Python 3.10+.
- Acceso de red a PLCs y backend.
- Variable de entorno `COLLECTOR_API_KEY`.

## Instalacion

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Configuracion

### Variables de entorno

`.env` minimo:

```env
COLLECTOR_API_KEY=tu-api-key
```

Variable opcional:

- `COLLECTOR_SEND_ERROR_LOG_INTERVAL_SEC`: rate limit de logs repetidos de fallo HTTP.

### Configuracion single PLC

```yaml
lagoon_id: "aquavista"
source: "siemens"
poll_seconds: 1
timezone: "America/Mexico_City"

backend:
  url: "http://127.0.0.1:8090/ingest/scada"
  timeout_sec: 3
  pool_connections: 2
  pool_maxsize: 4
  send_events: true

runtime:
  send_queue_maxsize: 100
  send_queue_full_policy: "drop_newest"
  spool_on_send_fail: true
  replay_spool_batch_size: 10
  max_replay_payload_age_sec: 900
  send_retry_attempts: 2
  send_retry_backoff_base_sec: 1.0
  send_retry_backoff_max_sec: 8.0
  startup_jitter_max_sec: 0.25
  log_every_n_cycles: 10
  log_every_n_sends: 100
  enable_state_events: true

siemens:
  opc_server_url: "opc.tcp://192.168.17.10:4840"
  timeout_sec: 1

tags:
  PT117_R_SCADA: "ns=4;i=3"

event_tags:
  VE001_ST: "Valvula VE001"
```

### Configuracion master

```yaml
backend:
  url: "http://127.0.0.1:8090/ingest/scada"
  pool_connections: 2
  pool_maxsize: 4

runtime:
  send_queue_maxsize: 100
  send_queue_full_policy: "drop_newest"
  spool_on_send_fail: true
  replay_spool_batch_size: 10
  max_replay_payload_age_sec: 900

plcs:
  - include: "config/lagoon_aquavista.yml"
  - include: "config/lagoon_costadellago.yml"
  - include: "config/Ava_lagoons.yml"
```

## Opciones de runtime importantes

- `send_queue_maxsize`: tamano de la cola por laguna.
- `send_queue_full_policy`: `drop_newest`, `drop_oldest` o `block`.
- `spool_on_send_fail`: persiste payloads fallidos a disco.
- `replay_spool_batch_size`: cuantos payloads del spool intenta reprocesar por tanda.
- `max_replay_payload_age_sec`: descarta backlog demasiado viejo durante el replay.
- `send_retry_attempts`: reintentos HTTP por payload antes de spooling.
- `send_retry_backoff_base_sec` y `send_retry_backoff_max_sec`: backoff exponencial.
- `startup_jitter_max_sec`: evita bursts sincronizados entre lagunas.
- `enable_state_events`: habilita eventos por cambios enteros `0..3`.

Opciones especificas Rockwell:

- `force_reconnect_every_sec`
- `max_consecutive_fails`
- `rockwell.ip`
- `rockwell.slot`
- `rockwell.timeout_sec`

Opciones especificas Siemens:

- `siemens.opc_server_url`
- `siemens.timeout_sec`
- `siemens.username`
- `siemens.password`

## Ejecucion

```powershell
python main.py --config collectors.yml
```

o

```powershell
python main.py --config config\Ava_lagoons.yml
```

Tambien puedes usar:

```powershell
run_collector.bat
```

## Payload enviado al backend

Base:

```json
{
  "lagoon_id": "ava_lagoons",
  "source": "rockwell",
  "timestamp": "2026-04-17T14:32:00+00:00",
  "tags": {
    "PT117_R_SCADA": 12.34,
    "WM01_TOT_DELTA_SCADA": 0.17
  }
}
```

Si `backend.send_events=true` y hubo eventos, se agrega:

```json
{
  "events": [
    {
      "type": "STATE_CHANGE",
      "lagoon_id": "ava_lagoons",
      "tag_id": "P005_STS_SCADA",
      "alert_type": "STATE",
      "previous_state": 1,
      "state": 3,
      "ts": "2026-04-17T14:32:00+00:00"
    }
  ]
}
```

## Observabilidad

Mensajes relevantes:

- `[COLLECTOR START]`
- `[COLLECTOR CYCLE]`
- `[COLLECTOR EMPTY]`
- `[COLLECTOR SEND STATS]`
- `[SPOOL REPLAY]`
- `[COLLECTOR STARTUP] migrated_spool_lagoons=...`
- `[COLLECTOR WORKER ERROR]`

## Limitaciones conocidas

- `storage/pg_writer.py` sigue sin uso productivo.
- El spool es JSONL local; no hay servicio separado de replay externo.
- El replay es streaming: no carga el spool completo en memoria antes de reprocesarlo.
- La precision del scheduler depende del host y del tiempo de lectura del PLC.

## Documentacion relacionada

- `ARQUITECTURA.md`: arquitectura y flujos.
- `DOCUMENTACION_TECNICA.md`: operacion, tuning y troubleshooting.
