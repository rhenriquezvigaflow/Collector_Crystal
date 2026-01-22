# Documentación Técnica - Collector Python

## 1. Descripción General

**Collector Python** es una aplicación de recopilación de datos industriales en tiempo real que conecta con controladores lógicos programables (PLCs) Rockwell y Siemens. La aplicación:

- Lee datos de tags/variables desde dispositivos PLC
- Normaliza los datos en un formato estándar
- Almacena los datos en múltiples destinos (JSONL, PostgreSQL, SQLite)
- Implementa reconexión automática y tolerancia a fallos
- Proporciona logging centralizado y monitoreo

**Stack Tecnológico:**
- Python 3.x
- YAML para configuración
- Flask (opcional)
- Almacenamiento en JSONL, PostgreSQL, SQLite

---

## 2. Estructura del Proyecto

```
collector_python/
├── main.py                          # Punto de entrada principal
├── requirements.txt                 # Dependencias del proyecto
├── run.bat                          # Script de ejecución en Windows
├── DOCUMENTACION_TECNICA.md         # Este archivo
│
├── common/                          # Módulos compartidos
│   ├── __init__.py
│   ├── logger.py                   # Sistema de logging centralizado
│   ├── payload.py                  # Estructura de datos normalizada
│   ├── time.py                     # Utilidades de tiempo
│   └── __pycache__/
│
├── config/                          # Archivos de configuración
│   ├── lagoon_aguavista.yml        # Configuración Planta Aguavista
│   └── lagoon_costadellago.yml     # Configuración Planta Costa del Lago
│
├── data/                            # Almacenamiento de datos
│   └── buffer.jsonl                # Buffer local de datos en JSONL
│
├── logs/                            # Archivos de logs
│   └── collector.log               # Log principal de la aplicación
│
├── storage/                         # Módulos de persistencia
│   ├── __init__.py
│   ├── jsonl_buffer.py             # Almacenamiento en JSONL
│   ├── pg_writer.py                # Escritor de PostgreSQL
│   ├── sqlite_buffer.py            # Almacenamiento en SQLite
│   └── __pycache__/
│
└── workers/                         # Workers especializados por fabricante
    ├── __init__.py
    ├── get_rockwell.py             # Lector de PLCs Rockwell
    ├── get_siemens.py              # Lector de PLCs Siemens
    └── __pycache__/
```

---

## 3. Módulos Principales

### 3.1 `main.py` - Orquestador Principal

**Responsabilidades:**
- Cargar configuración desde archivos YAML
- Inicializar conexiones con PLCs
- Coordinar ciclos de lectura de datos
- Manejar reconexiones automáticas

**Flujo de Ejecución:**
1. Carga configuración `load_config(config_path)`
2. Identifica el tipo de fuente (rockwell/siemens)
3. Ejecuta el worker específico (`run_rockwell()`)
4. En cada ciclo:
   - Lee tags del PLC
   - Normaliza datos a estructura estándar
   - Guarda en buffer local (JSONL)
   - Registra en logs
   - Duerme según intervalo configurado
5. Implementa reconexión automática ante fallos

**Constantes Clave:**
- `RECONNECT_DELAY = 5s` - Espera entre intentos de reconexión

**Funciones Principales:**
```python
load_config(path: str) -> dict              # Carga YAML
run_rockwell(cfg: dict)                     # Ejecuta ciclo Rockwell con reconexión
main(config_path: str)                      # Punto de entrada
```

---

### 3.2 `common/logger.py` - Sistema de Logging

**Responsabilidades:**
- Configurar logging centralizado
- Registrar eventos en archivo y consola
- Gestionar rotación y almacenamiento de logs

**Características:**
- Nivel: INFO
- Formato: `timestamp | nivel | mensaje`
- Destinos: `logs/collector.log` + consola
- Creación automática de directorio `logs/`
- Encoding UTF-8

**Uso:**
```python
from common.logger import get_logger
logger = get_logger()
logger.info("Mensaje informativo")
logger.warning("Advertencia")
```

---

### 3.3 `common/payload.py` - Estructura de Datos Normalizada

**Responsabilidades:**
- Definir estructura estándar para datos recopilados
- Normalizar datos de diferentes fuentes (Rockwell, Siemens)

**Estructura NormalizedPayload:**
```python
NormalizedPayload(
    plant_id: int,              # ID de planta
    source: str,                # Fuente (rockwell/siemens)
    timestamp: datetime,        # Marca de tiempo UTC
    tags: Dict[str, Any]       # Diccionario de tags/valores
)
```

