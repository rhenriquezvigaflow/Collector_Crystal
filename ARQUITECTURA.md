# Arquitectura - Collector Python

Documento de arquitectura funcional basado en el codigo actual de `main.py` y modulos asociados.

## 1) Objetivo

Recolectar datos SCADA desde PLCs, normalizarlos y enviarlos a un backend central por HTTP, con tolerancia a fallos de conexion.

## 2) Vista de alto nivel

```text
Config YAML (single o master)
        |
        v
     main.py
        |
        +--> 1 hilo por PLC (ThreadPoolExecutor si hay "plcs")
                 |
                 v
            run_one_plc(cfg)
                 |
                 +--> Reader Rockwell (pycomm3) o Siemens (opcua)
                 +--> TotDeltaNormalizer (WM01_TOT_SCADA -> WM01_TOT_DELTA_SCADA)
                 +--> Detectores de eventos (boolean/state)
                 +--> NormalizedPayload
                 +--> BackendSender (requests POST + X-Api-Key)
```

## 3) Componentes y responsabilidades

| Componente | Archivo | Responsabilidad |
|---|---|---|
| Orquestador | `main.py` | Carga config, selecciona reader, ejecuta loops, maneja multi-PLC |
| Reader Rockwell | `workers/get_rockwell.py` | Conexion persistente y lectura batch de tags |
| Reader Siemens | `workers/get_siemens.py` | Conexion OPC-UA, lectura por nodos y reconexion |
| Normalizador TOT | `normalizer/tot_delta_normalizer.py` | Convierte acumulado TOT a delta por ciclo |
| Payload | `common/payload.py` | Estructura estandar (`lagoon_id`, `source`, `timestamp`, `tags`) |
| Sender HTTP | `common/sender.py` | Envia payload a `backend.url` con header `X-Api-Key` |
| Supervisor | `supervisor.py` | Reinicia `main.py` si el proceso termina |

## 4) Flujo de ejecucion por ciclo

1. `reader.read_once()` obtiene `raw_tags`.
2. Se crea copia defensiva `tags = dict(raw_tags)`.
3. Si existe `WM01_TOT_SCADA`, se calcula `WM01_TOT_DELTA_SCADA`.
4. Se crea `NormalizedPayload` con timestamp UTC.
5. Se detectan eventos:
   - `BooleanEventDetector`: transiciones `False->True` (`OPEN`) y `True->False` (`CLOSE`).
   - `StateEventDetector`: cambios de estado para enteros `0,1,2,3`.
6. Si hay backend configurado, se envia HTTP POST.
7. Se ajusta sleep con `poll_seconds - elapsed`.

## 5) Modelo de concurrencia

- Si el YAML no tiene `plcs`, se ejecuta un solo loop en el hilo principal.
- Si el YAML tiene `plcs`, `main.py` lanza un hilo por PLC via `ThreadPoolExecutor`.
- Cada hilo mantiene su propio reader y estado local de detectores/normalizador.

## 6) Configuracion y topologia

### Topologia single

Un archivo describe un solo PLC.

### Topologia master

`collectors.yml` define `plcs` con `include` de archivos por laguna.  
`main.py` resuelve rutas relativas respecto al archivo maestro.

## 7) Integracion externa

- Protocolo de salida: HTTP POST.
- Header requerido: `X-Api-Key` desde `COLLECTOR_API_KEY`.
- Body actual enviado:
  - `lagoon_id`
  - `source`
  - `timestamp` (UTC ISO-8601)
  - `tags`

## 8) Manejo de fallos

### Rockwell

- Reconexion al perder driver o al cumplir `force_reconnect_every_sec`.
- Contador `max_consecutive_fails` para forzar desconexion/reconexion.
- Ante error de lectura devuelve `{}` y el loop continua.

### Siemens

- Si falla lectura OPC-UA, desconecta y reintenta en siguiente ciclo.
- No rompe el proceso principal.

### Sender HTTP

- Si el backend falla, registra error y retorna `False`.
- El loop de lectura no se detiene.

## 9) Decisiones importantes actuales

- Timestamp de payload se genera en UTC (`common/time.py`).
- `timezone` en config es obligatorio en `main.py`, pero hoy no transforma la salida.
- Los eventos detectados se agregan al objeto payload en memoria, pero no se incluyen en el JSON enviado por `BackendSender`.

## 10) Deuda tecnica identificada

- `storage/jsonl_buffer.py` no esta integrado en el loop.
- `storage/pg_writer.py` no tiene implementacion.
- `common/logger.py` no esta conectado al flujo principal (se usa mayormente `print`).
- Campo `events` del modelo y esquema de envio HTTP no estan alineados.
