from datetime import datetime, date, timedelta
import sqlite3
import time
import threading
from email_service import enviar_mail
from telegram_service import enviar_telegram
from dateutil.relativedelta import relativedelta

DB_NAME = "tareas.db"

def get_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def revisar_tareas():
    ahora_dt = datetime.now()
    hoy = ahora_dt.date()
    ahora_hm = ahora_dt.strftime('%H:%M') # solo hora y minuto
    
    print(f"[{ahora_dt.strftime('%Y-%m-%d %H:%M:%S')}] === REVISANDO ===")
    
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM tareas WHERE enviado = 0")
        tareas = c.fetchall()

        for tarea in tareas:
            fecha_venc_str = tarea['fecha_proxima']
            if not fecha_venc_str: continue

            fecha_venc = datetime.strptime(fecha_venc_str, '%Y-%m-%d').date()
            hora_envio_hm = tarea['hora_envio'][:5] # "09:00:00" -> "09:00"
            
            enviar_hoy = False
            dias_ant_enviado = 0

            # 1. AVISOS DIAS ANTES
            if tarea['dias_aviso']:
                dias_lista = [int(d) for d in tarea['dias_aviso'].split(',') if d.strip().isdigit()]
                for dias_ant in dias_lista:
                    fecha_aviso = fecha_venc - timedelta(days=dias_ant)
                    if fecha_aviso == hoy and hora_envio_hm == ahora_hm: # CAMBIO: == en vez de <=
                        dias_ant_enviado = dias_ant
                        enviar_hoy = True
                        print(f" -> [AVISO {dias_ant} dias] {tarea['tarea']}")

            # 2. VENCE HOY
            if fecha_venc == hoy and hora_envio_hm == ahora_hm: # CAMBIO: == en vez de <=
                dias_ant_enviado = 0
                enviar_hoy = True
                print(f" -> [ENVIADO VENCE HOY] {tarea['tarea']}")

            if enviar_hoy:
                # Enviar
                if tarea['email_activo'] == 1 and tarea['destinatarios']:
                    try:
                        enviar_mail(tarea['tarea'], fecha_venc.strftime('%d/%m/%Y'), dias_ant_enviado, tarea['destinatarios'])
                    except Exception as e:
                        print(f"ERROR EMAIL: {e}")
                
                if tarea['telegram_activo'] == 1 and tarea['destinatarios_telegram']:
                    try:
                        enviar_telegram(tarea['tarea'], fecha_venc.strftime('%Y-%m-%d'), dias_ant_enviado, tarea['destinatarios_telegram'])
                    except Exception as e:
                        print(f"ERROR TELEGRAM: {e}")

                # Actualizar repeticion
                rep_hechas = tarea['repeticiones_hechas'] + 1
                if tarea['repeticion'] != 'unica' and rep_hechas < tarea['total_repeticiones']:
                    delta = None
                    if tarea['repeticion'] == 'dias': delta = relativedelta(days=tarea['cada_cantidad'])
                    if tarea['repeticion'] == 'semanas': delta = relativedelta(weeks=tarea['cada_cantidad'])
                    if tarea['repeticion'] == 'meses': delta = relativedelta(months=tarea['cada_cantidad'])

                    nueva_fecha = fecha_venc + delta
                    c.execute("UPDATE tareas SET fecha_proxima =?, repeticiones_hechas =? WHERE id =?",
                              (nueva_fecha.strftime('%Y-%m-%d'), rep_hechas, tarea['id']))
                    print(f" -> [REPROGRAMADA] {tarea['tarea']} para {nueva_fecha}")
                else:
                    c.execute("UPDATE tareas SET enviado = 1 WHERE id =?", (tarea['id'],))
                    print(f" -> [FINALIZADA] {tarea['tarea']}")
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"ERROR EN SCHEDULER: {e}")

def iniciar_scheduler():
    def loop():
        while True:
            revisar_tareas()
            time.sleep(30) # cada 30 seg
    
    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    print("Scheduler iniciado. Revisando cada 30 segundos.")
