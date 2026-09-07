# Prompt: adaptar el collector existente usando este collector como referencia

Necesito que adaptes el **collector ya existente en el proyecto destino** tomando como referencia funcional el repositorio `collector_python` de Crystal Lagoons. No reemplaces el collector destino de forma ciega ni asumas que ambos tienen la misma arquitectura: primero inspecciona el código, la configuración, el contrato HTTP y los procesos de ejecución del destino; luego propone e implementa una adaptación compatible.

## Objetivo

El collector de referencia lee telemetría SCADA de varias lagunas desde PLC Rockwell, servidores OPC-UA Siemens o un simulador local; normaliza parte de los datos; detecta eventos; y envía payloads HTTP al backend. Debe seguir leyendo aunque el backend esté lento o caído, por lo que desacopla lectura y envío y conserva localmente los envíos fallidos.

La adaptación debe conservar las responsabilidades equivalentes del collector de referencia, pero respetar los nombres, protocolo, despliegue y restricciones del collector de destino cuando sean distintos.

## Comportamiento que debes replicar o mapear

### 1. Configuración de una o muchas lagunas

- El comando principal es `python main.py --config <archivo-yaml>`.
- Un YAML de laguna individual contiene al menos `lagoon_id`, `source`, `timezone` y `tags`.
- Un YAML maestro define valores globales (`backend`, `runtime`, `product_type`) y una lista `plcs`.
- Cada elemento de `plcs` puede incluir otro YAML mediante `include`. El include se resuelve relativo al YAML maestro.
- La configuración incluida puede recibir overrides de primer nivel desde su entrada de `plcs`.
- `product_type` solo admite `crystal` y `small`. La prioridad es:
  1. override de la entrada `plcs[]`;
  2. valor en el YAML de la laguna;
  3. valor global del maestro;
  4. `crystal` por defecto.
- Un archivo maestro crea un worker independiente por laguna. Una configuración individual ejecuta solo un worker.

No asumas que el collector destino utiliza YAML ni estos nombres. Si tiene otro esquema, crea un mapeo explícito y documentado, manteniendo compatibilidad con sus configuraciones existentes siempre que sea posible.

### 2. Lectura de tags

Cada laguna realiza ciclos continuos con `poll_seconds` (por defecto, 1 segundo). La programación se basa en un reloj monotónico: intenta mantener el intervalo aun cuando un ciclo tarde algo de tiempo, y se reancla si queda atrasado.

El diccionario `tags` siempre usa nombres lógicos como claves; los valores de la configuración identifican la dirección real en el PLC o nodo OPC-UA.

Fuentes soportadas por la referencia:

| Fuente | Implementación de referencia | Comportamiento relevante |
| --- | --- | --- |
| `rockwell` | `workers/get_rockwell.py` | Mantiene una sesión `pycomm3.LogixDriver`, lee todas las direcciones en batch, reconecta por antigüedad o tras varios fallos consecutivos, y devuelve `{}` ante errores de comunicación. |
| `siemens` | `workers/get_siemens.py` | Mantiene un cliente OPC-UA, obtiene todos los nodos en batch con `get_values`, y desconecta para forzar una reconexión tras un error. Soporta usuario y contraseña opcionales. |
| `siemens` con `opcua_modules` | `SiemensModulesReader` | Lee varios endpoints OPC-UA. Si un módulo falla, conserva sus claves lógicas con valor `null`, mientras combina los módulos disponibles. Puede sumar tags suplementarios fijos/simulados. |
| `simulator` | `workers/get_simulator.py` | Entrega valores fijos o valores deterministas pseudoaleatorios. Soporta `float`, `int`, `bool`, `state` y `choice`, con `seed` opcional. |

Si una lectura devuelve un diccionario vacío o lanza una excepción, el ciclo no genera un payload. Si devuelve tags, incluso si alguno es `null`, el payload sí se genera.

### 3. Normalización y eventos

