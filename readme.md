# Crystal Lagoons — Realtime PLC Data Collector

Resumen
-------
Crystal Lagoons es un conjunto de utilidades para leer datos en tiempo real desde PLCs, exponerlos por una interfaz web ligera y almacenar eventos binarios (TRUE/FALSE) en SQLite. Está pensado para redes de control internas y pruebas rápidas.

Contenido principal
------------------
- conectpy/ROCWELL/plc_realtime_demo.py — Monitor realtime (pycomm3 + Flask + SQLite).
  - Web UI: http://localhost:5000
  - Endpoints: `/` (UI), `/data` (JSON), `/api/events`, `/events` (HTML)
  - DB: events.sqlite3 (tabla `events`)
- conectpy/SIEMENS/get_opUA.py — Ejemplo cliente OPC UA que lee NodeIds en bucle.
- documentation.md — Documentación técnica extendida.

Requisitos
---------
- Python 3.8+
- Recomendado en virtualenv
- Dependencias (ejemplo):
  - pycomm3
  - flask
  - opcua (python-opcua)
  - sqlite3 (stdlib)
Instalar:
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Ejecución
--------
- Iniciar demo Rockwell:
```powershell
python conectpy\ROCWELL\plc_realtime_demo.py
```
- Iniciar cliente OPC UA:
```powershell
python conectpy\SIEMENS\get_opUA.py
```

Arquitectura (rápido)
---------------------
- Un hilo por PLC ejecuta `read_plc_loop(...)`.
- Flask corre en hilo separado.
- `realtime_data` mantiene estado en memoria.
- `events.sqlite3` guarda eventos abiertos/cerrados.

Seguridad — estado actual
-------------------------
- Web sin autenticación (diseñada para LAN/segmento OT).
- Scripts sin gestión de credenciales ni cifrado.
- OPC UA demo y conexiones a PLCs sin políticas TLS/usuario por defecto.
- SQLite sin cifrado.

Mejoras de seguridad y roadmap
------------------------------
- Añadir autenticación/autoridad a la API/UI (basic/JWT) y servir con TLS (reverse proxy).
- Mover configuración sensible a variables de entorno o vault.
- Usar OPC UA con certificados y validar servidor.
- Backoff/circuit-breaker en reconexiones y exportar métricas (Prometheus).
- Tests unitarios para helpers y mocks de PLC/OPC.
- Rotación/backup y (si es necesario) cifrado de la DB.

Notas operativas
----------------
- Mantener los scripts en una VLAN/segmento de control industrial.
- Hacer backups regulares de `events.sqlite3`.
- Ajustar `PLCS`, `NODES` y intervalos en los scripts según la red y la carga.

