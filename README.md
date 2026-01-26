# 🏭 Collector Python

Sistema de recopilación de datos industriales en tiempo real desde controladores PLC (Rockwell y Siemens) con almacenamiento local y reconexión automática.

**Proyecto:** Crystal Lagoons | **Versión:** 1.0 | **Estado:** Producción ✅

## 📋 Características

✅ Lectura en tiempo real de tags/variables desde PLCs  
✅ Soporte para **Rockwell** (EthernetIP) y **Siemens** (OPC-UA)  
✅ Almacenamiento en múltiples formatos (JSONL, PostgreSQL, SQLite)  
✅ Reconexión automática y rotación forzada de conexión  
✅ Logging centralizado con archivo + consola  
✅ Configuración flexible basada en YAML  
✅ Tolerancia a fallos y recuperación ante desconexiones  
✅ Envío opcional a backend centralizado (HTTP POST)  

## 🚀 Inicio Rápido

### 1. Requisitos Previos

- Python 3.8 o superior
- pip (gestor de paquetes)
- Acceso a red con los PLCs

### 2. Instalación

```bash
# Clonar o descargar el proyecto
cd collector_python

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configuración

Editar el archivo de configuración para tu laguna/planta:

**`config/lagoon_costadellago.yml`** (ejemplo - Siemens):
```yaml
lagoon_id: "b723d4a9-2f2f-474b-b87f-0dfce68c18e8"
source: "siemens"
poll_seconds: 1.0

force_reconnect_every_sec: 3600
max_consecutive_fails: 10

backend:
  url: "http://localhost:8000/ingest/scada"

siemens:
  opc_server_url: "opc.tcp://192.168.17.10:4840"
  timeout_sec: 4

tags:
  tag_temperature: "ns=4;i=3"
  tag_pressure: "ns=4;i=4"
  tag_flow: "ns=4;i=5"
```

### 4. Ejecutar

**Windows (Script Batch):**
```bash (Rockwell):**
```bash
python main.py --config config/lagoon_aquavista.yml
```

