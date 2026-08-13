from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import sqlite3
import os
import datetime

from email_service import enviar_mail
from telegram_service import enviar_telegram
from scheduler import iniciar_scheduler

app = FastAPI()

DB_NAME = "/data/tareas.db" # CLAVE 1: QUE NO SE BORRE

def get_db():
    os.makedirs("/data", exist_ok=True) # crea la carpeta si no existe
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def crear_tabla():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS tareas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarea TEXT,
        fecha_inicio DATE,
        fecha_proxima DATE,
        hora_envio TEXT,
        repeticion TEXT,
        cada_cantidad INTEGER,
        total_repeticiones INTEGER,
        email_activo INTEGER,
        telegram_activo INTEGER,
        destinatarios TEXT,
        dias_aviso TEXT,
        destinatarios_telegram TEXT,
        enviado INTEGER DEFAULT 0,
        repeticiones_hechas INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()

@app.on_event("startup")
def startup_event():
    crear_tabla()
    iniciar_scheduler()

CSS = """ :root{ --bg:#0a0a0a; --card:#121212; --border:#ff2e2e; --text:#e0e0e0; --muted:#aaa; --red:#ff2e2e; --input-bg:#1a1a1a; } body { font-family: 'Segoe UI', sans-serif; background: #000; color: var(--text); margin:0; padding: 40px 20px; display:flex; justify-content:center; align-items:flex-start; min-height:100vh; }.container { width: 100%; max-width: 680px; background: linear-gradient(180deg, #141414, #0f0f0f); padding: 30px 35px; border-radius: 16px; border: 2px solid var(--border); box-shadow: 0 0 30px rgba(255,46,46,0.25); }.header { display: flex; justify-content: flex-end; align-items: center; margin-bottom: 25px; }.btn-header { color: var(--text); text-decoration: none; border:1px solid #333; background:#1a1a1a; padding:8px 14px; border-radius:8px; font-size:13px; } h1 { color: var(--red); font-size: 34px; margin: 0 0 25px 0; font-weight: 800; letter-spacing: 2px; text-shadow: 0 0 10px rgba(255,46,46,0.3); text-transform: uppercase; } label { font-weight: 600; display: block; margin-top: 18px; margin-bottom: 8px; color: #ccc; font-size: 14px; }.input-field { width: 100%; padding: 14px; background: var(--input-bg)!important; border: 1px solid #333; color: #fff!important; border-radius: 10px; box-sizing: border-box; font-size:15px; }.input-field:focus { outline: none; border-color: var(--red); box-shadow: 0 0 0 2px rgba(255,46,46,0.15); }.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }.grid-btn { display: grid; grid-template-columns: 1fr auto; gap: 10px; }.btn-red { background: transparent; color: var(--red); border: 1.5px solid var(--red); padding: 14px 18px; border-radius: 10px; cursor: pointer; font-weight:600; white-space:nowrap; }.btn-red:hover{ background: rgba(255,46,46,0.1); }.btn-group { display: flex; flex-wrap:wrap; gap: 10px; margin-top: 10px; }.btn-dia { padding: 12px 18px; background: var(--input-bg); border: 1px solid #333; color: #ccc; border-radius: 10px; cursor: pointer; font-weight: bold; font-size:15px; }.btn-dia.active { background: var(--red); border-color: var(--red); color: #fff; }.btn-submit { background: var(--red); color: white; border: none; padding: 15px; width: 100%; font-size: 16px; font-weight: bold; border-radius: 10px; cursor: pointer; margin-top:25px; }.btn-test { background: transparent; color: var(--red); border: 1.5px solid var(--red); padding: 15px; width: 100%; font-size: 16px; font-weight: bold; border-radius: 10px; cursor: pointer; }.btn-row{ display:grid; grid-template-columns: 1fr 1fr; gap:15px; margin-top:25px; }.item-list { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; min-height: 10px; }.chip { background: var(--input-bg); border: 1px solid #333; padding: 8px 12px; border-radius: 8px; display: flex; align-items: center; gap: 8px; font-size:14px; }.chip.x { cursor: pointer; color: var(--muted); font-weight:bold; }.chip.x:hover{ color: var(--red); }.card { border:1px solid #333; padding:15px; margin-bottom:10px; border-radius:8px; background:#111; }.card a { color:#ff2e2e; margin-right:15px; text-decoration:none; font-weight:600; } @media(max-width: 700px){ body{ padding: 20px 10px; }.container{ padding: 20px; }.grid-2{ grid-template-columns: 1fr; }.btn-row{ grid-template-columns: 1fr; } """

