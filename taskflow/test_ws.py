import websocket

# Proyecto inexistente (ej. ID 999)
try:
    ws = websocket.create_connection("ws://127.0.0.1:8000/ws/projects/999/")
    ws.send('{"test": "ok"}')
    print("Respuesta:", ws.recv())
    ws.close()
except Exception as e:
    print("Conexión rechazada correctamente (Tarea cumplida):", e)