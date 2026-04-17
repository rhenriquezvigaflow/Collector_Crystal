# Arquitectura - Collector Python

Documento de arquitectura funcional alineado al codigo actual.

## Objetivo

Leer telemetria SCADA desde PLCs, convertirla a un payload comun y entregarla al backend sin que la capa HTTP degrade el ritmo de lectura.

## Vista de alto nivel

```text
YAML single/master
    |
    v
main.py
    |
    +--> 1 reader loop por PLC
    |       |
    |       +--> RockwellSessionReader | SiemensSessionReader
    |       +--> TotDeltaNormalizer
    |       +--> BooleanEventDetector / StateEventDetector
    |       +--> enqueue payload
    |
    +--> 1 sender thread por laguna
            |
            +--> BackendSender
            +--> send_with_retry
            +--> spool JSONL por laguna
            +--> replay del spool cuando la cola queda vacia
```

## Componentes

| Componente | Archivo | Responsabilidad |
|---|---|---|
| Orquestador | `main.py` | Carga config, crea readers, cola, sender threads y scheduler |
| Reader Rockwell | `workers/get_rockwell.py` | Conexion persistente, batch read, rotacion de conexion |
| Reader Siemens | `workers/get_siemens.py` | Conexion OPC-UA, `get_values`, reconexion ante error |
| Sender HTTP | `common/sender.py` | POST con `requests.Session`, pool y header `X-Api-Key` |
| Spool/Replay | `storage/jsonl_buffer.py` | Persistencia por laguna, replay, migracion del buffer legacy |
| Payload | `common/payload.py` | Modelo Pydantic del payload normalizado |
| TOT delta | `normalizer/tot_delta_normalizer.py` | Calcula `WM01_TOT_DELTA_SCADA` |
| Supervisor | `supervisor.py` | Reinicia `main.py` cuando el proceso cae |

## Flujo por ciclo

1. `load_plc_configs()` expande el master YAML y resuelve `include`.
2. `run_one_plc()` crea el reader segun `source`.
3. El reader hace `read_once()` y devuelve `tags`.
4. Si viene `WM01_TOT_SCADA`, se agrega `WM01_TOT_DELTA_SCADA`.
5. Se construye `NormalizedPayload` con timestamp UTC.
6. Si hay `event_tags`, `BooleanEventDetector` genera `OPEN` y `CLOSE`.
7. Si `enable_state_events=true`, `StateEventDetector` detecta cambios enteros `0..3`.
8. El payload se encola segun la politica de cola.
9. `sender_worker_loop()` intenta enviar:
   - HTTP directo
   - reintentos con backoff exponencial
   - spool si sigue fallando
10. Si la cola queda vacia, el sender intenta reprocesar `data/spool/<lagoon>.jsonl`.
11. El replay se hace en streaming y puede descartar payloads viejos segun `max_replay_payload_age_sec`.

## Modelo de concurrencia

- Single PLC:
  - 1 reader loop.
  - 1 sender thread si hay `backend.url`.
- Multi PLC:
  - 1 reader loop por PLC en `ThreadPoolExecutor`.
  - 1 sender thread por laguna.
- La cola por laguna desacopla PLC y backend.

## Spool y replay

Formato vigente:

- `data/spool/<lagoon_id>.jsonl`

Compatibilidad:

- Si existe `data/buffer.jsonl`, al arranque se migra al formato por laguna.

Semantica:

- `append_for_lagoon()` escribe de forma thread-safe.
- `replay_for_lagoon()` mueve el archivo a `.work`, reintenta un batch y recompone pendientes.
- El replay no carga el archivo completo a RAM; procesa linea por linea.
- El replay ocurre solo cuando la cola en memoria esta vacia para no competir con trafico fresco.

## Manejo de fallos

### Rockwell

- Rota la conexion por tiempo (`force_reconnect_every_sec`).
- Desconecta si supera `max_consecutive_fails`.
- Devuelve `{}` ante error y el loop sigue vivo.

### Siemens

- Reconecta cuando falla `get_values`.
- Mantiene cache de nodos para batch reads.

### Sender HTTP

- Si falta `COLLECTOR_API_KEY`, no envia.
- Usa `send_retry_attempts` antes de declarar fallo.
- Si `spool_on_send_fail=true`, persiste el payload.
- Si `max_replay_payload_age_sec > 0`, el replay puede descartar backlog demasiado viejo.
- Si la cola se llena:
  - `drop_newest`: descarta el nuevo.
  - `drop_oldest`: saca uno viejo y mete el nuevo.
  - `block`: aplica backpressure al reader.

## Decisiones clave

- Timestamps del payload siempre en UTC.
- La timezone por laguna se usa para logging y observabilidad.
- Los eventos viajan en el mismo payload solo si `backend.send_events=true`.
- El scheduler usa `next_tick` para limitar drift cuando el host puede sostener la frecuencia.

## Deuda tecnica

- No hay pipeline separado para drenar spool desde otro proceso.
- `storage/pg_writer.py` no participa del flujo productivo actual.
