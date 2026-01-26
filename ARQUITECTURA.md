# 🏗️ Arquitectura - Collector Python

**Versión:** 1.0  
**Fecha:** Enero 2026  
**Proyecto:** Crystal Lagoons - Collector Python  

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
- ✅ Almacena datos locales (JSONL, SQLite, PostgreSQL)
- ✅ Envía datos a un backend centralizado
- ✅ Implementa reconexión automática y recuperación ante fallos
- ✅ Funciona continuamente en modo daemon

### Tipos de Datos Soportados

| Origen | Protocolo | Clase | Estado |
|--------|-----------|-------|--------|
| Rockwell (Allen-Bradley) | Ethernet/IP | `RockwellSessionReader` | ✅ Activo |
| Siemens (S7) | OPC-UA | `SiemensSessionReader` | ✅ Activo |

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
         │  - JSONL       │     │   Sender   │
         │  - SQLite      │     │ (HTTP POST)│
         │  - PostgreSQL  │     └────────────┘
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
│ 4. ALMACENAMIENTO LOCAL (OPCIONAL)                      │
│    - JSONL Buffer (data/buffer.jsonl)                   │
│    - PostgreSQL / SQLite (si configurado)               │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 5. ENVÍO AL BACKEND (OPCIONAL)                          │
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
  - `RockwellSessionReader` (Ethernet/IP vía pycomm3)
  - `SiemensSessionReader` (OPC-UA)
- **Responsabilidades:**
  - Conexión al PLC
  - Lectura de tags individuales
  - Reconexión automática
  - Manejo de errores de conexión
- **Patrón:** Session-based reader con reintentos

### 3. **Capa de Normalización**
- **Ubicación:** `common/payload.py`
- **Clase:** `NormalizedPayload`
- **Responsabilidades:**
  - Modelo Pydantic para validación de datos
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
    lagoon_id: UUID          # Identificador único de laguna
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

**Características:**
- Protocolo: EthernetIP vía pycomm3
- Tag mapping: `{logical_name: plc_address}`
- Reconexión forzada cada N segundos
- Contador de fallos consecutivos

#### `get_siemens.py`
```python
class SiemensSessionReader:
    def __init__(
        endpoint: str,              # "opc.tcp://ip:port"
        tag_map: dict,
        timeout_sec: int = 4,
        username: str = None,
        password: str = None
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
lagoon_id: "uuid"
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

# Backend (opcional)
backend:
  url: "http://localhost:8000/ingest/scada"
```

### Archivo de Ejemplo: `lagoon_aquavista.yml`
```yaml
lagoon_id: "b723d4a9-2f2f-474b-b87f-0dfce68c18e8"
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
│ Buffer Local (JSONL)          │ ← Rápido, sin esquema
│ data/buffer.jsonl             │
└───────────────────────────────┘
    ↓ (opcional)
┌───────────────────────────────┐
│ SQLite Local                  │ ← Queryable, histórico
│ data/collector.db             │
└───────────────────────────────┘
    ↓ (opcional)
┌───────────────────────────────┐
│ PostgreSQL (remoto)           │ ← Escalable, backup
│ centralizado                  │
└───────────────────────────────┘
    ↓ (opcional)
┌───────────────────────────────┐
│ Backend HTTP                  │ ← Procesamiento remoto
│ POST /ingest/scada            │
└───────────────────────────────┘
```

### Formatos de Datos

#### JSONL
```json
{"lagoon_id":"b723d4a9-2f2f-474b-b87f-0dfce68c18e8","source":"siemens","timestamp":"2026-01-23T14:30:45.123456+00:00","tags":{"Tags_01_Real":23.5,"Tags_02_Real":18.2}}
{"lagoon_id":"b723d4a9-2f2f-474b-b87f-0dfce68c18e8","source":"siemens","timestamp":"2026-01-23T14:30:46.125000+00:00","tags":{"Tags_01_Real":23.6,"Tags_02_Real":18.1}}
```

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

#### Capa de Lectura (Workers)
```python
try:
    if not self._driver or self.should_rotate():
        self._disconnect()
        self._connect()
    result = self._driver.read(tag)
    values[tag_id] = result.value
except Exception as e:
    self._consecutive_fails += 1
    if self._consecutive_fails >= self.max_consecutive_fails:
        self._disconnect()  # Reconecta en siguiente ciclo
        self._consecutive_fails = 0
    # Continúa con siguiente tag
```