**Métodos:**
- `model_dump_json()` - Serializa a JSON

---

### 3.4 `common/time.py` - Utilidades de Tiempo

**Responsabilidades:**
- Proporcionar marca de tiempo UTC normalizada

**Funciones:**
```python
utc_now() -> datetime           # Retorna datetime UTC actual
```

---

### 3.5 `storage/jsonl_buffer.py` - Buffer JSONL

**Responsabilidades:**
- Almacenar datos en formato JSONL (JSON Lines)
- Actuar como buffer local/caché

**Características:**
- Ubicación: `data/buffer.jsonl`
- Formato: Una línea JSON por registro
- Creación automática de directorio `data/`
- Append-only (sin sobrescritura)

**API:**
```python
append(payload_json: str)       # Añade línea al buffer
```

**Formato de Línea:**
```json
{"plant_id": 1, "source": "rockwell", "timestamp": "2026-01-22T14:30:45.123Z", "tags": {...}}
```

---

### 3.6 `storage/pg_writer.py` - Escritor PostgreSQL

**Responsabilidades:**
- Persistencia en base de datos PostgreSQL
- Gestión de conexiones y transacciones

**Nota:** Pendiente de implementación completa

---

### 3.7 `storage/sqlite_buffer.py` - Buffer SQLite

**Responsabilidades:**
- Almacenamiento local en SQLite
- Alternativa ligera a PostgreSQL

**Nota:** Pendiente de implementación completa

---

### 3.8 `workers/get_rockwell.py` - Lector Rockwell

**Responsabilidades:**
- Conectar con controladores Allen-Bradley (Rockwell)
- Leer tags/variables en tiempo real
- Manejar sesiones persistentes
- Implementar reconexión forzada

**Clase Principal: RockwellSessionReader**

**Constructor:**
```python
RockwellSessionReader(
    ip: str,                              # IP del PLC
    slot: int,                            # Slot del procesador (por defecto 0)
    tag_map: Dict[str, str],             # Mapeo de nombres a tags
    force_reconnect_every_sec: int,       # Forzar reconexión cada N segundos
    max_consecutive_fails: int            # Fallos consecutivos permitidos
)
```

**Métodos Clave:**
```python
connect()                       # Establece conexión con el PLC
read_once() -> Dict            # Lee todos los tags una sola vez
should_rotate() -> bool        # Verifica si debe reconectarse
close()                         # Cierra la conexión
```

**Características:**
- Sesión persistente (no reconecta en cada lectura)
- Lectura batch de múltiples tags
- Contador de fallos consecutivos
- Rotación forzada periódica

---

### 3.9 `workers/get_siemens.py` - Lector Siemens

**Responsabilidades:**
- Conectar con controladores Siemens (S7)
- Leer variables en tiempo real

**Nota:** Pendiente de implementación (similar a Rockwell)

---

## 4. Archivos de Configuración

### Estructura General

Los archivos YAML en `config/` definen la configuración de cada planta.

**Parámetros Esenciales:**

```yaml
plant_id: 1                              # ID único de la planta
source: "rockwell"                       # Fuente de datos
poll_seconds: 1.0                        # Intervalo de lectura (segundos)
force_reconnect_every_sec: 3600          # Reconexión cada N segundos
max_consecutive_fails: 10                # Máximo de fallos antes de reconectar

rockwell:                                # Configuración específica Rockwell
  ip: "192.168.1.100"                   # IP del PLC
  slot: 0                                # Slot del procesador

siemens:                                 # Configuración específica Siemens
  ip: "192.168.1.200"                   # IP del PLC
  rack: 0                                # Rack del PLC
  slot: 1                                # Slot del PLC

tags:                                    # Mapeo de tags a leer
  tag_temperature: "TemperatureSensor"
  tag_pressure: "PressureSensor"
  tag_flow: "FlowMeter"
  # ...
```

### Ejemplos de Archivos

**`lagoon_aguavista.yml`** - Configuración para Planta Aguavista
**`lagoon_costadellago.yml`** - Configuración para Planta Costa del Lago

---

## 5. Flujo de Ejecución

### Ciclo Principal (Run Loop)

