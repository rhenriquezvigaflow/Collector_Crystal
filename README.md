# Collector Python - Crystal Lagoons

Collector SCADA en Python para leer tags de PLCs (Rockwell y Siemens) y enviarlos a un backend HTTP.

## Estado real del proyecto

El comportamiento actual del codigo en `main.py` es:

- Lee tags en ciclo continuo (`poll_seconds`).
- Soporta `source: rockwell` y `source: siemens`.
- Soporta ejecucion de 1 o N PLCs desde un `collectors.yml` maestro con `include`.
- Normaliza `WM01_TOT_SCADA` a `WM01_TOT_DELTA_SCADA`.
- Detecta eventos de cambio de estado (booleanos y enteros 0-3).
- Envia datos al backend por `POST` con header `X-Api-Key`.

## Requisitos

- Python 3.10+ recomendado.
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

Archivo `.env` (ejemplo):

```env
COLLECTOR_API_KEY=tu-api-key
```

### Modo 1: un solo PLC

```yaml
lagoon_id: "aquavista"
source: "siemens"   # rockwell | siemens
poll_seconds: 1
timezone: "America/Mexico_City"

backend:
  url: "http://localhost:8000/ingest/scada"

siemens:
  opc_server_url: "opc.tcp://192.168.17.10:4840"
  timeout_sec: 1

tags:
  Tags_01_Real: "ns=4;i=3"
```

### Modo 2: multiples PLCs (master)

```yaml
backend:
  url: "http://localhost:8000/ingest/scada"

plcs:
  - include: "config/lagoon_aquavista.yml"
  - include: "config/lagoon_costadellago.yml"
  - include: "config/Ava_lagoons.yml"
```

## Campos importantes de config

- `lagoon_id` (requerido): identificador de laguna.
- `source` (requerido): `rockwell` o `siemens`.
- `timezone` (requerido): zona IANA valida (ej. `America/Asuncion`).
- `tags` (requerido): mapa `tag_logica -> tag_plc`.
- `backend.url` (opcional en codigo, practico requerido para envio).
- `poll_seconds` (opcional, default `1`).
- `force_reconnect_every_sec` y `max_consecutive_fails` (usado por Rockwell).
- `event_tags` (opcional): tags booleanos a monitorear para eventos `OPEN/CLOSE`.

## Ejecucion

### Directo por CLI

```powershell
python main.py --config collectors.yml
```

o con un archivo de una laguna:

```powershell
python main.py --config config\Ava_lagoons.yml
```

### Script Windows

```powershell
run_collector.bat
```

Este script:
- activa `.venv`
- ejecuta `main.py --config collectors.yml`
- si el proceso termina con error, inicia `supervisor.py`.

## Payload enviado al backend

Actualmente `BackendSender` envia:

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

Nota: aunque se detectan eventos en memoria, hoy no se envian en el JSON HTTP.

## Observabilidad

La salida principal hoy es por consola (`print` y logs de `requests`/sender).

Ejemplos:

- `START rockwell lagoon=ava_lagoons`
- `OK rockwell lagoon=ava_lagoons utc=... tags=11 events=1 cycle=120.4ms`
- `ERR siemens lagoon=aquavista err=... cycle=1001.0ms`

## Limitaciones actuales (importante)

- `timezone` se valida/carga, pero no se aplica al timestamp del payload (se envia UTC).
- `events` se calculan pero no viajan en el request HTTP.
- `storage/jsonl_buffer.py` existe, pero no se usa desde `main.py`.
- `storage/pg_writer.py` esta vacio.
- `common/logger.py` existe, pero no esta integrado en el flujo principal actual.

## Arquitectura

Ver documento detallado en [ARQUITECTURA.md](ARQUITECTURA.md).
