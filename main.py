from fastapi import FastAPI, Request, BackgroundTasks, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from datetime import datetime, date, timedelta
import sqlite3
import os

from email_service import enviar_mail
from telegram_service import enviar_telegram
from scheduler import iniciar_scheduler

app = FastAPI(title="Notificacion Flama")
DB_NAME = "tareas.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tareas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  tarea TEXT NOT NULL, 
                  fecha_proxima TEXT NOT NULL, 
                  hora_envio TEXT NOT NULL,
                  repeticion TEXT DEFAULT 'unica', 
                  cada_cantidad INTEGER DEFAULT 1, 
                  total_repeticiones INTEGER DEFAULT 1, 
                  repeticiones_hechas INTEGER DEFAULT 0,
                  dias_aviso TEXT DEFAULT '', 
                  email_activo INTEGER DEFAULT 0, 
                  telegram_activo INTEGER DEFAULT 0,
                  destinatarios TEXT DEFAULT '', 
                  destinatarios_telegram TEXT DEFAULT '', 
                  enviado INTEGER DEFAULT 0,
                  creado_en TEXT DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@app.on_event("startup")
def startup_event():
    init_db()
    iniciar_scheduler()
    print("====================================")
    print(" App FLAMA iniciada correctamente ")
    print(" Scheduler corriendo cada 30 seg ")
    print("====================================")

HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NOTIFICACIÓN FLAMA</title>
<style>
    body{font-family:'Segoe UI',Arial,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px;margin:0}
    .container{max-width:1000px;margin:auto;background:#161b22;padding:25px;border-radius:12px;border:1px solid #30363d}
    h1{color:#ff4d4d;text-align:center;margin-bottom:30px}
    h2{border-bottom:1px solid #30363d;padding-bottom:10px}
    input,select,button{width:100%;padding:12px;margin:8px 0;border-radius:6px;border:1px solid #30363d;background:#0d1117;color:#c9d1d9;box-sizing:border-box}
    button{background:#238636;border:none;cursor:pointer;font-weight:bold;font-size:16px}
    button:hover{background:#2ea043}
    button.danger{background:#da3633} button.danger:hover{background:#f85149}
    button.test{background:#1f6feb} button.test:hover{background:#388bfd}
    .task{background:#21262d;padding:20px;margin:15px 0;border-radius:8px;border-left:4px solid #ff4d4d;display:flex;justify-content:space-between;align-items:center}
    .badge{display:inline-block;padding:4px 10px;border-radius:15px;font-size:12px;margin-right:8px;font-weight:bold}
    .badge.mail{background:#1f6feb} .badge.tg{background:#238636} .badge.off{background:#484f58}
    .grid{display:grid;grid-template-columns:1fr 1fr;gap:15px}
    label{font-size:14px;color:#8b949e}
    .checkbox-label{display:flex;align-items:center;gap:8px}
    .actions{display:flex;gap:10px}
    .alert{padding:10px;background:#238636;border-radius:6px;margin-bottom:15px;display:none}
</style>
<script>
async function probarEnvio(id) {
    if(!confirm('¿Enviar notificacion de prueba ahora?')) return;
    const btn = document.getElementById('btn-test-'+id);
    btn.innerText = 'Enviando...';
    btn.disabled = true;
    const res = await fetch('/probar/'+id, {method:'POST'});
    const data = await res.json();
    alert(data.message);
    btn.innerText = 'Probar Envío';
    btn.disabled = false;
}
async function eliminarTarea(id) {
    if(!confirm('¿Seguro que quieres eliminar esta tarea?')) return;
    await fetch('/eliminar/'+id, {method:'POST'});
    location.reload();
}
</script>
</head>
<body>
<div class="container">
    <h1>🔔 NOTIFICACIÓN FLAMA</h1>
    
    <div id="alert" class="alert"></div>

    <h2>Crear Nueva Tarea</h2>
    <form method="post" action="/crear">
        <input name="tarea" placeholder="Nombre de la tarea" required>
        <div class="grid">
            <div><label>Fecha Vencimiento:</label><input type="date" name="fecha_proxima" required></div>
            <div><label>Hora Envío:</label><input type="time" name="hora_envio" required></div>
        </div>
        
        <label>Repetir:</label>
        <select name="repeticion" id="repeticion" onchange="toggleRep()">
            <option value="unica">Única vez</option>
            <option value="dias">Cada X Días</option>
            <option value="semanas">Cada X Semanas</option>
            <option value="meses">Cada X Meses</option>
        </select>
        <div class="grid" id="rep_fields">
            <div><input name="cada_cantidad" type="number" placeholder="Cada cuantos" value="1" min="1"></div>
            <div><input name="total_repeticiones" type="number" placeholder="Total de repeticiones" value="1" min="1"></div>
        </div>

        <input name="dias_aviso" placeholder="Avisar días antes: ej: 3,1">
        
        <div class="grid">
            <div>
                <div class="checkbox-label"><input type="checkbox" name="email_activo" id="email_activo"><label for="email_activo">Activar Email</label></div>
                <input name="destinatarios" placeholder="emails@ separados por coma">
            </div>
            <div>
                <div class="checkbox-label"><input type="checkbox" name="telegram_activo" id="telegram_activo"><label for="telegram_activo">Activar Telegram</label></div>
                <input name="destinatarios_telegram" placeholder="chat_ids@ separados por coma">
            </div>
        </div>
        
        <button type="submit">Guardar Tarea</button>
    </form>

    <h2>Tareas Activas</h2>
    <div id="tasks">{tasks}</div>
</div>
<script>
function toggleRep(){
    const val = document.getElementById('repeticion').value;
    document.getElementById('rep_fields').style.display = val === 'unica' ? 'none' : 'grid';
}
toggleRep();
</script>
</body>
</html>
"""

def render_tasks():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM tareas WHERE enviado = 0 ORDER BY fecha_proxima, hora_envio")
    tareas = c.fetchall()
    conn.close()
    
    if not tareas:
        return "<p style='text-align:center;color:#8b949e'>No hay tareas activas</p>"
    
    html_tasks = ""
    for t in tareas:
        badges = ""
        badges += '<span class="badge mail">EMAIL</span>' if t['email_activo'] else '<span class="badge off">EMAIL OFF</span>'
        badges += '<span class="badge tg">TELEGRAM</span>' if t['telegram_activo'] else '<span class="badge off">TELEGRAM OFF</span>'
        
        fecha_formateada = datetime.strptime(t['fecha_proxima'], '%Y-%m-%d').strftime('%d/%m/%Y')
        rep_texto = "Única vez"
        if t['repeticion'] != 'unica':
            rep_texto = f"Cada {t['cada_cantidad']} {t['repeticion']} - Quedan: {t['total_repeticiones'] - t['repeticiones_hechas']}"
        
        html_tasks += f'''
        <div class="task">
            <div>
                <b style="font-size:18px">{t["tarea"]}</b><br>
                <span style="color:#8b949e">Vence: {fecha_formateada} a las {t["hora_envio"][:5]}</span><br>
                <span style="color:#8b949e">{rep_texto}</span><br>
                {badges}
            </div>
            <div class="actions">
                <button class="test" id="btn-test-{t["id"]}" onclick="probarEnvio({t["id"]})">Probar Envío</button>
                <button class="danger" onclick="eliminarTarea({t["id"]})">Eliminar</button>
            </div>
        </div>'''
    return html_tasks

@app.get("/", response_class=HTMLResponse)
async def home():
    tasks_html = render_tasks()
    return HTML.format(tasks=tasks_html)

@app.post("/crear")
async def crear_tarea(
    tarea: str = Form(...), 
    fecha_proxima: str = Form(...), 
    hora_envio: str = Form(...),
    repeticion: str = Form("unica"), 
    cada_cantidad: int = Form(1), 
    total_repeticiones: int = Form(1),
    dias_aviso: str = Form(""), 
    email_activo: str = Form(None), 
    telegram_activo: str = Form(None),
    destinatarios: str = Form(""), 
    destinatarios_telegram: str = Form("")
):
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO tareas 
                (tarea, fecha_proxima, hora_envio, repeticion, cada_cantidad, total_repeticiones, dias_aviso, email_activo, telegram_activo, destinatarios, destinatarios_telegram) 
                VALUES (?,?,?,?,?,?,?)""",
              (tarea, fecha_proxima, hora_envio, repeticion, cada_cantidad, total_repeticiones, dias_aviso, 
               1 if email_activo else 0, 1 if telegram_activo else 0, destinatarios, destinatarios_telegram))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.post("/probar/{tarea_id}")
async def probar_envio(tarea_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM tareas WHERE id = ?", (tarea_id,))
    tarea = c.fetchone()
    conn.close()
    
    if not tarea:
        return JSONResponse({"message": "Tarea no encontrada"})
    
    fecha_fmt = datetime.strptime(tarea['fecha_proxima'], '%Y-%m-%d').strftime('%d/%m/%Y')
    
    try:
        if tarea['email_activo']: enviar_mail(tarea['tarea'], fecha_fmt, 0, tarea['destinatarios'])
        if tarea['telegram_activo']: enviar_telegram(tarea['tarea'], fecha_fmt, 0, tarea['destinatarios_telegram'])
        return JSONResponse({"message": "✅ Envío de prueba realizado"})
    except Exception as e:
        return JSONResponse({"message": f"❌ Error: {str(e)}"})

@app.post("/eliminar/{tarea_id}")
async def eliminar_tarea(tarea_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM tareas WHERE id = ?", (tarea_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)