**Línea de Comandos (Siemens):**
```bash
python main.py --config config/lagoon_costadellago.yml
**Python (Programáticamente):**
```python
from main import main
main("config/lag del Proyecto

```
collector_python/
├── main.py                      # Punto de entrada (CLI)
├── requirements.txt             # Dependencias Python
├── run.bat                      # Script para Windows
├── README.md                    # Este archivo (guía rápida)
├── ARQUITECTURA.md              # Documentación de arquitectura
├── DOCUMENTACION_TECNICA.md     # Documentación técnica detallada
│
├── common/                      # Módulos compartidos
│   ├── __init__.py
│   ├── payload.py               # Estructura NormalizedPayload
│   ├── sender.py                # BackendSender (HTTP)
│   ├── logger.py                # Sistema de logging
│   └── time.py                  # Utilidades de tiempo (UTC)
│
├── config/                      # Archivos de configuración YAML
│   ├── lagoon_aquavista.yml     # Config Rockwell (ejemplo)
│   └── lagoon_costadellago.yml  # Config Siemens (ejemplo)
│
├── workers/                     # Lectores de datos (Workers)
│   ├── __init__.py
│   ├── get_rockwell.py          # RockwellSessionReader
│   └── get_siemens.py           # Si Requerido |
|-----------|-------------|---------|-----------|
| `lagoon_id` | UUID único de la laguna | `"b723d4a9-..."` | ✅ |
| `source` | Tipo de PLC | `"rockwell"` \| `"siemens"` | ✅ |
| `poll_seconds` | Intervalo entre lecturas (segundos) | `1.0` | ✅ |
| `force_reconnect_every_sec` | Rotar conexión cada N seg | `3600` | ❌ |
| `max_consecutive_fails` | Fallos antes de reconectar | `10` | ❌ |
| `backend.url` | Endpoint HTTP para envío | `"http://localhost:8000/ingest/scada"` | ❌ |

### Para Rockwell (EthernetIP)

```yaml
rockwell:
  ip: "192.168.1.100"          # IP del PLC
  slot: 0                        # Slot del procesador (típicamente 0)
```

### Para Siemens (OPC-UA)

```yaml
siemens:
  opc_server_url: "opc.tcp://192.168.17.10:4840"
  timeout_sec: 4
  username: null                 # Opcional: credenciales
  password: null                 # Opcional
```

##lagoon_id":"b723d4a9-2f2f-474b-b87f-0dfce68c18e8","source":"siemens","timestamp":"2026-01-26T14:30:45.123456+00:00","tags":{"Tags_01_Real":23.5,"Tags_02_Real":18.2}}
{"lagoon_id":"b723d4a9-2f2f-474b-b87f-0dfce68c18e8","source":"siemens","timestamp":"2026-01-26T14:30:46.125000+00:00","tags":{"Tags_01_Real":23.6,"Tags_02_Real":18.1}}
```

**Características:**
- Una línea por evento (formato JSONL)
- Timestamp en UTC con microsegundos
- Tags con valores de lectura
- Preserva histórico completo

### Logs de Consola y Archivo
**Archivo:** `logs/collector.log`

```
2026-01-26 14:30:44,001 | INFO | START siemens lagoon=b723d4a9-...
2026-0Error: "connection refused" o "timeout"

**Causas posibles:**
- IP del PLC incorrecta
- Firewall bloqueando conexión
- Puerto cerrado en PLC
- Servicio OPC-UA no activo (Siemens)

**Soluciones:**
```bash
# Verificar conectividad
ping 192.168.17.10

# Para Rockwell: verificar puerto 2944 
# Para Siemens: verificar puerto 4840 

# Revisar configuración
cat config/lagoon_costadellago.yml
```

### ❌ Error: "No tags read" o valores NULL

**Causas posibles:**
- Direcciones de tags incorrectas
- Tags no existen en el PLC
- Formato de dirección incorrecto

**Soluciones:**
```yaml
# Verificar formato correcto
# Rockwell: nombre_tag directo
tags:
  temperatura: "TemperatureSensor"

# Siemens: namespace y node ID
tags:
  temperature: "ns=4;i=3"
```

### ❌ Reconexiones muy frecuentes

**Causas:**
- Fallos de red transitivos
- `max_consecutive_fails` muy bajo
- Problema de estabilidad del PLC

**Soluciones:**
```yaml Completa

### Ejemplo 1: Rockwell (Allen-Bradley)

**`config/lagoon_aquavista.yml`:**
```yaml
lagoon_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
source: "rockwell"
poll_seconds: 1.0

force_reconnect_every_sec: 3600
max_consecutive_fails: 10

backend:
  url: "http://backend-server:8000/ingest/scada"

rockwell:
  ip: "192.168.1.100"
  slot: 0

tags:
  temperature: "TemperatureSensor"
  pressure: "PressureSensor"
  flow: "FlowMeter"
  status: "SystemStatus"
```

**Ejecutar:**
```bash
python main.py --config config/lagoon_aquavista.yml
```

### Ejemplo 2: Siemens 

**`config/lagoon_costadellago.yml`:**
```yaml
lagoon_id: "b723d4a9-2f2f-474b-b87f-0dfce68c18e8"
source: "siemens"
poll_seconds: 1.0

force_reconnect_every_sec: 3600
max_consecutive_fail en Windows

```powershell
# Ver últimas 20 líneas del log
Get-Content logs\collector.log -Tail 20

# Monitoreo en tiempo real
Get-Content logs\collector.log -Tail 20 -Wait

# Contar registros en buffer
@(Get-Content data\buffer.jsonl).Count

# Ver último registro (el más reciente)
(Get-Content data\buffer.jsonl -Tail 1) | ConvertFrom-Json | Format-Table
```

### Verificar Estado en Linux/macOS

```bash
# Ver últimas 20 líneas del log
tail -20 logs/collector.log

# Monitoreo en tiempo real
tail -f logs/collector.log

# Contar registros en buffer
wc -l data/buffer.jsonl

# Ver último registro
tail -1 data/buffer.jsonl | jq .
```

### Métricas Útiles

```bash
# Cantidad de tags capturados por ciclo (verificar logs)
grep "OK " logs/collector.log | grep -o "tags=[0-9]*"

# Tiempo promedio de ciclo
grep "OK " logs/collector.log | grep -o "cycle=[0-9.]*ms"

# De**Credenciales:** Usar variables de entorno en lugar de hardcodear
- ✅ **Permisos:** Restringir acceso a `config/*.yml` (contienen IPs y config sensible)
- ✅ **Red:** Firewall - permitir solo IPs autorizadas de PLCs
- ✅ **Datos:** Backups periódicos de `data/` y `logs/`
- ✅ **Logs:** Revisar periódicamente para detectar intentos de acceso anómalos
- ✅ **Rotación:** Implementar rotación de archivos de log para evitar llenar disco



4. ✅ Checklist de Instalación

- [ ] **Python:** Verificar Python 3.8+ → `python --version`
- [ ] **Dependencias:** `pip install -r requirements.txt`
- [ ] **Archivo de config:** Editar `config/lagoon_*.yml` con datos reales
- [ ] **Conectividad:** `ping 192.168.X.X` (IP del PLC)
- [ ] **Directorios:** Crear `data/` y `logs/` (se crean automáticamente)
- [ ] **Permisos:** Permisos de lectura en `config/` y escritura en `data/`, `logs/`
- [ ] **Puertos:** Verificar firewall
  - Rockwell: Puerto **2944** (EthernetIP)
  - Siemens: Puert Comunes

### 1. Monitoreo en Tiempo Real 
```bash
python main.py --config config/lagoon_aquavista.yml
# Verá logs en consola y archivo logs/collector.log

```

### 2. Lectura Siemens con Envío a Backend
```bash
python main.py --config config/lagoon_costadellago.yml
# Lee datos del OPC-UA Siemens
# Los envía a backend HTTP (si está configurado)
# También almacena en data/buffer.jsonl como respaldo
```

### 3. Recuperación Automática ante Fallos
```bash
# El sistema:
# - Reconecta automáticamente si el PLC se desconecta
# - Fuerza reconexión cada N segundos (configurable)
# - Tolera fallos consecutivos antes de reconectar
# - Sin intervención manual necesaria
```


### 4. Despliegue Múltiple (Multi-Laguna)
```bash
# Terminal 1: Laguna Aquavista (Rockwell)
python main.py --config config/lagoon_aquavista.yml

# Terminal 2: Laguna Costa del Lago (Siemens)
python main.py --config config/lagoon_costadellago.yml

# Cada instancia opera independientemente
```

### Componentes Clave
- **Rockwell:** EthernetIP vía `pycomm3`
- **Siemens:** OPC-UA vía `opcua`
- **Almacenamiento:** JSONL + SQLite + PostgreSQL
- **Integración:** HTTP POST al backend
- Revisar nombres de tags en `config/*.yml`
- Validar que existan en el software del PLC

### ❌ "Reconexiones frecuentes"
**Solución:**
- Aumentar `force_reconnect_every_sec`
- Aumentar `max_consecutive_fails`
- Verificar estabilidad de red

### ❌ "ModuleNotFoundError"
**Solución:**
```bash
pip install -r requirements.txt
```

## 📝 Ejemplos de Configuración

### Rockwell (Allen-Bradley)

```yaml
plant_id: 1
source: "rockwell"
poll_seconds: 1.0
force_reconnect_every_sec: 3600
max_consecutive_fails: 10

rockwell:
  ip: "192.168.1.100"
  slot: 0

tags:
  temperatura: "TemperatureSensor"
  presion: "PressureSensor"
```

### Siemens (S7)

```yaml
plant_id: 2
source: "siemens"
poll_seconds: 2.0
force_reconnect_every_sec: 1800
max_consecutive_fails: 5

siemens:
  ip: "192.168.1.200"
  rack: 0
  slot: 1

tags:
  temperatura: "DB1.DBD0"
  contador: "DB1.DBD4"
```

## 📊 Monitoreo

### Verificar Estado

```bash
# Ver últimas líneas del log
type logs\collector.log | tail -20

# Contar líneas en buffer
wc -l data\buffer.jsonl

# Ver última entrada
tail -1 data\buffer.jsonl
```

## 🔒 Seguridad

- ✅ Usar variables de entorno para credenciales
- ✅ Restringir permisos de archivos YAML
- ✅ Firewall: permitir solo IPs autorizadas
- ✅ Backups periódicos de `data/` y `logs/`

## 📚 Documentación Completa

Para información detallada sobre:
- Arquitectura del sistema
- Módulos y APIs
- Flujos de ejecución
- Extensión y desarrollo
- Configuración avanzada


## 📋 Checklist de Instalación

- [ ] Python 3.8+ instalado
- [ ] Dependencias instaladas: `pip install -r requirements.txt`
- [ ] Archivo de configuración editado: `config/lagoon_*.yml`
- [ ] IP del PLC validada: `ping [IP]`
- [ ] Directorios creados: `data/`, `logs/`
- [ ] Permisos de lectura en `config/*.yml`
- [ ] Puerto de acceso al PLC abierto (predeterminado 2944 para Rockwell)

## 🎯 Casos de Uso

### 1. Monitoreo en Tiempo Real
```bash
python main.py config/lagoon_aguavista.yml
# Verá logs en consola y archivo
```

### 2. Lectura con Reintentos Automáticos
El sistema reinicia automáticamente ante fallos sin intervención manual.

### 3. Integración con Otras Herramientas
Los datos en `data/buffer.jsonl` pueden ser procesados por otros scripts.