- Si existe la clave lógica exacta `WM01_TOT_SCADA`, agrega `WM01_TOT_DELTA_SCADA`.
- El delta es `0` en la primera lectura; después es `actual - anterior`. Si el total disminuye, se interpreta como reset y el delta pasa a ser `actual`. Valores no numéricos, nulos o negativos producen delta `0`.
- Esta normalización es por laguna y vive en memoria; al reiniciar el proceso se pierde el valor anterior.
- Los tags declarados en `event_tags` generan eventos booleanos solo al cambiar de `false` a `true` (`OPEN`) o de `true` a `false` (`CLOSE`). La primera lectura solo inicializa el estado, no crea evento.
- Si `runtime.enable_state_events` está activo (por defecto `true`), cualquier tag de tipo `int` con valor entre `0` y `3` genera `STATE_CHANGE` cuando cambia. Los booleanos se excluyen de esta regla. La primera lectura tampoco genera evento.
- Los eventos se adjuntan al mismo payload de telemetría, no se envían a un endpoint separado.

No habilites eventos en el destino sin comprobar antes cuál es su contrato de eventos y si espera eventos en el payload de telemetría, en otro endpoint o en otro formato.

### 4. Contrato de envío HTTP de referencia

El backend se configura con `backend.url`. La referencia usa una `requests.Session` por worker sender, con un pool HTTP configurable, y hace `POST` JSON con el encabezado `X-Api-Key: <COLLECTOR_API_KEY>`.

Si no está definida la variable de entorno `COLLECTOR_API_KEY`, el envío falla deliberadamente y nunca debe enviar una clave vacía como si fuera válida.

Payload base:

```json
{
  "lagoon_id": "ava_lagoons",
  "product_type": "crystal",
  "source": "rockwell",
  "timestamp": "2026-04-17T14:32:00+00:00",
  "tags": {
    "PT117_R_SCADA": 12.34,
    "WM01_TOT_DELTA_SCADA": 0.17
  }
}
```

`timestamp` debe expresarse en UTC con offset. `timezone` de la laguna se utiliza para observabilidad y logs locales, no para cambiar el timestamp enviado.

Solo si `backend.send_events` es verdadero y hay eventos, se agrega `events`:

```json
{
  "events": [
    {
      "type": "STATE_CHANGE",
      "lagoon_id": "ava_lagoons",
      "tag_id": "P005_STS_SCADA",
      "alert_type": "STATE",
      "previous_state": 1,
      "state": 3,
      "ts": "2026-04-17T14:32:00+00:00"
    }
  ]
}
```

Antes de implementar, compara campo a campo este contrato con el backend y collector destino. No cambies el contrato del destino ni el backend por inferencia.

### 5. Aislamiento entre la lectura y el envío

Por cada laguna con backend configurado, la referencia mantiene:

1. un loop de lectura que construye payloads;
2. una cola acotada en memoria;
3. un thread sender independiente que consume esa cola y hace el HTTP `POST`.

Así, la latencia HTTP no frena la lectura del PLC. La cola se controla con estas opciones de runtime:

- `send_queue_maxsize`: tamaño máximo, mínimo efectivo de 1.
- `send_queue_full_policy`: `drop_newest`, `drop_oldest` o `block`.
- `send_retry_attempts`: reintentos adicionales tras el primer intento.
- `send_retry_backoff_base_sec` y `send_retry_backoff_max_sec`: backoff exponencial limitado.
- `startup_jitter_max_sec`: demora aleatoria inicial para evitar que todas las lagunas se conecten a la vez.

Cuando la cola está vacía, el sender intenta primero reproducir un pequeño lote de datos pendientes del disco y luego continúa con los datos nuevos.

### 6. Tolerancia a fallos: spool JSONL local

Cuando el envío agota sus reintentos o no es posible encolar un payload, y `spool_on_send_fail=true`, el payload se persiste en:

```text
data/spool/<lagoon_id_sanitizado>.jsonl
```

Características que deben conservarse en la adaptación o sustituirse por una garantía equivalente:

- El spool se separa por laguna, por lo que una laguna caída no bloquea las demás.
- Cada entrada es un JSON completo por línea (JSONL), se escribe con `flush` y `fsync`.
- Al reintentar, el archivo se rota temporalmente a `.work`; los pendientes se conservan y los nuevos que lleguen durante el replay se unen de nuevo de manera segura.
- El replay procesa como máximo `replay_spool_batch_size` payloads por pasada.
- `max_replay_payload_age_sec` permite descartar datos atrasados. Un valor menor o igual a cero no aplica límite.
- Un fallo durante replay conserva el payload fallido y no intenta los siguientes de esa tanda, preservando el orden.
- Al iniciar, migra el buffer antiguo `data/buffer.jsonl` al formato separado por laguna cuando puede inferir `lagoon_id`.

