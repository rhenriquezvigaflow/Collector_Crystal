# Guia Collector para Agregar una Nueva Laguna

**Actualizado:** 2026-06-12

Esta guia cubre solo el collector. Backend, base de datos y frontend deben usar el mismo `lagoon_id`.

## 1. Campos Minimos

Cada YAML de laguna debe definir:

- `lagoon_id`
- `product_type`: `crystal` o `small`
- `source`: `rockwell`, `siemens` o `simulator`
- `poll_seconds`
- `timezone`
- `backend.url`
- `tags`

`product_type` puede heredarse desde `collectors.yml`, pero se recomienda declararlo en la laguna cuando sea SmallLagoons.

## 2. Ejemplo Rockwell Crystal

```yaml
lagoon_id: "mi_laguna"
product_type: "crystal"
source: rockwell
poll_seconds: 1
timezone: "America/Santiago"

backend:
  url: "http://127.0.0.1:8090/ingest/scada"
  timeout_sec: 3
  send_events: true

rockwell:
  ip: "192.168.16.10"
  slot: 0
  timeout_sec: 1

tags:
  PT117_R: "PT117_R"
  FIT002_R: "FIT002_R"
  P006_ST: "P006_ST"

event_tags:
  P006_ST: "Pump filtracion"
```

## 3. Ejemplo Siemens Crystal

```yaml
lagoon_id: "mi_laguna_siemens"
product_type: "crystal"
source: siemens
poll_seconds: 1
timezone: "America/Santiago"

backend:
  url: "http://127.0.0.1:8090/ingest/scada"

siemens:
  opc_server_url: "opc.tcp://192.168.17.10:4840"
  timeout_sec: 1

tags:
  PT117_R_SCADA: "ns=4;i=3"
```

## 4. Ejemplo SmallLagoons Simulado

```yaml
lagoon_id: "small_sim"
product_type: "small"
source: simulator
poll_seconds: 1
timezone: "America/Santiago"

backend:
  url: "http://127.0.0.1:8090/ingest/scada"

tags:
  "PT-123": 1.4
  "AE-100": 650
  "AE-022": 7.2
  TEMP: 28.4
  ORP: 650
  Dosif: 1.25
```

Para valores aleatorios:

```yaml
simulator:
  seed: 1
  tags:
    TEMP:
      type: float
      min: 24
      max: 31
      decimals: 1
    ORP:
      type: int
      min: 550
      max: 750
    MODE:
      type: choice
      values: ["AUTO", "MANUAL"]
```

## 5. Agregar al Master

En `collectors.yml`:

```yaml
product_type: "crystal"

plcs:
  - include: "config/mi_laguna.yml"
  - include: "config/small_sim.yml"
    product_type: "small"
```

Prioridad de `product_type`:

1. override dentro de `plcs[]`;
2. YAML incluido;
3. valor global del master;
4. default `crystal`.

Valores distintos de `crystal` o `small` detienen el worker al arrancar.

## 6. Ejecutar y Validar

Single:

```powershell
python main.py --config config\mi_laguna.yml
```

Master:

```powershell
python main.py --config collectors.yml
```

Validar en logs:

- `[COLLECTOR START] lagoon=<id> product=<product_type>`
- `[COLLECTOR CYCLE]`
- `[COLLECTOR SEND STATS]`

Validar payload:

- `lagoon_id` coincide con `lagoons.id`;
- `product_type` coincide con backend;
- tags coinciden con `src/assets/positions/<lagoon_id>.json`;
- si backend falla, aparece spool en `data/spool/<lagoon_id>.jsonl`.
