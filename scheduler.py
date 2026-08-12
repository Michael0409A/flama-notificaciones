from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, date, timedelta
import sqlite3
from email_service import enviar_mail
from telegram_service import enviar_telegram
from dateutil.relativedelta import relativedelta

DB_NAME = "tareas.db"

def get_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row # para usar t['tarea']
    return conn

def revisar_tareas():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] === REVISANDO ===")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM tareas WHERE enviado = 0")
    tareas = c.fetchall()

    hoy = date.today()
    ahora_str = datetime.now().strftime('%H:%M:%S')

    for tarea in tareas:
        fecha_venc_str = tarea['fecha_proxima'] # SQLite lo guarda como '2025-10-20'
        if not fecha_venc_str: continue

        fecha_venc = datetime.strptime(fecha_venc_str, '%Y-%m-%d').date()
        hora_envio_str = tarea['hora_envio'][:5] # "09:00:00" -> "09:00"

        # 1. AVISOS DIAS ANTES
        if tarea['dias_aviso']:
            dias_lista = [int(d) for d in tarea['dias_aviso'].split(',') if d.strip().isdigit()]
            for dias_ant in dias_lista:
                fecha_aviso = fecha_venc - timedelta(days=dias_ant)
                if fecha_aviso == hoy and hora_envio_str <= ahora_str:
                    if tarea['email_activo']: enviar_mail(tarea['tarea'], fecha_venc.strftime('%d/%m/%Y'), dias_ant, tarea['destinatarios'])
                    if tarea['telegram_activo']: enviar_telegram(tarea['tarea'], fecha_venc.strftime('%d/%m/%Y'), dias_ant, tarea['destinatarios_telegram'])
                    print(f" -> [AVISO {dias_ant} dias] {tarea['tarea']}")

        # 2. VENCE HOY
        if fecha_venc == hoy and hora_envio_str <= ahora_str:
            if tarea['email_activo']: enviar_mail(tarea['tarea'], fecha_venc.strftime('%d/%m/%Y'), 0, tarea['destinatarios'])
            if tarea['telegram_activo']: enviar_telegram(tarea['tarea'], fecha_venc.strftime('%d/%m/%Y'), 0, tarea['destinatarios_telegram'])
            print(f" -> [ENVIADO VENCE HOY] {tarea['tarea']}")

            rep_hechas = tarea['repeticiones_hechas'] + 1
            if tarea['repeticion']!= 'unica' and rep_hechas < tarea['total_repeticiones']:
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

def iniciar_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(revisar_tareas, 'interval', seconds=30)
    scheduler.start()
    print("Scheduler iniciado. Revisando cada 30 segundos.")