JS = """ function addChip(containerId, inputId) { const val = document.getElementById(inputId).value.trim(); if(!val) return; const container = document.getElementById(containerId); const chip = document.createElement('div'); chip.className = 'chip'; chip.innerHTML = `${val} <span class="x" onclick="removeChip(this)">✕</span>`; container.appendChild(chip); const hiddenInput = document.createElement('input'); hiddenInput.type = 'hidden'; hiddenInput.name = containerId; hiddenInput.value = val; hiddenInput.className = 'hidden_' + containerId; document.getElementById('hidden_inputs').appendChild(hiddenInput); document.getElementById(inputId).value = ''; } function removeChip(x) { let chip = x.parentElement; let val = chip.childNodes[0].nodeValue.trim(); document.querySelectorAll('.hidden_' + chip.parentElement.id).forEach(inp => { if(inp.value === val) inp.remove(); }); chip.remove(); } function toggleDia(btn){ btn.classList.toggle('active'); updateHidden(); } function updateHidden(){ let dias = [...document.querySelectorAll('.btn-dia.active')].map(b => b.dataset.dia); document.getElementById('dias_hidden').value = dias.join(','); } function addCustomDia(){ const val = document.getElementById('dia_custom_input').value.trim(); if(!val) return; const grupo = document.getElementById('dias_grupo'); val.split(',').forEach(d => { d = d.trim(); if(d &&!isNaN(d) &&!document.querySelector(`.btn-dia[data-dia="${d}"]`)){ let btn = document.createElement('button'); btn.type = 'button'; btn.className = 'btn-dia active'; btn.dataset.dia = d; btn.innerText = d + ' Día' + (d > 1? 's' : ''); btn.onclick = () => toggleDia(btn); grupo.appendChild(btn); } }); document.getElementById('dia_custom_input').value = ''; updateHidden(); } function probar() { const form = document.getElementById('formTarea'); const formData = new FormData(form); fetch('/probar', { method: 'POST', body: formData }).then(res => res.text()).then(alert); } """

def get_regla_texto(rep, cada, total):
    if rep == 'unica': return "No se repite"
    if rep == 'dias': txt = f"Cada {cada} días"
    if rep == 'semanas': txt = f"Cada {cada} semanas"
    if rep == 'meses': txt = f"Mensual, cada {cada} mes{'es' if cada > 1 else ''}"
    return f"{txt} durante {total} veces"

