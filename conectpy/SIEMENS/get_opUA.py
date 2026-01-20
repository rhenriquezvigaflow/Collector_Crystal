from opcua import Client
import time

OPC_SERVER_URL = "opc.tcp://192.168.17.10:4840"

# Lista de NodeIds (copiados desde UaExpert)
NODES = {
    "TAGS_01_REAL": "ns=4;i=3",
    "TAGS_02_REAL": "ns=4;i=4",
    "TAGS_03_REAL": "ns=4;i=5",
}

client = Client(OPC_SERVER_URL)

try:
    print(f"Conectando a {OPC_SERVER_URL} ...")
    client.connect()
    print("Conectado correctamente.\n")

    # Crear nodos
    nodes = {
        name: client.get_node(node_id)
        for name, node_id in NODES.items()
    }

    # Mostrar info
    for name, node in nodes.items():
        print(f"{name}")
        print(f"  NodeId   : {node.nodeid}")
        print(f"  DataType : {node.get_data_type_as_variant_type()}")
        print("")

    # Loop de lectura
    while True:
        print("----- Lectura -----")
        for name, node in nodes.items():
            value = node.get_value()
            print(f"{name}: {value}")
        time.sleep(1)

except Exception as e:
    print(f"Error: {e}")

finally:
    client.disconnect()
    print("Desconectado.")