No sustituyas este mecanismo por una cola ilimitada en RAM. Si el destino ya tiene una cola duradera o base de datos, evalúa si ofrece las mismas propiedades: aislamiento por origen, recuperación después de reinicio, orden razonable y límite de crecimiento.

### 7. Operación

- `supervisor.py` inicia `main.py --config collectors.yml` y reinicia el proceso cinco segundos después de una caída.
- Las credenciales deben venir de variables de entorno o de un gestor de secretos; nunca deben quedar incluidas en YAML ni en el repositorio.
- Deben mantenerse logs útiles de inicio, ciclos de lectura, estadísticas de envío, replay, buffer y fallos de workers, sin imprimir valores secretos.

## Advertencias que debes resolver antes de portar

1. El normalizador se activa solo con el nombre lógico `WM01_TOT_SCADA`. Algunas configuraciones de referencia usan `WM01_TOT`, por lo que no obtendrán el delta sin un mapeo explícito. Decide y documenta si el destino debe aceptar ambos nombres o normalizar sus configuraciones.
2. En la referencia, los detectores construyen eventos con `alert_type`, pero el modelo `ScadaEvent` declara un campo obligatorio `event_type`. Verifica con una prueba de transición real si Pydantic rechaza esos eventos. En el destino define un único esquema consistente y pruébalo antes de habilitar eventos productivos.
3. El merge de configuraciones es superficial. `backend` y `runtime` se combinan explícitamente al consumirlos, pero otros objetos anidados no reciben deep merge automático. Conserva o mejora esto solo si queda cubierto por pruebas de compatibilidad.
4. Los paths de spool son relativos al directorio de ejecución. El destino debe usar una ruta estable y con permisos de escritura en su servicio o contenedor.

## Método de trabajo obligatorio

1. Inspecciona el collector actual de destino: entrypoint, fuentes de datos, esquema de config, concurrencia, payload que envía, autenticación, persistencia local y método de despliegue.
2. Escribe una tabla de equivalencias entre destino y referencia. Marca cada función como: ya existe, hay que adaptar, falta, o no aplica.
3. Propón un cambio mínimo y compatible. No sustituyas dependencias, nombres de endpoints ni formatos sin justificarlo.
4. Implementa por etapas: carga de configuración, lectura por fuente, payload/normalización, envío asíncrono, spool/replay, y luego eventos.
5. Agrega o actualiza pruebas automatizadas para:
   - prioridad y validación de `product_type`;
   - mapeo de nombres lógicos de tags;
   - delta inicial, incremento, reset e inválidos;
   - eventos en primera lectura y en transiciones;
   - cola llena para cada política;
   - envío fallido, reintento, spool y replay;
   - vencimiento de payloads durante replay;
   - una ejecución multi-laguna donde una fuente o backend falla sin detener las demás.
6. Entrega un resumen con archivos modificados, migraciones de configuración necesarias, variables de entorno, comandos de ejecución y riesgos abiertos.

## Criterios de aceptación

- La lectura de una laguna no queda bloqueada por el envío HTTP ni por el fallo de otra laguna.
- No se pierde telemetría por una caída transitoria del backend, salvo políticas explícitas de descarte, cola llena o edad máxima ya configuradas.
- Los payloads cumplen el contrato del backend destino y contienen timestamps UTC.
- La configuración no contiene credenciales y los secretos se leen fuera del repositorio.
- La adaptación conserva las funciones relevantes del collector destino y no rompe sus instalaciones existentes.
- Las decisiones de compatibilidad y cualquier diferencia deliberada frente a esta referencia quedan documentadas.

## Archivos de referencia

- `main.py`: orquestación, scheduling, detectores, colas y sender workers.
- `common/config.py`: carga de YAML maestro/incluido y `product_type`.
- `common/sender.py`: contrato HTTP y autenticación.
- `workers/get_rockwell.py`, `workers/get_siemens.py`, `workers/get_simulator.py`: fuentes de lectura.
- `normalizer/tot_delta_normalizer.py`: cálculo de delta de totalizador.
- `storage/jsonl_buffer.py`: spool, replay y migración del buffer legacy.
- `collectors.yml` y `config/*.yml`: ejemplos reales de configuración.
- `tests/`: pruebas existentes de configuración, spool y fuentes.
