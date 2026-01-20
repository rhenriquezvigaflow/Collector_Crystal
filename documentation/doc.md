# Documentación técnica — Crystal Lagoons

Última actualización: 2026-01-20

---

## Resumen
Crystal Lagoons es un conjunto de utilidades para recolectar datos en tiempo real desde PLCs (Rockwell via EtherNet/IP y OPC UA para Siemens) y exponerlos para visualización y almacenamiento de eventos. El objetivo principal es:
- Leer tags periódicamente.
- Medir latencias por lectura.
- Detectar eventos binarios (ej.: TRUE -> FALSE) y persistirlos.
- Exponer datos en una web ligera (Flask) y en formato JSON.

Componentes principales:
- conectpy/ROCWELL/plc_realtime_demo.py — Monitor realtime para PLCs Rockwell (pycomm3 + Flask + SQLite).
- conectpy/SIEMENS/get_opUA.py — Cliente OPC UA de ejemplo para lectura de nodos.
- events.sqlite3 — Base de datos SQLite (creada por el demo).

---

## Arquitectura resumida
- Hilos por PLC: cada PLC tiene un hilo que ejecuta `read_plc_loop(...)`.
- Flask corre en un hilo separado exponiendo:
  - `/` — UI HTML simple.
  - `/data` — JSON con estado en tiempo real.
  - `/api/events` — API para eventos.
  - `/events` — HTML con lista de eventos.
- SQLite guarda solo eventos (tabla `events`).
- Estructuras en memoria:
  - `realtime_data` — datos por PLC y tag, latencias y metadatos.
  - `open_event_ids` — eventos abiertos recuperados de DB al inicio.
  - `last_state` — último valor booleano conocido por tag de estado.

---

## Archivos clave y responsabilidad
- conectpy/ROCWELL/plc_realtime_demo.py
  - Variables de configuración: `PLCS`, `TAG_LABELS`, `READ_INTERVAL`, `DB_PATH`, etc.
  - DB helpers: `db_connect`, `db_init`, `db_get_open_events`, `db_insert_event`, `db_close_event`, `db_list_events`.
  - Utilidades: `now_ts`, `trunc_4`, `trunc_ms_4`, `to_bool`, `tag_label`.
  - Web: Flask + plantillas reducidas (`HTML_PAGE`, `EVENTS_PAGE`).
  - Loop de lectura: `read_plc_loop` (con reconexión forzada y manejo de fallos).
  - Inicio: lanza hilo web y hilos por PLC.
- conectpy/SIEMENS/get_opUA.py
  - Cliente OPC UA básico para conectar a `OPC_SERVER_URL`.
  - Lee nodos listados en `NODES` en un bucle y printa valores.
  - Ejemplo sin autenticación ni seguridad.

---

## Esquema de la base de datos
Tabla `events`:
- id INTEGER PRIMARY KEY AUTOINCREMENT
- plc_ip TEXT NOT NULL
- plc_name TEXT NOT NULL
- tag TEXT NOT NULL
- tag_label TEXT NOT NULL
- start_ts TEXT NOT NULL
- end_ts TEXT (NULL hasta cierre del evento)
- created_at TEXT NOT NULL

Índices:
- idx_events_plc_tag ON (plc_ip, tag)
- idx_events_start_ts ON (start_ts)

---

## Endpoints (Flask)
- GET / -> UI HTML interactiva (actualiza cada 1s).
- GET /data -> JSON con `realtime_data` (estructura: por IP: `_meta`, `_name`, tags).
- GET /api/events?plc=<ip>&limit=<n> -> JSON con eventos (por PLC opcional).
- GET /events?plc=<ip>&limit=<n> -> HTML con tabla de eventos.

Estructura JSON (ejemplo parcial):
{
  "<plc_ip>": {
    "_name": "Nombre PLC",
    "_meta": {
      "quality": "OK|BAD|DOWN|INIT",
      "last_cycle_ms": "12.3456",
      "last_cycle_ts": "YYYY-MM-DD HH:MM:SS",
      "last_ok_ts": "...",
      "last_error": "...",
      "consecutive_fails": 0
    },
    "TAG_NAME": {
      "valor": "12.3456 or TRUE/FALSE",
      "timestamp": "YYYY-MM-DD HH:MM:SS",
      "latencia_ms": "1.2345",
      "quality": "OK|BAD|DOWN",
      "label": "Etiqueta legible",
      "is_state": true|false
    },
    ...
  }
}

---

## Requisitos y dependencias
Sugerido en virtualenv:
- Python 3.8+
- pycomm3 (para Rockwell)
- flask
- opcua (python-opcua) para get_opUA.py
- sqlite3 (incluido en stdlib)
- Otras libs usadas: threading, time, math, logging, datetime

Instalación:
pip install -r requirements.txt
(asegurar que requirements.txt incluya pycomm3, flask, opcua)

---

## Cómo ejecutar
1. Inicializar DB y lanzar demo Rockwell:
   python conectpy/ROCWELL/plc_realtime_demo.py
   - Abre UI en http://localhost:5000

2. Ejecutar cliente OPC UA (lectura simple):
   python conectpy/SIEMENS/get_opUA.py

Nota: ajustar IPs y NodeIds en los archivos según la red y los equipos.

---

## Seguridad — estado actual
- Interfaz web no autenticada (pensada para red interna).
- Conexiones a PLCs/OPC UA sin autenticación avanzada en los ejemplos.
- Configuración hardcodeada en los scripts (IPs, NodeIds).
- SQLite sin cifrado.

Recomendaciones inmediatas:
- No exponer la UI a Internet sin protección.
- Ejecutar detrás de un reverse proxy con TLS si se necesita acceso remoto.
- Mover datos sensibles a variables de entorno o gestor de secretos.

---

## Mejoras propuestas (prioridad)
1. Autenticación para la UI/API (JWT o Basic + HTTPS).
2. Soporte de TLS y certificados en OPC UA y mecanismo de seguridad para pycomm3 si aplica.
3. Configuración por archivo YAML/JSON y variables de entorno.
4. Exportar métricas (Prometheus) y agregar alertas para fallos prolongados.
5. Circuit breaker y backoff exponencial para reconexiones a PLC.
6. Tests unitarios para parsers y DB helpers; integración para el loop de lectura (mocked).
7. Rotación/backup y posible cifrado de la base de datos.
8. UI mejorada con filtros, rango temporal y export CSV.

---

## Buenas prácticas operativas
- Mantener el script en una VLAN/segmento de control industrial.
- Supervisar el uso de CPU/memoria si se agregan muchos PLCs.
- Hacer backups periódicos de `events.sqlite3`.
- Anotar cambios en PLCS (IPs, tags) en control de versiones.

---

## Troubleshooting rápido
- Error de conexión a PLC:
  - Verificar accesibilidad IP (ping), firewall, cableado y que el PLC acepte conexiones EtherNet/IP.
- Web no responde:
  - Revisar si Flask está corriendo en el proceso; revisar logs por excepciones.
- DB locked / concurrent access:
  - SQLite usa WAL en el script; si surgen locks prolongados revisar procesos en curso o permisos del archivo.

---

## Contacto / Contribuciones
Abrir issues o PRs en el repositorio con:
- Añadidos de seguridad (auth/TLS).
- Integración de métricas.
- Soporte a otros protocolos.

---

## Licencia
Colocar la licencia de la organización / proyecto según política interna. Si no hay, usar licencia permissive (MIT) o consultar al equipo legal.

---