```
┌─────────────────────────────────────────┐
│ 1. Cargar Configuración                 │
│    main.py -> load_config()             │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ 2. Conectar a PLC                       │
│    RockwellSessionReader.connect()      │
└──────────────┬──────────────────────────┘
               │
               ▼
        ┌──────────────────┐
        │ 3. Loop Principal │
        └────────┬─────────┘
                 │
     ┌───────────┴───────────┐
     │                       │
     ▼                       ▼
┌──────────────┐      ┌─────────────┐
│ 3.1 Leer    │      │ 3.2 Verificar
│ Tags PLC    │      │ Rotación    │
└──────┬───────┘      └────────┬────┘
       │                       │
       │               ¿Rotar?
       │                 Sí/No
       │              │      │
       ▼              │      ▼
┌──────────────┐      │   ┌───────────┐
│ 3.3 Normalizar     │   │ Continuar  │
│ Datos (Payload)    │   └─────┬──────┘
└──────┬───────┐      │         │
       │ Falla └──────┴─Reconectar
       │              │
       ▼              ▼
┌──────────────┐   ┌──────────────┐
│ 3.4 Guardar │   │ Close &      │
│ en Buffer   │   │ Reintentar   │
│ JSONL       │   └──────────────┘
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ 3.5 Registrar
│ en Logs      │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ 3.6 Dormir   │
│ poll_seconds │
└────────┬─────┘
         │
         └─────→ (Volver a 3.1)
```

### Ciclo de Reconexión

```
Fallo en lectura
       │
       ▼
┌──────────────────────┐
│ Log: RECONNECT       │
│ Intentar close()     │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Sleep: RECONNECT_    │
│ DELAY (5 segundos)   │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Reintentar conexión  │
│ connect()            │
└──────┬───────────────┘
       │
       ├─ Éxito → Volver a loop
       │
       └─ Fallo → Reintentar (exponencial)
```

---

## 6. Manejo de Errores y Excepciones

### Estrategias Implementadas

1. **Reconexión Automática**
   - Ante cualquier excepción, intenta cerrar sesión
   - Espera `RECONNECT_DELAY` segundos
   - Reinicia desde el paso de conexión

2. **Contador de Fallos**
   - `RockwellSessionReader` cuenta fallos consecutivos
   - Si excede `max_consecutive_fails`, fuerza reconexión

3. **Rotación Forzada**
   - Se reconecta cada `force_reconnect_every_sec` segundos
   - Previene bloqueos de sesión

### Tipos de Fallos Manejados

```python
Exception                           # Cualquier error desconocido
Exception("FORCE_RECONNECT")       # Rotación forzada
ConnectionError                     # Problemas de conexión
TimeoutError                        # Timeout de lectura
```

---

## 7. Inicialización y Ejecución

### Requisitos Previos

1. **Dependencias Python:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Archivos de Configuración:**
   - Configurar planta en `config/lagoon_*.yml`
   - Especificar IP, slot y tags del PLC

3. **Directorios:**
   - `logs/` - Se crea automáticamente
   - `data/` - Se crea automáticamente

### Ejecución

**Opción 1: Script Batch (Windows)**
```bash
run.bat
```

**Opción 2: Línea de comandos**
```bash
python main.py config/lagoon_aguavista.yml
```

**Opción 3: Programación**
```python
from main import main
main("config/lagoon_aguavista.yml")
```

---

## 8. Formato de Datos

### Estructura JSONL

**Archivo:** `data/buffer.jsonl`

**Formato por línea:**
```json
{
  "plant_id": 1,
  "source": "rockwell",
  "timestamp": "2026-01-22T14:30:45.123456Z",
  "tags": {
    "tag_temperature": 25.5,
    "tag_pressure": 101.325,
    "tag_flow": 1250.75,
    "tag_status": true
  }
}
```

### Logs

**Archivo:** `logs/collector.log`

**Formato:**
```
2026-01-22 14:30:45,123 | INFO | START plant=1 source=rockwell plc=192.168.1.100/0 poll=1.0s tags=4
2026-01-22 14:30:45,234 | INFO | CONNECTED plc=192.168.1.100/0
2026-01-22 14:30:45,456 | INFO | OK plant=1 ts=2026-01-22T14:30:45.345Z tags=4 sample=[...] cycle=123.4ms
2026-01-22 14:30:46,789 | WARNING | RECONNECT plant=1 plc=192.168.1.100/0 reason=Connection timeout sleep=5s
```

---

## 9. Configuración Avanzada

### Parámetros de Tuning

| Parámetro | Rango | Defecto | Descripción |
|-----------|-------|---------|-------------|
| `poll_seconds` | 0.1 - 60 | 1.0 | Intervalo entre lecturas |
| `force_reconnect_every_sec` | 300 - 86400 | 3600 | Segundos antes de reconectar |
| `max_consecutive_fails` | 1 - 100 | 10 | Fallos antes de reconectar |
| `slot` | 0 - 16 | 0 | Slot del procesador (Rockwell) |