**Comportamiento:**
- Tolera fallos transitivos
- Reconecta después de N fallos consecutivos
- Fuerza reconexión cada N segundos (rotación)

#### Capa de Envío (Backend)
```python
def send(self, payload):
    try:
        r = requests.post(self.url, json=..., timeout=3.0)
        r.raise_for_status()
        return True
    except Exception as e:
        logger.warning(f"backend unreachable: {e}")
        return False  # No detiene lectura
```

**Comportamiento:**
- NO reintentos automáticos
- Logs de advertencia solamente
- Aplicación continúa funcionando

#### Capa Principal (main.py)
```python
while True:
    cycle_start = time.perf_counter()
    raw_tags = reader.read_once()
    # Si falla read_once(), lanza excepción (app termina)
    # → Recomendación: agregar try/except en main loop
```

---

## Dependencias Externas

### Librerías Principales

| Librería | Versión | Propósito | Uso |
|----------|---------|----------|-----|
| `pycomm3` | 1.2.16 | Driver Rockwell EthernetIP | `workers/get_rockwell.py` |
| `opcua` | 0.98.13 | Cliente OPC-UA (Siemens) | `workers/get_siemens.py` |
| `requests` | - | HTTP client | `common/sender.py` |
| `pydantic` | 2.12.5 | Validación de datos | `common/payload.py` |
| `PyYAML` | 6.0.3 | Parseo YAML | `main.py` |

### Librerías de Soporte
- `lxml` - Parsing XML (requerido por opcua)
- `python-dateutil` - Utilidades de fecha
- `pytz` - Soporte de zonas horarias
- `Flask`, `Werkzeug` - (no usadas actualmente)

### Conectividad de Red

**Rockwell:**
- Protocolo: EthernetIP (Puerto 44818 TCP/UDP)
- Requerimiento: Red con acceso al PLC

**Siemens:**
- Protocolo: OPC-UA (Puerto 4840 TCP por defecto)
- Requerimiento: Servidor OPC-UA activo en PLC

---

## Limitaciones y Mejoras Futuras

### Limitaciones Actuales
1. ❌ **Sin retry en backend** - Si falla envío, se pierde oportunidad
2. ❌ **Sin limpieza explícita** - No hay shutdown graceful
3. ❌ **Logging mínimo** - Principalmente print() en main
4. ❌ **Tag map estático** - No puede cambiar tags en runtime
5. ❌ **Sin monitoreo** - No hay health checks
6. ❌ **Sin compresión** - JSONL sin comprimir en storage

### Mejoras Recomendadas
1. ✅ **Agregar signal handlers** para `SIGINT`, `SIGTERM`
2. ✅ **Implementar queue** de payloads pendientes con reintentos
3. ✅ **Metricas** (Prometheus) con count de lecturas, errores
4. ✅ **Actualizacion de tag map** vía API sin reiniciar
5. ✅ **Health check endpoint** si se convierte en servicio
6. ✅ **Rotar archivo de buffer JSONL** por tamaño/fecha
7. ✅ **Compresión** de archivos JSONL antiguos

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
│ en planta            │    │ (opcional)          │
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

### Sistemas de Almacenamiento
- ✅ JSONL (archivo local)
- ✅ SQLite (local, no requiere servidor)
- ✅ PostgreSQL (remoto, requiere servidor)

---

## Resumen Ejecutivo

| Aspecto | Descripción |
|--------|-------------|
| **Tipo** | Collector de datos industrial |
| **Protoclos** | EthernetIP (Rockwell), OPC-UA (Siemens) |
| **Entrada** | Configuración YAML + Tags desde PLC |
| **Procesamiento** | Loop continuo con polling |
| **Salida** | JSONL/SQLite/PostgreSQL + HTTP Backend |
| **Escalabilidad** | Vertical (multi-threaded posible en futuro) |
| **Disponibilidad** | 24/7 con reconexión automática |
| **Recuperación** | Buffer local ante desconexiones |

---

**Fin del Documento**
