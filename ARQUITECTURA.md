# 🏗️ Arquitectura - Collector Python

**Versión:** 1.0  
**Fecha:** 26 de Enero de 2026  
**Proyecto:** Crystal Lagoons - Collector Python  
**Estado:** ✅ Producción

---

## 📋 Tabla de Contenidos

1. [Visión General](#visión-general)
2. [Componentes Principales](#componentes-principales)
3. [Flujo de Datos](#flujo-de-datos)
4. [Capas de la Arquitectura](#capas-de-la-arquitectura)
5. [Módulos](#módulos)
6. [Patrones de Diseño](#patrones-de-diseño)
7. [Ciclo de Vida](#ciclo-de-vida)
8. [Configuración](#configuración)
9. [Almacenamiento](#almacenamiento)
10. [Manejo de Errores](#manejo-de-errores)
11. [Dependencias Externas](#dependencias-externas)

---

## Visión General

**Collector Python** es un sistema de recopilación de datos industriales en tiempo real que:

- ✅ Lee datos de controladores PLC (Rockwell, Siemens)
- ✅ Normaliza los datos en payloads estándar
- ✅ Almacena datos locales (PostgreSQL)
- ✅ Envía datos a un backend centralizado
- ✅ Implementa reconexión automática y recuperación ante fallos
- ✅ Funciona continuamente en modo daemon

### Tipos de Datos Soportados

| Origen | Protocolo | Clase | Librería | Estado |
|--------|-----------|-------|----------|--------|
| Rockwell (Allen-Bradley) | EthernetIP/ OPC-UA | `RockwellSessionReader` | pycomm3 1.2.16 | ✅ Activo |
| Siemens (S7) | OPC-UA | `SiemensSessionReader` | opcua 0.98.13 | ✅ Activo |

---

## Componentes Principales

```
┌─────────────────────────────────────────────────────────┐
│                    APLICACIÓN PRINCIPAL                 │
│                     (main.py)                           │
└─────────────────────────────────────────────────────────┘
                            │
                ┌───────────┼───────────┐
                │           │           │
         ┌──────▼────┐  ┌──▼─────┐  ┌─▼──────────┐
         │  Rockwell │  │Siemens │  │Configuration
         │  Reader   │  │Reader  │  │Manager
         └──────┬────┘  └──┬─────┘  └─┬──────────┘
                │           │          │
                └───────────┴──────────┘
                            │
                ┌───────────▼───────────┐
                │  Payload Normalizer   │
                │  (NormalizedPayload)  │
                └───────────┬───────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
         ┌──────▼────────┐      ┌─────▼──────┐
         │  Local Storage │     │   Backend  │
         │   - PostgreSQL │     │   Sender   │
         │                │     │ (HTTP POST)│
         │                │     └────────────┘
         └────────────────┘
```

---

## Flujo de Datos

### Ciclo Principal de Lectura

```
┌─────────────────────────────────────────────────────────┐
│ 1. INICIO DEL CICLO                                     │
│    - Marca tiempo de inicio (cycle_start)               │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 2. LECTURA DE PLC                                       │
│    - RockwellSessionReader.read_once() o               │
│    - SiemensSessionReader.read_once()                  │
│    - Retorna: dict[tag_id] = value                     │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 3. NORMALIZACIÓN                                        │
│    - Crea NormalizedPayload:                           │
│      {lagoon_id, source, timestamp, tags}              │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 4. ALMACENAMIENTO                                       │
│    - PostgreSQL                                         │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 5. ENVÍO AL BACKEND                                     │
│    - BackendSender.send(payload)                        │
│    - HTTP POST a endpoint configurado                   │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 6. CÁLCULO DE DELAY                                     │
│    - elapsed = time.perf_counter() - cycle_start        │
│    - sleep_for = poll_seconds - elapsed                 │
│    - Si sleep_for > 0: time.sleep(sleep_for)            │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 7. LOG DE CICLO                                         │
│    - Imprime: timestamp, cantidad tags, tiempo ciclo    │
└────────────────┬────────────────────────────────────────┘
                 │
                 └─────────────────────┐
                                       │
                                 (Repetir)
```

---

## Capas de la Arquitectura

### 1. **Capa de Presentación/Punto de Entrada**
- **Archivo:** `main.py`
- **Responsabilidades:**
  - Parseo de argumentos CLI
  - Carga de configuración YAML
  - Selección de worker (Rockwell/Siemens)
  - Orquestación del loop principal
- **Flujo:** `main() → load_config() → run_rockwell() / run_siemens()`

### 2. **Capa de Lectura (Workers)**
- **Ubicación:** `workers/`
- **Clases:**
  - `RockwellSessionReader` (`pycomm3` 1.2.16)
  - `SiemensSessionReader` (`opcua` 0.98.13)
- **Responsabilidades:**
  - Conexión persistente al PLC (sesión stateful)
  - Lectura batch de todos los tags en un ciclo
  - Reconexión automática con contador de fallos
  - Rotación forzada cada N segundos
  - Manejo de errores de conexión y timeout
- **Patrón:** Session-based reader con reintentos y rotación periódica
- **Constantes Clave:**
  - `RECONNECT_DELAY = 5` segundos (entre intentos)
 (Pydantic BaseModel)
- **Estructura:**
  ```python
  NormalizedPayload(
      plant_id: ,              # Identificador único de planta/laguna
      source: str,                 # "rockwell" | "siemens"
      timestamp: datetime,         # UTC con microsegundos
      tags: dict[str, Any]        # {tag_id: value, ...}
  )
  ```
- **Responsabilidades:**
  - Validación Pydantic de estructura de datos
  - Serialización automática a JSON
  - Independencia de origen (abstracción)
- **Métodos Clave:**
  - `model_dump_json()` → JSON string para JSONL
  - Estructura estándar: `{lagoon_id, source, timestamp, tags}`
  - Serialización JSON automática
- **Ventaja:** Independencia de origen de datos (Rockwell, Siemens)

### 4. **Capa de Almacenamiento**
- **Ubicación:** `storage/`
- **Componentes:**
  - `jsonl_buffer.py` - Buffer local en JSONL
  - `sqlite_buffer.py` - Base de datos SQLite local
  - `pg_writer.py` - Escritor PostgreSQL
- **Responsabilidades:**
  - Persistencia de datos
  - Buffer ante desconexiones

### 5. **Capa de Integración**
- **Ubicación:** `common/sender.py`
- **Clase:** `BackendSender`
- **Responsabilidades:**
  - Envío HTTP POST al backend
  - Manejo de timeouts
  - Logging de errores
  - Tolerancia a fallos (no detiene lectura)

### 6. **Capa de Utilidades**
- **Ubicación:** `common/`
- **Módulos:**
  - `logger.py` - Logging centralizado
  - `time.py` - Utilidades de tiempo (UTC)
  - `payload.py` - Definición de estructura

---

## Módulos

### 📦 `common/`

#### `payload.py`
```python
class NormalizedPayload(BaseModel):
    lagoon_id:           # Identificador único de laguna
    source: str              # "rockwell" | "siemens"
    timestamp: datetime      # Marca de tiempo UTC
    tags: dict[str, Any]     # Valores de tags -> {tag_id: value}
```

#### `sender.py`
- **Clase:** `BackendSender(url, timeout=3.0)`
- **Métodos:**
  - `send(payload: NormalizedPayload) -> bool`
- **Comportamiento:** 
  - POST JSON a endpoint
  - Retry automático no implementado (fail gracefully)
  - Continúa operación si backend no disponible

#### `logger.py`
- **Función:** `get_logger() -> logging.Logger`
- **Configuración:**
  - Salida dual: archivo + consola
  - Archivo: `logs/collector.log`
  - Formato: `"%(asctime)s | %(levelname)s | %(message)s"`

#### `time.py`
- **Función:** `utc_now() -> datetime`
- **Propósito:** Timestamp UTC estandarizado

---

### 📦 `workers/`

#### `get_rockwell.py`
```python
class RockwellSessionReader:
    def __init__(
        ip: str,
        slot: int,
        tag_map: dict,
        force_reconnect_every_sec: int = 3600,
        max_consecutive_fails: int = 10
    )
    
    def read_once(self) -> dict[str, Any]
        # Retorna {tag_id: value, ...}
    
    def should_rotate(self) -> bool
        # Verifica si debe reconectarse
```

**Características:** (ej: "opc.tcp://192.168.17.10:4840")
        tag_map: dict,              # Mapeo {logical_id: node_id} (ej: {"temp": "ns=4;i=3"})
        timeout_sec: int = 4,       # Timeout de conexión
        username: str = None,       # Autenticación opcional
        password: str = None        # Autenticación opcional
    )
    
    def read_once(self) -> dict[str, Any]  # Lectura batch de todos los tags
```

**Características:**
- **Protocolo:** OPC-UA (estándar IEC 62541)
- **Librería:** `opcua` 0.98.13
- **Endpoint:** `opc.tcp://hostname:port` (puerto defecto 4840)
- **Tag addressing:** Namespace + Node ID (ej: "ns=4;i=3")
- **Autenticación:** Soporte para username/password
- **Timeout:** Configurable para conexión y lectura
- **Sesión persistente:** Mantiene suscripciones activas entre ciclos= None
    )
    
    def read_once(self) -> dict[str, Any]
```

**Características:**
- Protocolo: OPC-UA
- Endpoint: `opc.tcp://ip:port`
- Autenticación opcional
- Timeout configurable

---

### 📦 `storage/`

#### `jsonl_buffer.py`
```python
def append(payload_json: str)
    # Escribe payload JSON (una línea por registro)
    # Archivo: data/buffer.jsonl
```

#### `sqlite_buffer.py` / `pg_writer.py`
- Almacenamiento en bases de datos
- Esquema: tabla de eventos con timestamp
- Permite histórico completo

---

## Patrones de Diseño

### 1. **Pattern: Session Reader**
Ambos workers implementan el patrón Session Reader:

```
reader = XxxSessionReader(config)
    ↓
while True:
    data = reader.read_once()  # Maneja conexión internamente
    process(data)
```

**Ventajas:**
- Abstracción de detalles de conexión
- Reconexión automática transparente
- Estado compartido (driver, contadores)

### 2. **Pattern: Payload Normalization**
Datos heterogéneos → Estructura uniforme:

```
RockwellTags → NormalizedPayload
    ↑           ↑
SiemensValues→ (lagoon_id, source, timestamp, tags)
                          ↓
                  BackendSender / Storage
```

### 3. **Pattern: Graceful Degradation**
Si backend no está disponible:
```
sender.send(payload)  # Retorna False pero continúa
# La aplicación sigue leyendo del PLC
```

### 4. **Pattern: Configuration-Driven**
YAML externo controla:
- Qué PLC (Rockwell/Siemens)
- Dónde conectar (IP, endpoint)
- Qué tags leer
- Intervalos de polling
- Destinos de almacenamiento

---

## Ciclo de Vida

### Inicio
```
python main.py --config config/lagoon_aquavista.yml
    ↓
load_config(path)  # YAML → dict
    ↓
RockwellSessionReader.__init__()
    ↓
Crea LogixDriver (no conecta aún)
    ↓
Inicia loop infinito
```

### Durante Ejecución
```
┌─────────────────────────────────┐
│ read_once()                     │
├─────────────────────────────────┤
│ if not _driver or should_rotate │
│     → _disconnect()             │
│     → _connect()                │
│         ↓                       │
│     Crea conexión Ethernet/IP   │
│     Reset contadores            │
└─────────────────────────────────┘
           ↓
┌─────────────────────────────────┐
│ Lee cada tag del tag_map        │
│ _driver.read(plc_tag)           │
│ Retorna dict con valores        │
└─────────────────────────────────┘
           ↓
┌─────────────────────────────────┐
│ Crea NormalizedPayload          │
│ Serializa a JSON                │
└─────────────────────────────────┘
           ↓
┌─────────────────────────────────┐
│ Backend sender.send() (opt.)    │
│ Storage buffer.append() (opt.)  │
└─────────────────────────────────┘
           ↓
┌─────────────────────────────────┐
│ Espera: poll_seconds - elapsed  │
│ Repite desde inicio             │
└─────────────────────────────────┘
```

### Terminación
- **Señal:** `Ctrl+C` (SIGINT)
- **Comportamiento:** Cierra conexión PLC en `_disconnect()`
- **Actual:** Sin limpieza explícita (todo es daemon)

---

## Configuración

### Estructura YAML

```yaml
# Identificación
lagoon_id: "laguna_id"
source: "rockwell" | "siemens"

# Timing
poll_seconds: 1.0                    # Cada cuánto leer
force_reconnect_every_sec: 3600      # Reconectar cada N seg
max_consecutive_fails: 10            # Fallos antes de reconectar

# Rockwell (si source: rockwell)
rockwell:
  ip: "192.168.1.100"
  slot: 0

# Siemens (si source: siemens)
siemens:
  opc_server_url: "opc.tcp://ip:port"
  timeout_sec: 4
  username: null                     # Opcional
  password: null                     # Opcional

# Tags a leer (mapeo lógico → dirección PLC)
tags:
  logical_id_1: "PLC_address_1"
  logical_id_2: "PLC_address_2"

# Backend 
backend:
  url: "http://localhost:8000/ingest/scada"
```

### Archivo de Ejemplo: `lagoon_aquavista.yml`
```yaml
lagoon_id: "laguna_id"
source: siemens
poll_seconds: 1

force_reconnect_every_sec: 3600
max_consecutive_fails: 10

backend:
  url: "http://localhost:8000/ingest/scada"

siemens:
  opc_server_url: "opc.tcp://192.168.17.10:4840"
  timeout_sec: 4

tags:
  Tags_01_Real: "ns=4;i=3"
  Tags_02_Real: "ns=4;i=4"
  Tags_03_Real: "ns=4;i=5"
  Tags_04_Real: "ns=4;i=18"
```

### Variables de Entorno
- Actualmente: No configuradas
- Recomendación futura: Backend URL, credenciales

---

## Almacenamiento

### Jerarquía de Persistencia

```
Memoria (ciclo actual)
    ↓

┌───────────────────────────────┐
│ PostgreSQL (remoto)           │ ← Escalable, backup
│ centralizado                  │
└───────────────────────────────┘
    ↓ 
┌───────────────────────────────┐
│ Backend HTTP                  │ ← Procesamiento remoto
│ POST /ingest/scada            │
└───────────────────────────────┘
```

### Formatos de Datos

#### HTTP POST (Backend)
```json
{
  "lagoon_id": "b723d4a9-2f2f-474b-b87f-0dfce68c18e8",
  "source": "siemens",
  "timestamp": "2026-01-23T14:30:45.123456+00:00",
  "tags": {
    "Tags_01_Real": 23.5,
    "Tags_02_Real": 18.2
  }
}
```

---

## Manejo de Errores

### Estrategias por Capas

#### Capa de Lectura (Workers) - Tolerancia con Contador
```python
try:
    if not self._driver or self.should_rotate():
        self._disconnect()
        self._connect()
        self._last_connect_ts = time.time()
        self._consecutive_fails = 0  # Reset contador
    
    values = {}
    for tag_id, plc_tag in self.tag_map.items():
        result = self._driver.read(plc_tag)
        values[tag_id] = result.value
    
    self._consecutive_fails = 0  # Reset en éxito
    return values
    
except Exception as e:
    self._consecutive_fails += 1
    if self._consecutive_fails >= self.max_consecutive_fails:
        self._disconnect()
        # Siguiente ciclo tentará reconectar
```

**Comportamiento:**
- ✅ Tolera fallos transitivos sin reconectar
- ✅ Reconecta tras N fallos consecutivos
- ✅ Fuerza reconexión cada N segundos (previene bloqueos)
- ✅ Reset de contador en éxito

#### Capa de Envío (Backend) 
```python
def send(self, payload):
    try:
        r = requests.post(self.url, json=..., timeout=3.0)
        r.raise_for_status()
        return True
    except Exception as e:
        logger.warning(f"backend unreachable: {e}")
        return False  # ✅ No detiene lectura del PLC
```

**Comportamiento:**
- ✅ NO reintentos automáticos (fail-fast)
- ✅ Logs de advertencia solamente
- ✅ Aplicación continúa leyendo PLCs
- ✅ Datos respaldados en buffer.jsonl

---

## Dependencias Externas

### Librerías Principales

| Librería | Versión | Propósito | Uso |
|----------|---------|----------|-----|
| `pycomm3` | 1.2.16 | Driver Rockwell | `workers/get_rockwell.py` |
| `opcua` | 0.98.13 | Cliente OPC-UA (Siemens) | `workers/get_siemens.py` |
| `requests` | - | HTTP client | `common/sender.py` |
| `pydantic` | 2.12.5 | Validación de datos | `common/payload.py` |
| `PyYAML` | 6.0.3 | Parseo YAML | `main.py` |

### Librerías de Soporte
- `lxml` - Parsing XML (requerido por opcua)
- `python-dateutil` - Utilidades de fecha
- `pytz` - Soporte de zonas horarias


---



## Diagrama de Despliegue

```
┌──────────────────────────────────────────────────────────┐
│                  SERVIDOR COLLECTOR                      │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Proceso Python (main.py)                           │ │
│  │                                                    │ │
│  │ ┌─────────────────────────────────────────────┐   │ │
│  │ │ RockwellSessionReader | SiemensSessionReader│   │ │
│  │ └────────────┬────────────────────────────────┘   │ │
│  │              │                                    │ │
│  │ ┌────────────▼────────────────────────────────┐   │ │
│  │ │ NormalizedPayload                          │   │ │
│  │ └────────────┬────────────────────────────────┘   │ │
│  │              │                                    │ │
│  │    ┌─────────┼──────────┐                         │ │
│  │    ▼         ▼          ▼                         │ │
│  │ [JSONL]  [SQLite]  [PostgreSQL]  [Backend HTTP]   │ │
│  │ Local    Local      Remoto       API              │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│   FILES:                                               │
│   - logs/collector.log                                 │
│   - data/buffer.jsonl                                  │
│   - data/collector.db (si SQLite)                      │
└──────────────────────────────────────────────────────────┘
          ▲                          ▲
          │                          │
          ▼                          ▼
┌──────────────────────┐    ┌─────────────────────┐
│ PLC Rockwell/Siemens │    │ Backend Centralizado│
│ en planta            │    
└──────────────────────┘    └─────────────────────┘
```

---

## Matriz de Compatibilidad

### Plataformas Soportadas
- ✅ Windows (run.bat)
- ✅ Linux (python main.py)
- ✅ macOS (python main.py)

### Versiones Python
- ✅ Python 3.8+
- ✅ Python 3.10+ (recomendado)
- ✅ Python 3.11+

- ✅ PostgreSQL (remoto, requiere servidor)

---

## Resumen Ejecutivo

## Resumen Ejecutivo

| Aspecto | Descripción | Especificación |
|--------|-------------|----------------|
| **Tipo** | Collector de datos industrial | Aplicación daemon Python |
| **Entrada** | Configuración YAML + Tags desde PLC | YAML + diccionarios |
| **Procesamiento** | Loop continuo con polling | `time.perf_counter()` para precisión |
| **Salida** | JSONL + SQLite + PostgreSQL + HTTP | Append-only, no sobrescribe |
| **Escalabilidad** | Vertical (1 proceso por planta) | Multi-instancia posible |
| **Disponibilidad** | 24/7 con reconexión automática | MTTR < 1min típico |
| **Recuperación** | Buffer local (data/buffer.jsonl) | Respaldo ante backend down |
| **Overhead** | < 100MB RAM, < 5% CPU | En inactividad |
| **Throughput** | 100-1000 tags/seg | Depende del PLC |
| **Latencia de ciclo** | 10-100ms típico | Depende de poll_seconds y red |

---