@app.get("/", response_class=HTMLResponse)
def form():
    return f""" <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>{CSS}</style></head> <body><div class="container"> <div class="header"><a href="/tareas" class="btn-header">☰ Mis Recordatorios</a></div> <h1>NOTIFICACIÓN FLAMA</h1> <form action="/crear" method="post" id="formTarea" autocomplete="off"> <label>Recordatorio</label> <input class="input-field" name="tarea" required placeholder="Ej. Reunión con equipo de marketing"> <div class="grid-2"> <div><label>Fecha de Vencimiento</label><input class="input-field" type="date" name="fecha" required></div> <div><label>Hora de Envío ARG</label><input class="input-field" type="time" name="hora_envio" required value="09:00"></div> </div> <div class="grid-2"> <div><label>Repetición</label> <select class="input-field" name="repeticion"> <option value="unica">Una sola vez</option> <option value="dias">Cada X Días</option> <option value="semanas">Cada X Semanas</option> <option value="meses">Cada X Meses</option> </select> </div> <div><label>Cada Cuántos</label><input class="input-field" type="number" name="cada_cantidad" value="1" min="1"></div> </div> <label>Repetir Durante</label> <input class="input-field" type="number" name="total_repeticiones" value="1" min="1"> <span style="font-size:12px; color:#aaa">Cantidad de veces que se va a repetir</span> <label>Destinatarios Gmail</label> <div id="destinatarios" class="item-list"></div> <div class="grid-btn"><input class="input-field" type="email" id="inputMail" placeholder="correo@ejemplo.com"><button type="button" class="btn-red" onclick="addChip('destinatarios', 'inputMail')">+ Agregar</button></div> <label>Destinatarios Telegram</label> <div id="destinatarios_telegram" class="item-list"></div> <div class="grid-btn"><input class="input-field" type="tel" id="inputTelegram" placeholder="123456789"><button type="button" class="btn-red" onclick="addChip('destinatarios_telegram', 'inputTelegram')">+ Agregar</button></div> <label>Días para Avisar</label> <div class="btn-group" id="dias_grupo"> <button type="button" class="btn-dia active" data-dia="1" onclick="toggleDia(this)">1 Día</button> <button type="button" class="btn-dia" data-dia="3" onclick="toggleDia(this)">3 Días</button> <button type="button" class="btn-dia" data-dia="7" onclick="toggleDia(this)">7 Días</button> </div> <input class="input-field" type="text" id="dia_custom_input" placeholder="O añade días personalizados: ej 2,5,10" style="margin-top:10px"> <button type="button" class="btn-red" onclick="addCustomDia()" style="margin-top:10px; width:100%">Añadir Día Personalizado</button> <input type="hidden" name="dias" id="dias_hidden" value="1"> <div id="hidden_inputs"></div> <div class="btn-row"> <button class="btn-submit">Guardar Recordatorio</button> <button type="button" class="btn-test" onclick="probar()">Probar envío ahora</button> </div> </form> </div><script>{JS}</script></body></html> """

@app.post("/crear")
def crear(tarea: str = Form(...), fecha: str = Form(...), hora_envio: str = Form(...),
          repeticion: str = Form("unica"), cada_cantidad: int = Form(1), total_repeticiones: int = Form(1),
          dias: str = Form(""), destinatarios: list[str] = Form([]), destinatarios_telegram: list[str] = Form([])):

    dias_final = ",".join([d.strip() for d in dias.split(",") if d.strip()])
    dest_str = ",".join([d for d in destinatarios if d])
    dest_tele_str = ",".join([d for d in destinatarios_telegram if d])
    email_act = 1 if dest_str else 0
    tele_act = 1 if dest_tele_str else 0
    fecha_inicio = datetime.date.today().strftime("%Y-%m-%d")

    conn = get_db()
    with conn:
        conn.execute("""INSERT INTO tareas
            (tarea, fecha_inicio, fecha_proxima, hora_envio, repeticion, cada_cantidad, total_repeticiones,
            email_activo, telegram_activo, destinatarios, dias_aviso, destinatarios_telegram, enviado, repeticiones_hechas)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0,0)""",
                       (tarea, fecha_inicio, fecha, hora_envio, repeticion, cada_cantidad, total_repeticiones,
                        email_act, tele_act, dest_str, dias_final, dest_tele_str))
    return HTMLResponse("Guardado! <a href='/'>Volver</a>")

