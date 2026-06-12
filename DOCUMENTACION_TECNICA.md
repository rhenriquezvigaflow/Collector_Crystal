# Documentacion Tecnica Operativa

Guia de operacion, tuning y troubleshooting del collector.

**Actualizado:** 2026-06-12

## Comandos clave

Instalar dependencias:

```powershell
pip install -r requirements.txt
```

Ejecutar una laguna:

```powershell
python main.py --config config\Ava_lagoons.yml
```

Ejecutar varias lagunas:

```powershell
python main.py --config collectors.yml
```

El master actual incluye, entre otras, `ary`, `nyah` y `small_sim`.

Batch Windows:

```powershell
run_collector.bat
```

## Contrato minimo de configuracion

Campos base por laguna:

- `lagoon_id`
- `product_type` (`crystal` o `small`; opcional si viene heredado del master)
- `source` (`rockwell`, `siemens` o `simulator`)
- `timezone` (IANA)
- `tags`

En modo master, `product_type` puede definirse globalmente o en cada `plcs[]`.
El override dentro de `plcs[]` tiene prioridad sobre el archivo incluido.
Ejemplo:

```yaml
product_type: "crystal"

plcs:
  - include: "config/lagoon_aquavista.yml"
  - include: "config/small_sim.yml"
    product_type: "small"
```

Campos backend:

- `backend.url`
- `backend.timeout_sec`
- `backend.pool_connections`
- `backend.pool_maxsize`
- `backend.send_events`

Campos runtime:

- `runtime.send_queue_maxsize`
- `runtime.send_queue_full_policy`
- `runtime.spool_on_send_fail`
- `runtime.replay_spool_batch_size`
- `runtime.max_replay_payload_age_sec`
- `runtime.send_retry_attempts`
- `runtime.send_retry_backoff_base_sec`
- `runtime.send_retry_backoff_max_sec`
- `runtime.startup_jitter_max_sec`
- `runtime.log_every_n_cycles`
- `runtime.log_every_n_sends`
- `runtime.enable_state_events`

Campos Rockwell:

- `rockwell.ip`
- `rockwell.slot`
- `rockwell.timeout_sec`
- `force_reconnect_every_sec`
- `max_consecutive_fails`

Campos Siemens:

- `siemens.opc_server_url`
- `siemens.timeout_sec`
- `siemens.username`
- `siemens.password`

Campos Simulator:

- `simulator.seed`
- `simulator.tags`

Si `simulator.tags` no existe, el reader usa `tags`. Los valores pueden ser fijos o specs con `type: float|int|bool|choice|state`.

## Variables de entorno

- `COLLECTOR_API_KEY`: obligatorio para el header `X-Api-Key`.
- `COLLECTOR_LOG_LEVEL`: nivel de salida a consola (`INFO` por defecto).
- `COLLECTOR_SEND_ERROR_LOG_INTERVAL_SEC`: opcional, limita logs repetidos de fallo HTTP.

## Tuning recomendado

Si el backend esta lento:

1. subir `backend.pool_maxsize`
2. subir `runtime.send_queue_maxsize`
3. habilitar `spool_on_send_fail`
4. revisar `send_retry_attempts` y backoff

Si quieres priorizar memoria y datos frescos:

1. bajar `runtime.send_queue_maxsize`
2. bajar `runtime.replay_spool_batch_size`
3. ajustar `runtime.max_replay_payload_age_sec` para descartar backlog demasiado viejo
4. mantener `send_queue_full_policy: drop_newest` para spool seguro

Si hay bursts entre muchas lagunas:

1. usar `startup_jitter_max_sec`
2. revisar `poll_seconds`
3. validar que no todas las lagunas arranquen con el mismo scheduler

Si no quieres perder payloads por saturacion:

- usar `send_queue_full_policy: block`

Tradeoff:

- protege datos, pero puede frenar lectura PLC si el backend no responde.

## Eventos emitidos

Booleanos:

- requieren `event_tags`
- producen `OPEN` y `CLOSE`

Estados enteros:

- requieren `enable_state_events=true`
- ignoran booleanos
- solo consideran enteros `0, 1, 2, 3`
- producen `STATE_CHANGE`

## Spool local

Rutas:

- vigente: `data/spool/<lagoon_id>.jsonl`
- legacy: `data/buffer.jsonl`

Comportamiento:

- el legacy se migra automaticamente al arrancar
- el replay ocurre en batches cuando la cola esta vacia
- el replay es streaming y no carga el spool completo en memoria
- si `max_replay_payload_age_sec > 0`, descarta payloads demasiado antiguos durante el replay
- si un payload del spool vuelve a fallar, queda pendiente para el siguiente ciclo

## Logs utiles

- `[COLLECTOR START]`: confirma source, poll y politica de cola.
- `[COLLECTOR CYCLE]`: muestra tags, eventos, queue y elapsed.
- `[COLLECTOR EMPTY]`: indica ciclos sin datos.
- `[COLLECTOR SEND STATS]`: agrega metricas de envio.
- `[SPOOL REPLAY]`: confirma replay y pendientes restantes.
- `[COLLECTOR WORKER ERROR]`: error fatal de una hebra lectora.

## Troubleshooting rapido

### No llega data al backend

- revisar `backend.url`
- revisar `COLLECTOR_API_KEY`
- revisar timeout HTTP y reachability
- revisar si aparecen archivos en `data/spool`

### El spool crece y no baja

- revisar conectividad al backend
- revisar `send_retry_attempts`
- revisar `backend.pool_maxsize`
- revisar `max_replay_payload_age_sec`
- revisar si la cola nunca queda vacia y por eso el replay no avanza

### Rockwell falla de forma intermitente

- bajar `force_reconnect_every_sec`
- revisar `max_consecutive_fails`
- confirmar `slot` e IP

### Siemens devuelve vacio

- validar `opc_server_url`
- revisar credenciales si aplican
- confirmar que los node ids del YAML siguen vigentes

### Small simulator no se ve en frontend

- validar que `config/small_sim.yml` use `product_type: "small"`
- ejecutar alta backend de `small_sim`
- confirmar que los tags coincidan con `src/assets/positions/small_sim.json`
- revisar `/api/small/lagoons` y `WS /ws/small/small_sim`

## Limitaciones conocidas

- no existe proceso externo dedicado a replay
- `pg_writer` no forma parte del flujo activo
- el collector no hace deduplicacion de payloads: si el PLC envia cambio, el backend decide persistencia/eventos

## Referencias

- `README.md`
- `ARQUITECTURA.md`
- `GUIA_NUEVA_LAGUNA.md`
