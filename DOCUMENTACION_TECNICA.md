# Documentacion Tecnica Operativa

Guia corta para operar y mantener el collector segun el estado actual del repositorio.

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

Ejecucion por batch (Windows):

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

- Si `rockwell`: `rockwell.ip`, `rockwell.slot` (opcional, default 0).
- Si `siemens`: `siemens.opc_server_url` (`timeout_sec`, `username`, `password` opcionales).

Campos operativos:

- `poll_seconds` (default 1).
- `force_reconnect_every_sec` y `max_consecutive_fails` (Rockwell).
- `backend.url` (necesario para envio HTTP).

## 3. Variables de entorno

- `COLLECTOR_API_KEY`: se envia en header `X-Api-Key`.

Sin esta variable, el sender registra error y el backend puede rechazar requests.

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

## 5. Senales de salud en consola

- Inicio: `START <source> lagoon=<id>`
- Ciclo OK: `OK <source> lagoon=<id> utc=... tags=<n> events=<n> cycle=<ms>`
- Error ciclo: `ERR <source> lagoon=<id> err=... cycle=<ms>`

## 6. Troubleshooting rapido

Error de conexion PLC:

- Verificar IP/endpoint en YAML.
- Validar conectividad de red desde el host.
- Revisar credenciales Siemens si aplica.

No llega data al backend:

- Verificar `backend.url`.
- Verificar `COLLECTOR_API_KEY`.
- Confirmar endpoint y respuesta HTTP del backend.

Loop con tags vacios:

- Revisar nombres/NodeId en `tags`.
- Confirmar que esos tags existen en PLC/OPC server.

## 7. Limites actuales conocidos

- No hay persistencia local activa en el loop (JSONL/PG no integrados).
- `pg_writer.py` sin implementacion.
- `events` no se envian en el request HTTP actual.

## 8. Referencias

- Arquitectura completa: `ARQUITECTURA.md`
- Guia de uso rapido: `README.md`
