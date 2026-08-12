import requests
import os  # <-- AGREGADO

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") # <-- CAMBIADO: ya no quemado

def enviar_telegram(tarea, fecha, dias, destinatarios_str):
    if not destinatarios_str or not TELEGRAM_TOKEN: # <-- AGREGADO: chequeo por si falta el token
        return
    chat_ids = [d.strip() for d in destinatarios_str.split(",") if d]

    if dias > 0:
        mensaje = f"🔔 *AVISO FLAMA*\n\nFaltan *{dias} días* para: *{tarea}*\nVence el: {fecha}"
    else:
        mensaje = f"🚨 *VENCE HOY FLAMA*\n\nLa tarea: *{tarea}*\nVence: {fecha}"

    for chat_id in chat_ids:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {'chat_id': chat_id, 'text': mensaje, 'parse_mode': 'Markdown'}
        try:
            requests.post(url, data=payload, timeout=10)
            print(f"[OK] Telegram enviado a: {chat_id}")
        except Exception as e:
            print(f"[ERROR] Telegram: {e}")