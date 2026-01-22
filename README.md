# 🏭 Collector Python

Sistema de recopilación de datos industriales en tiempo real desde controladores PLC (Rockwell y Siemens) con almacenamiento local y reconexión automática.

## 📋 Características

✅ Lectura en tiempo real de tags/variables desde PLCs  
✅ Soporte para Rockwell (Allen-Bradley) y Siemens (S7)  
✅ Almacenamiento en múltiples formatos (JSONL, PostgreSQL, SQLite)  
✅ Reconexión automática ante fallos  
✅ Logging centralizado con rotación  
✅ Configuración flexible por YAML  
✅ Tolerancia a fallos y recuperación  

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

Editar el archivo de configuración para tu planta:

**`config/lagoon_aguavista.yml`** (ejemplo):
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
  tag_temperature: "TemperatureSensor"
  tag_pressure: "PressureSensor"
  tag_flow: "FlowMeter"
```

### 4. Ejecutar

**Windows (Script Batch):**
```bash
run.bat
```

**Línea de Comandos:**
```bash
python main.py config/lagoon_aguavista.yml
```

**Python (Programáticamente):**
```python
from main import main
main("config/lagoon_aguavista.yml")
```

## 📁 Estructura

```
collector_python/
├── main.py                      # Punto de entrada
├── requirements.txt             # Dependencias
├── run.bat                      # Script Windows
├── README.md                    # Este archivo
├── DOCUMENTACION_TECNICA.md    # Documentación detallada
├── common/                      # Módulos compartidos
├── config/                      # Configuraciones
├── workers/                     # Lectores (Rockwell, Siemens)
├── storage/                     # Almacenamiento
├── data/                        # Datos (buffer.jsonl)
└── logs/                        # Logs de la aplicación
```

## ⚙️ Configuración

### Parámetros Principales

| Parámetro | Descripción | Ejemplo |
|-----------|-------------|---------|
| `plant_id` | ID único de la planta | `1` |
| `source` | Tipo de PLC | `rockwell` o `siemens` |
| `poll_seconds` | Intervalo de lectura | `1.0` |
| `force_reconnect_every_sec` | Reconexión cada N segundos | `3600` |
| `max_consecutive_fails` | Fallos antes de reconectar | `10` |
| `rockwell.ip` | IP del PLC | `192.168.1.100` |
| `rockwell.slot` | Slot del procesador | `0` |

### Configurar Tags

Agregar tags en la sección `tags`:

```yaml
tags:
  temperatura: "Temperature_PLC"
  presion: "Pressure_PLC"
  velocidad: "Speed_Motor"
  estado: "System_Status"
```

## 📊 Salida de Datos

### Buffer Local (JSONL)
**Archivo:** `data/buffer.jsonl`

```json
{"plant_id": 1, "source": "rockwell", "timestamp": "2026-01-22T14:30:45Z", "tags": {"temperatura": 25.5, "presion": 101.3}}
{"plant_id": 1, "source": "rockwell", "timestamp": "2026-01-22T14:30:46Z", "tags": {"temperatura": 25.6, "presion": 101.4}}
```

### Logs
**Archivo:** `logs/collector.log`

```
2026-01-22 14:30:45,123 | INFO | START plant=1 source=rockwell plc=192.168.1.100/0 poll=1.0s tags=4
2026-01-22 14:30:45,234 | INFO | CONNECTED plc=192.168.1.100/0
2026-01-22 14:30:45,456 | INFO | OK plant=1 ts=2026-01-22T14:30:45Z tags=4 cycle=123.4ms
```

## 🔧 Solución de Problemas

### ❌ "Connection refused"
**Solución:**
- Verificar IP del PLC en configuración
- Ejecutar: `ping 192.168.1.100`
- Verificar firewall del equipo

### ❌ "No tags read"
**Solución:**
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

Consulta: [DOCUMENTACION_TECNICA.md](DOCUMENTACION_TECNICA.md)

## 🐛 Reportar Problemas

Si encuentras errores o tienes sugerencias:
1. Revisar `logs/collector.log`
2. Consultar [DOCUMENTACION_TECNICA.md](DOCUMENTACION_TECNICA.md) sección Troubleshooting
3. Verificar configuración en `config/*.yml`

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

## 📞 Soporte

- Documentación técnica: [DOCUMENTACION_TECNICA.md](DOCUMENTACION_TECNICA.md)
- Logs detallados: `logs/collector.log`
- Datos recopilados: `data/buffer.jsonl`

---

**Versión:** 1.0  
**Fecha:** 22 de Enero de 2026  
**Estado:** Producción