@app.post("/probar", response_class=HTMLResponse)
def probar(tarea: str = Form(...), fecha: str = Form(...),
           destinatarios: list[str] = Form([]), destinatarios_telegram: list[str] = Form([])):
    dest_str = ",".join([d for d in destinatarios if d])
    dest_tele_str = ",".join([d for d in destinatarios_telegram if d])
    try:
        if dest_str:
            enviar_mail(tarea, fecha, 0, dest_str)
        if dest_tele_str:
            enviar_telegram(tarea, fecha, 0, dest_tele_str)
        return HTMLResponse("Prueba enviada! Revisa tu mail y telegram <a href='/'>Volver</a>")
    except Exception as e:
        return HTMLResponse(f"ERROR AL ENVIAR: {e} <a href='/'>Volver</a>")

@app.get("/tareas", response_class=HTMLResponse)
def listar():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM tareas WHERE enviado = 0 ORDER BY fecha_proxima ASC")
    tareas = c.fetchall()
    conn.close()

    cards = ""
    for t in tareas:
        regla = get_regla_texto(t['repeticion'], t['cada_cantidad'], t['total_repeticiones'])
        proxima = datetime.datetime.strptime(t['fecha_proxima'], '%Y-%m-%d').strftime('%d/%m/%Y') if t['fecha_proxima'] else '-'
        progreso = f"{t['repeticiones_hechas']} de {t['total_repeticiones']}"
        cards += f""" <div class="card"> <b style='font-size:18px'>{t['tarea']}</b><br> <b>Próximo vencimiento:</b> {proxima} a las {t['hora_envio']} ARG<br> <b>Regla:</b> {regla}<br> <b>Progreso:</b> {progreso}<br> Avisar: {t['dias_aviso']} días antes<br> Gmail: {t['destinatarios'] or '-'}<br> Telegram: {t['destinatarios_telegram'] or '-'}<br> <div style='margin-top:10px'> <a href='/editar/{t['id']}'>✏️ Editar</a> <a href='/borrar/{t['id']}' onclick="return confirm('¿Borrar {t['tarea']}?')">🗑️ Borrar</a> </div> </div>"""

    return f""" <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>{CSS}</style></head> <body><div class="container"> <h1>MIS RECORDATORIOS</h1> <a href="/" class="btn-header">+ Nuevo Recordatorio</a><br><br> {cards if cards else "<p>No hay recordatorios activos</p>"} </div></body></html> """

