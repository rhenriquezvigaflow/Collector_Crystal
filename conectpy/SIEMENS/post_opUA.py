from opcua import Client, ua
import time

# Dirección del servidor OPC UA del PLC
OPC_SERVER_URL = "opc.tcp://192.168.100.10:4840"

# Node IDs según UaExpert 
NODES = {
    "MOTOR": "ns=4;i=79",
    "PARAR": "ns=4;i=78",
    "PARTIR": "ns=4;i=80"
}

# Crear cliente
client = Client(OPC_SERVER_URL)

try:
    print(f"Conectando a {OPC_SERVER_URL} ...")
    client.connect()
    print("Conectado correctamente.\n")

    # Obtener nodos
    node_motor = client.get_node(NODES["MOTOR"])
    node_parar = client.get_node(NODES["PARAR"])
    node_partir = client.get_node(NODES["PARTIR"])

    # Leer valores actuales
    print("Lecturas iniciales:")
    print(f"PLC_MOTOR : {node_motor.get_value()}")
    print(f"PLC_PARAR : {node_parar.get_value()}")
    print(f"PLC_PARTIR: {node_partir.get_value()}")

    # --- Escribir valores ---
    print("Cambiando valores...")

    # Encender motor
    # node_motor.set_value(ua.DataValue(ua.Variant(True, ua.VariantType.Boolean)))
    # print("MOTOR activado (True)")
    # time.sleep(2)

    # Detener motor
    node_motor.set_value(ua.DataValue(ua.Variant(False, ua.VariantType.Boolean)))
    print(" MOTOR detenido (False)")
    time.sleep(2)

    # Activar 'PARTIR' y luego 'PARAR'
    # node_partir.set_value(ua.DataValue(ua.Variant(False, ua.VariantType.Boolean)))
    # print("PARTIR activado")
    # time.sleep(1)

    # node_parar.set_value(ua.DataValue(ua.Variant(True, ua.VariantType.Boolean)))
    # print("PARAR activado")
    # time.sleep(1)

    # --- Confirmar valores ---
    print("Lecturas finales:")
    print(f"PLC_MOTOR : {node_motor.get_value()}")
    print(f"PLC_PARAR : {node_parar.get_value()}")
    print(f"PLC_PARTIR: {node_partir.get_value()}")

except Exception as e:
    print(f"Error: {e}")

finally:
    client.disconnect()
    print(" Desconectado.")
