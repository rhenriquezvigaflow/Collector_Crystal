#PLC ROCKWELL
# Aquaterra_2046 -> 192.168.12.10 ok 
# AVA Lagoons_3051 -> 192.168.16.10 ok
# Central District_3054 -> 192.168.20.10 ok 
# Laguna Baia Kristal_2056 -> 192.168.14.10 ok
# Laguna Costa del Lago_ 3015 -> 192.168.11.10
# Laguna Karibao_2037 -> 192.168.8.10
# Laguna Santa Rosalia_ 2043 -> 192.168.6.10

from pycomm3 import LogixDriver
from datetime import datetime
import threading
import time

# --- Consulta los Tags disponibles en el PLC -----

with LogixDriver("192.168.6.10") as plc:
    print("Tags disponibles en el PLC:")
    for tag in plc.get_tag_list():
        print(tag["tag_name"])

# from pycomm3 import LogixDriver  # Driver para Rockwell (EtherNet/IP)
# import time
# from datetime import datetime

# --- CONFIGURACIÓN ---
# PLC_IP = "192.168.11.10"  # cambia por la IP del PLC que desees probar

# tags = [
#     "AUTO_MODE", "PT117_R", "PT119_R", "PT114_R", "FIT002_R",
#     "VE238_ST", "VE239_ST", "VE244_ST", "VE401_ST", "VE402_ST",
#     "VE240_ST", "VE237_ST", "P005_ST", "P006_ST", "P009_ST",
#     "P007_ST", "P008_ST", "GLOBAL_ES", "SYSTEM_ENABLING",
#     "GLOBAL_MAN", "GLOBAL_AUTO", "FIL_ST",
#     "ALARM_X0_1", "ALARM_X1_1", "ALARM_X2_1", "ALARM_X3_1",
#     "ALARM_X4_1", "ALARM_X5_1", "ALARM_X6_1", "ALARM_X7_1",
#     "ALARM_X8_1", "ALARM_X9_1", "ALARM_X0_2", "ALARM_X1_2",
#     "ALARM_X2_2", "ALARM_X3_2", "ALARM_X4_2", "ALARM_X5_2",
#     "ALARM_X6_2", "ALARM_X7_2", "ALARM_X8_2", "ALARM_X9_2",
#     "ALARM_X0_3", "ALARM_X1_3", "ALARM_X2_3", "ALARM_X3_3",
#     "ALARM_X4_3", "ALARM_X5_3", "WM01_TOT"
# ]

# print(f"Iniciando conexión con PLC {PLC_IP}")

# # --- BUCLE PRINCIPAL ---
# def leer_tag(tag):
#     while True:
#         try:
#             with LogixDriver(PLC_IP) as plc:
#                 print(f"Hilo iniciado para {tag}")
#                 while True:
#                     t0 = time.time()
#                     result = plc.read(tag)
#                     t1 = time.time()

#                     valor = result.value if hasattr(result, "value") else result
#                     latencia_ms = (t1 - t0) * 1000
#                     timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

#                     print(f"{timestamp} | {tag:<20} | Valor: {valor:<10} | Latencia: {latencia_ms:>7.2f} ms")

#                     time.sleep(1)  # espera exacta de 1 s por tag
#         except Exception as e:
#             print(f"Error en {tag}: {e} — Reintentando en 5 s")
#             time.sleep(5)

# # crear y lanzar un hilo por cada tag
# for tag in tags:
#     thread = threading.Thread(target=leer_tag, args=(tag,), daemon=True)
#     thread.start()

# # mantener el programa vivo
# while True:
#     time.sleep(1)









# PLC_IP = "192.168.20.10"   # cambia por tu IP real del PLC
# tags = [

# "AUTO_MODE",
# "PT117_R",
# "PT119_R",
# "PT114_R",
# "FIT002_R",
# "VE238_ST",
# "VE239_ST",
# "VE244_ST",
# "VE401_ST",
# "VE402_ST",
# "VE240_ST",
# "VE237_ST",
# "P005_ST",
# "P006_ST",
# "P009_ST",
# "P007_ST",
# "P008_ST",
# "GLOBAL_ES",
# "SYSTEM_ENABLING",
# "GLOBAL_MAN",
# "GLOBAL_AUTO",
# "FIL_ST",
# "ALARM_X0_1",
# "ALARM_X1_1",
# "ALARM_X2_1",
# "ALARM_X3_1",
# "ALARM_X4_1",
# "ALARM_X5_1",
# "ALARM_X6_1",
# "ALARM_X7_1",
# "ALARM_X8_1",
# "ALARM_X9_1",
# "ALARM_X0_2",
# "ALARM_X1_2",
# "ALARM_X2_2",
# "ALARM_X3_2",
# "ALARM_X4_2",
# "ALARM_X5_2",
# "ALARM_X6_2",
# "ALARM_X7_2",
# "ALARM_X8_2",
# "ALARM_X9_2",
# "ALARM_X0_3",
# "ALARM_X1_3",
# "ALARM_X2_3",
# "ALARM_X3_3",
# "ALARM_X4_3",
# "ALARM_X5_3",
# "WM01_TOT"


# ]

# print("Iniciando conexión con PLC")

# while True:
#     try:
#         # Abrir conexión (se mantiene viva mientras no haya error)
#         with LogixDriver(f"{PLC_IP}") as plc:
#             print("Conectado al PLC")

#             while True:
#                 for tag in tags:
#                     try:
#                         result = plc.read(tag)
#                         # algunos tags devuelven objeto con .value, otros devuelven valor directo
#                         valor = result.value if hasattr(result, "value") else result
#                         print(f"{tag:<25} | Valor: {valor}")
#                     except Exception as e:
#                         print(f" Error leyendo {tag}: {e}")
#                 print("-" * 50)
#                 time.sleep(1)

#     except Exception as e:
#         print(f"Conexión perdida o error general: {e}")
#         print("Reintentando conexión en 5 segundos...")
#         time.sleep(5)






# from pycomm3 import LogixDriver

# PLC_IP = "192.168.16.10"

# tags = ["PT121_R"]


# while True:
#     try:
#         #Abrir conexión (se mantiene viva mientras no haya error)
#         with LogixDriver(f"{PLC_IP}") as plc:
#             print("Conectado al PLC — lectura cada 1 segundo\n")

#             while True:
#                 for tag in tags:
#                     try:
#                         result = plc.read(tag)
#                         # algunos tags devuelven objeto con .value, otros devuelven valor directo
#                         valor = result.value if hasattr(result, "value") else result
#                         print(f"{tag:<25} | Valor: {valor}")
#                     except Exception as e:
#                         print(f" Error leyendo {tag}: {e}")
#                 print("-" * 50)
#                 time.sleep(1)

#     except Exception as e:
#         print(f"Conexión perdida o error general: {e}")
#         print("Reintentando conexión en 5 segundos...\n")
#         time.sleep(5)







# with LogixDriver(f"{PLC_IP}") as plc:
#     print("Conectado al PLC — lectura cada 1 segundo\n")

#     while True:
#         start = time.time()  # marca el inicio del ciclo

#         for tag in tags:
#             try:
#                 value = plc.read(tag).value
#                 print(f"{tag:<25} | Tipo: {type(value.value).__name__:<10} | Valor: {value.value}")
#             except Exception as e:
#                 print(f"Error leyendo {tag}: {e}")

#         print("-" * 40)

#         # esperar hasta que haya pasado 1 segundo exacto
#         elapsed = time.time() - start
#         sleep_time = max(0, 1 - elapsed)
#         time.sleep(sleep_time)