@app.get("/editar/{id}", response_class=HTMLResponse)
def editar_form(id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM tareas WHERE id =?", (id,))
    t = c.fetchone()
    conn.close()

    mails = t['destinatarios'].split(',') if t['destinatarios'] else []
    teles = t['destinatarios_telegram'].split(',') if t['destinatarios_telegram'] else []
    dias_activos = t['dias_aviso'].split(',') if t['dias_aviso'] else []
    fecha_str = t['fecha_proxima'] if t['fecha_proxima'] else ''

    chips_mail = "".join([f"<div class='chip'>{m} <span class='x' onclick='removeChip(this)'>✕</span></div><input type='hidden' name='destinatarios' value='{m}' class='hidden_destinatarios'>" for m in mails])
    chips_tele = "".join([f"<div class='chip'>{w} <span class='x' onclick='removeChip(this)'>✕</span></div><input type='hidden' name='destinatarios_telegram' value='{w}' class='hidden_destinatarios_telegram'>" for w in teles])

    return f""" <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>{CSS}</style></head> <body><div class="container"> <h1>EDITAR RECORDATORIO</h1> <form action="/editar/{id}" method="post"> <label>Recordatorio</label> <input class="input-field" name="tarea" value="{t['tarea']}" required> <div class="grid-2"> <div><label>Fecha de Vencimiento</label><input class="input-field" type="date" name="fecha" value="{fecha_str}" required></div> <div><label>Hora de Envío ARG</label><input class="input-field" type="time" name="hora_envio" value="{t['hora_envio']}" required></div> </div> <div class="grid-2"> <div><label>Repetición</label> <select class="input-field" name="repeticion"> <option value="unica" {'selected' if t['repeticion']=='unica' else ''}>Una sola vez</option> <option value="dias" {'selected' if t['repeticion']=='dias' else ''}>Cada X Días</option> <option value="semanas" {'selected' if t['repeticion']=='semanas' else ''}>Cada X Semanas</option> <option value="meses" {'selected' if t['repeticion']=='meses' else ''}>Cada X Meses</option> </select> </div> <div><label>Cada Cuántos</label><input class="input-field" type="number" name="cada_cantidad" value="{t['cada_cantidad']}" min="1"></div> </div> <label>Repetir Durante</label> <input class="input-field" type="number" name="total_repeticiones" value="{t['total_repeticiones']}" min="1"> <label>Destinatarios Gmail</label> <div id="destinatarios" class="item-list">{chips_mail}</div> <div class="grid-btn"><input class="input-field" type="email" id="inputMail" placeholder="correo@ejemplo.com"><button type="button" class="btn-red" onclick="addChip('destinatarios', 'inputMail')">+ Agregar</button></div> <label>Destinatarios Telegram</label> <div id="destinatarios_telegram" class="item-list">{chips_tele}</div> <div class="grid-btn"><input class="input-field" type="tel" id="inputTelegram" placeholder="123456789"><button type="button" class="btn-red" onclick="addChip('destinatarios_telegram', 'inputTelegram')">+ Agregar</button></div> <label>Días para Avisar</label> <div class="btn-group" id="dias_grupo"> {"".join([f"<button type='button' class='btn-dia {'active' if str(d) in dias_activos else ''}' data-dia='{d}' onclick='toggleDia(this)'>{d} Día{'s' if d>1 else ''}</button>" for d in [1,3,7]])} </div> <input class="input-field" type="text" id="dia_custom_input" placeholder="O añade días personalizados: ej 2,5,10" style="margin-top:10px"> <button type="button" class="btn-red" onclick="addCustomDia()" style="margin-top:10px; width:100%">Añadir Día Personalizado</button> <input type="hidden" name="dias" id="dias_hidden" value="{t['dias_aviso']}"> <div id="hidden_inputs"></div> <button class="btn-submit">Guardar Cambios</button> </form> <a href="/tareas" class="btn-header" style="display:inline-block; margin-top:15px">Cancelar</a> </div><script>{JS}</script></body></html> """

@app.post("/editar/{id}")
def editar_tarea(id: int, tarea: str = Form(...), fecha: str = Form(...), hora_envio: str = Form(...),
          repeticion: str = Form("unica"), cada_cantidad: int = Form(1), total_repeticiones: int = Form(1),
          dias: str = Form(""), destinatarios: list[str] = Form([]), destinatarios_telegram: list[str] = Form([])):

    dias_final = ",".join([d.strip() for d in dias.split(",") if d.strip()])
    dest_str = ",".join([d for d in destinatarios if d])
    dest_tele_str = ",".join([d for d in destinatarios_telegram if d])
    email_act = 1 if dest_str else 0
    tele_act = 1 if dest_tele_str else 0

    conn = get_db()
    with conn:
        sql = """UPDATE tareas SET
                 tarea=?, fecha_proxima=?, hora_envio=?, repeticion=?, cada_cantidad=?,
                 total_repeticiones=?, destinatarios=?, destinatarios_telegram=?, dias_aviso=?,
                 email_activo=?, telegram_activo=?, enviado=0, repeticiones_hechas=0
                 WHERE id=?"""
        conn.execute(sql, (tarea, fecha, hora_envio, repeticion, cada_cantidad, total_repeticiones, dest_str, dest_tele_str, dias_final, email_act, tele_act, id))
    return HTMLResponse("Actualizado! <a href='/tareas'>Volver</a>")

@app.get("/borrar/{id}")
def borrar_tarea(id: int):
    conn = get_db()
    with conn:
        conn.execute("DELETE FROM tareas WHERE id =?", (id,))
    return HTMLResponse("Borrado! <a href='/tareas'>Volver</a>")
