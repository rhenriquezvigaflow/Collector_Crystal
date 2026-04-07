# Documentacion Tecnica Operativa

Guia operativa del collector para ejecucion y ajuste de performance.

## 1. Comandos clave

Instalar dependencias:

```powershell
pip install -r requirements.txt
```

Ejecutar una laguna:

```powershell
python main.py --config config\Ava_lagoons.yml
```

Ejecutar modo multi-laguna:

```powershell
python main.py --config collectors.yml
```

Batch Windows:

```powershell
run_collector.bat
```

## 2. Contrato minimo de configuracion

Campos requeridos por laguna:

- `lagoon_id`
- `source` (`rockwell` o `siemens`)
- `timezone` (IANA)
- `tags`

Campos por tipo:

- Rockwell: `rockwell.ip`, `rockwell.slot` (opcional), `rockwell.timeout_sec` (opcional).
- Siemens: `siemens.opc_server_url`, `siemens.timeout_sec` (opcional), `username/password` (opcionales).

Campos backend:

- `backend.url`
- `backend.timeout_sec` (default 3)
- `backend.pool_connections` (default 50)
- `backend.pool_maxsize` (default 200)
- `backend.send_events` (default false)

Campos runtime:

- `runtime.send_queue_maxsize` (default 1000)
- `runtime.send_queue_full_policy` (`drop_newest` | `drop_oldest` | `block`)
- `runtime.spool_on_send_fail` (default true)
- `runtime.startup_jitter_max_sec` (default `min(0.25, poll_seconds)`)
- `runtime.log_every_n_cycles` (default 10)
- `runtime.log_every_n_sends` (default 100)
- `runtime.enable_state_events` (default true)

## 3. Variables de entorno

- `COLLECTOR_API_KEY` se envia en header `X-Api-Key`.

Sin API key, el sender no envia y retorna fallo.

## 4. Formato de salida HTTP

`POST {backend.url}`

```json
{
  "lagoon_id": "costa_del_lago",
  "source": "rockwell",
  "timestamp": "2026-02-25T18:32:00.000000+00:00",
  "tags": {
    "PT117_R_SCADA": 10.2
  }
}
```

Si `backend.send_events=true`, se agrega el arreglo `events` cuando hay eventos.

## 5. Senales de salud (logs)

- `START source=<source> lagoon=<id> poll=<sec> queue=<n> policy=<policy>`
- `OK source=<source> lagoon=<id> utc=<ts> local=<ts> tags=<n> events=<n> cycle=<ms> queue=<n> dropped=<n>`
- `SEND lagoon=<id> sent=<n> failed=<n> queue=<n>`
- `EMPTY source=<source> lagoon=<id>`
- `ERR source=<source> lagoon=<id> err=<msg>`

## 6. Troubleshooting rapido

Error de conexion PLC:

- Verificar IP/endpoint en YAML.
- Validar conectividad de red desde el host.
- Revisar credenciales Siemens si aplica.

No llega data al backend:

- Verificar `backend.url`.
- Verificar `COLLECTOR_API_KEY`.
- Confirmar timeout (`backend.timeout_sec`) y saturacion de cola (`queue`, `dropped` en logs).

Cola creciendo o drops:

- Aumentar `runtime.send_queue_maxsize`.
- Aumentar `backend.pool_maxsize`.
- Revisar latencia/errores del backend.
- En caso extremo, usar `runtime.send_queue_full_policy: block` para priorizar no perder datos (con riesgo de frenar lectura).

## 7. Buffer local

- Archivo: `data/buffer.jsonl`.
- Se escribe cuando hay fallo de envio o drop de cola y `runtime.spool_on_send_fail=true`.
- Actualmente no hay replay automatico a backend.

## 8. Limites actuales conocidos

- `storage/pg_writer.py` sin implementacion.
- No existe proceso de replay JSONL integrado.

## 9. Referencias

- Arquitectura: `ARQUITECTURA.md`
- Guia general: `README.md`
