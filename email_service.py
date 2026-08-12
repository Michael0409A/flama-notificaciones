import smtplib
from email.mime.text import MIMEText

EMAIL_USUARIO = "notificacionesflama3@gmail.com" # <-- PONE TU GMAIL
EMAIL_CONTRASENA = "ngygzcyaedqvjktd" # <-- PONE TU CONTRASEÑA DE APLICACION

def enviar_mail(nombre_tarea, fecha_venc, dias_aviso, destinatarios_str):
    destinatarios = [d.strip() for d in destinatarios_str.split(",") if d]

    if dias_aviso > 0:
        asunto = f"[AVISO] {nombre_tarea} vence en {dias_aviso} dias"
        cuerpo = f"Hola,\n\nTe recordamos que la tarea '{nombre_tarea}' vence el dia {fecha_venc}.\nFaltan {dias_aviso} dias.\n\nSaludos,\nSistema FLAMA"
    else:
        asunto = f"[VENCE HOY] {nombre_tarea}"
        cuerpo = f"Hola,\n\nLa tarea '{nombre_tarea}' vence HOY {fecha_venc}.\n\nSaludos,\nSistema FLAMA"

    msg = MIMEText(cuerpo)
    msg['Subject'] = asunto
    msg['From'] = EMAIL_USUARIO
    msg['To'] = ", ".join(destinatarios)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USUARIO, EMAIL_CONTRASENA)
        server.sendmail(EMAIL_USUARIO, destinatarios, msg.as_string())
        server.quit()
        print(f"[OK] Mail enviado: {nombre_tarea} a {destinatarios}")
    except Exception as e:
        print(f"[ERROR] No se pudo enviar mail: {e}")