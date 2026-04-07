# Arquitectura - Collector Python

Documento de arquitectura funcional basado en el codigo actual.

## 1) Objetivo

Recolectar datos SCADA desde PLCs y enviarlos por HTTP manteniendo fluidez con muchas lagunas (ej: 50) aun con latencia o fallos de backend.

## 2) Vista de alto nivel

```text
Config YAML (single/master)
        |
        v
     main.py
        |
        +--> 1 hilo lector por PLC (ThreadPoolExecutor)
                 |
                 +--> Reader Rockwell / Siemens
                 +--> TotDeltaNormalizer
                 +--> Event detectors (boolean/state)
                 +--> Enqueue payload (cola local por laguna)
                              |
                              v
                         1 hilo sender por laguna
                              |
                              +--> BackendSender (HTTP Session + pool)
                              +--> (opcional) spool JSONL en fallos
```

## 3) Componentes y responsabilidades

| Componente | Archivo | Responsabilidad |
|---|---|---|
| Orquestador | `main.py` | Carga config, lanza 1 hilo por PLC, controla ritmo, cola y sender thread |
| Reader Rockwell | `workers/get_rockwell.py` | Conexion persistente, lectura batch y mapeo optimizado de tags |
| Reader Siemens | `workers/get_siemens.py` | Conexion OPC-UA, lectura batch `get_values`, reconexion |
| Normalizador TOT | `normalizer/tot_delta_normalizer.py` | Convierte acumulado TOT a delta por ciclo |
| Payload | `common/payload.py` | Modelo estandar de payload |
| Sender HTTP | `common/sender.py` | POST con `requests.Session`, pool y `X-Api-Key` |
| Buffer JSONL | `storage/jsonl_buffer.py` | Persistencia local thread-safe para fallos de envio |
| Supervisor | `supervisor.py` | Reinicia `main.py` si el proceso cae |

## 4) Flujo de ejecucion por ciclo

1. `reader.read_once()` obtiene `raw_tags`.
2. Se construye `tags = dict(raw_tags or {})`.
3. Si existe `WM01_TOT_SCADA`, se calcula `WM01_TOT_DELTA_SCADA`.
4. Se crea `NormalizedPayload` con timestamp UTC.
5. Se detectan eventos:
   - `BooleanEventDetector`: transiciones `False->True` (`OPEN`) y `True->False` (`CLOSE`).
   - `StateEventDetector`: cambios de estado para enteros `0,1,2,3` (ignora boolean).
6. El payload se encola para envio asincrono.
7. El sender thread hace `POST`; si falla, opcionalmente escribe en `buffer.jsonl`.
8. El loop lector duerme con scheduler de `next_tick` para mantener frecuencia.

## 5) Modelo de concurrencia

- Modo single: un hilo lector + (si hay backend) un hilo sender.
- Modo master: un hilo lector por PLC + un hilo sender por PLC.
- Lectura y envio desacoplados por `Queue`, evitando que latencia HTTP bloquee PLC.

## 6) Integracion externa

- Protocolo: HTTP `POST`.
- Header requerido: `X-Api-Key` desde `COLLECTOR_API_KEY`.
- Body base:
  - `lagoon_id`
  - `source`
  - `timestamp` (UTC ISO-8601)
  - `tags`
- `events` se incluye solo si `backend.send_events: true`.

## 7) Manejo de fallos

### Rockwell

- Reconecta por rotacion (`force_reconnect_every_sec`) o exceso de fallos (`max_consecutive_fails`).
- Ante error de lectura devuelve `{}` y el loop continua.

### Siemens

- Si falla lectura OPC-UA, desconecta y reintenta en proximo ciclo.
- La lectura es batch (un roundtrip de datos por ciclo).

### Sender HTTP

- Si el backend falla, el sender retorna `False`.
- Si `runtime.spool_on_send_fail=true`, guarda payload en JSONL local.
- Si la cola se llena:
  - `drop_newest`: descarta payload nuevo.
  - `drop_oldest`: descarta el mas antiguo en cola.
  - `block`: hace backpressure al lector.

## 8) Config de performance relevante

- `backend.timeout_sec`
- `backend.pool_connections`
- `backend.pool_maxsize`
- `runtime.send_queue_maxsize`
- `runtime.send_queue_full_policy`
- `runtime.spool_on_send_fail`
- `runtime.startup_jitter_max_sec`
- `runtime.log_every_n_cycles`
- `runtime.log_every_n_sends`
- `runtime.enable_state_events`

## 9) Decisiones tecnicas clave

- Timestamp enviado en UTC; timezone de laguna se usa para observabilidad local en logs.
- Se usa `requests.Session` para keep-alive y menor costo por request.
- Se introdujo jitter inicial para evitar burst sincronizado entre lagunas.

## 10) Deuda tecnica pendiente

- `storage/pg_writer.py` sin implementacion.
- Falta componente de replay automatico del `buffer.jsonl`.