### Optimización de Rendimiento

1. **Reducir `poll_seconds`** para mayor frecuencia de lecturas
   - Costo: Mayor consumo de CPU y red
   - Beneficio: Menor latencia de datos

2. **Aumentar `force_reconnect_every_sec`** para sesiones más largas
   - Costo: Mayor riesgo de bloqueo
   - Beneficio: Menos reconexiones

3. **Ajustar `max_consecutive_fails`** según estabilidad de red
   - Redes estables: valores altos (20-50)
   - Redes inestables: valores bajos (3-5)

---

## 10. Monitoreo y Mantenimiento

### Indicadores Clave

**En logs verificar:**
- `CONNECTED` - Conexión exitosa
- `OK` - Lectura exitosa
- `RECONNECT` - Evento de reconexión
- `WARNING` - Advertencias
- `cycle=XXXms` - Tiempo de ciclo

### Archivos a Monitorear

1. **`logs/collector.log`**
   - Revisar cada hora en producción
   - Detectar patrones de reconexiones

2. **`data/buffer.jsonl`**
   - Tamaño del archivo
   - Última línea con timestamp

3. **Memoria y CPU**
   - Proceso debe usar < 100MB RAM
   - CPU < 5% en promedio

### Mantenimiento Periódico

```bash
# Limpiar logs antiguos (más de 30 días)
del logs\collector.log

# Rotación manual del buffer
move data\buffer.jsonl data\buffer_backup_YYYYMMDD.jsonl
```

---

## 11. Extensión y Desarrollo

### Agregar Nuevo Worker (Ej: MQTT)

1. Crear `workers/get_mqtt.py`:
```python
class MQTTReader:
    def __init__(self, broker_ip, topic_prefix):
        self.broker_ip = broker_ip
        self.topic_prefix = topic_prefix
    
    def connect(self):
        # Implementar conexión MQTT
        pass
    
    def read_once(self) -> dict:
        # Implementar lectura
        pass
```

2. Actualizar `main.py`:
```python
elif source == "mqtt":
    run_mqtt(cfg)
```

### Agregar Nuevo Storage (Ej: InfluxDB)

1. Crear `storage/influxdb_writer.py`:
```python
def write_batch(payloads: List[NormalizedPayload]):
    # Implementar escritura a InfluxDB
    pass
```

2. Integrar en main loop:
```python
# Después de append a JSONL
influxdb_writer.write_batch([payload])
```

---

## 12. Troubleshooting

### Problema: "Connection refused"
**Causa:** PLC no disponible o IP incorrecta
**Solución:** 
- Verificar IP en configuración
- Ping al PLC: `ping 192.168.1.100`
- Verificar firewall

### Problema: "No tags read"
**Causa:** Tags no existen o mal mapeados
**Solución:**
- Revisar nombres en `tag_map`
- Validar en software del PLC

### Problema: "Reconexiones frecuentes"
**Causa:** Red inestable o timeout muy corto
**Solución:**
- Aumentar `force_reconnect_every_sec`
- Aumentar `max_consecutive_fails`
- Verificar latencia de red: `ping -t 192.168.1.100`

### Problema: "Archivo buffer crece demasiado"
**Causa:** No hay lectura/procesamiento
**Solución:**
- Implementar lectura periódica
- Purgar datos antiguos
- Implementar escritura a base de datos

---

## 13. Seguridad

### Recomendaciones

1. **Credenciales:**
   - No guardar contraseñas en YAML
   - Usar variables de entorno para credenciales sensibles

2. **Red:**
   - Usar VPN/VLAN para comunicación con PLCs
   - Firewall: permitir solo IPs autorizadas

3. **Acceso:**
   - Restringir permisos de archivos de configuración
   - Ejecutar con privilegios mínimos

4. **Datos:**
   - Encriptar buffer.jsonl en producción
   - Realizar backups periódicos

---


## 15. Glosario de Términos

| Término | Definición |
|---------|-----------|
| **PLC** | Controlador Lógico Programable (Programmable Logic Controller) |
| **Tag** | Variable/registro en un PLC |
| **Slot** | Posición física del procesador en un chassis Rockwell |
| **JSONL** | Formato JSON Lines (un JSON por línea) |
| **Poll** | Lectura o sondeo periódico |
| **Payload** | Estructura de datos con información recopilada |
| **Session** | Conexión persistente con un dispositivo |
| **Buffer** | Almacenamiento temporal de datos |

---

