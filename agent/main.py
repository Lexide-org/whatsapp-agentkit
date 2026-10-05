# agent/main.py — Servidor FastAPI + CRM de WhatsApp con Lucide Icons y Autenticación Robusta
# Generado por AgentKit

"""
Servidor principal del agente de WhatsApp y panel de administración CRM.
Implementa el webhook unificado con deduplicación y el panel administrativo /admin
con interfaz profesional en modo oscuro impulsada por Lucide Icons y sin diálogos nativos.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Request, Response, HTTPException, Depends, status, Form
from fastapi.responses import PlainTextResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from agent.brain import generar_respuesta
from agent.memory import (
    inicializar_db,
    guardar_mensaje,
    obtener_historial,
    es_mensaje_duplicado,
    obtener_estado_chat,
    actualizar_estado_chat,
    obtener_chats_activos,
    verificar_credenciales,
    actualizar_password,
    UsuarioAdmin
)
from agent.auth import (
    obtener_admin_actual,
    obtener_admin_opcional,
    crear_token_sesion,
    COOKIE_NAME
)
from agent.providers import obtener_proveedor

load_dotenv()

# Configuración de logging
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
log_level = logging.DEBUG if ENVIRONMENT == "development" else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger("agentkit")

# Proveedor de WhatsApp
proveedor = obtener_proveedor()
PORT = int(os.getenv("PORT", 8000))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa la base de datos al arrancar el servidor."""
    await inicializar_db()
    logger.info("Base de datos inicializada")
    logger.info(f"Servidor Tabersil Chatbots corriendo en puerto {PORT}")
    logger.info(f"Proveedor de WhatsApp: {proveedor.__class__.__name__}")
    yield


app = FastAPI(
    title="Tabersil Chatbots — WhatsApp AI & CRM",
    version="1.0.0",
    lifespan=lifespan
)

os.makedirs("images", exist_ok=True)
app.mount("/images", StaticFiles(directory="images"), name="images")


# =========================================================================
# LIBRERÍA DE LUCIDE ICONS (SVG NATIVO EMBEBIDO 100% LOCAL Y OFFLINE)
# =========================================================================

LUCIDE_JS_HELPER = """
<script>
    // Diccionario nativo de Lucide Icons (SVG puro, 100% local y sin peticiones externas)
    const LUCIDE_SVGS = {
        'user': '<circle cx="12" cy="7" r="4"/><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>',
        'lock': '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
        'key': '<circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6"/><path d="m15.5 7.5 3 3L22 7l-3-3"/>',
        'log-out': '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/>',
        'bot': '<path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/>',
        'bot-off': '<path d="M13.67 8H18a2 2 0 0 1 2 2v4.33"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M22 22 2 2"/><path d="M8 8H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h12a2 2 0 0 0 1.414-.586"/><path d="M9 13v2"/><path d="M9.67 4H12v2.33"/>',
        'refresh-cw': '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
        'send': '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
        'eye': '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
        'eye-off': '<path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" x2="22" y1="2" y2="22"/>',
        'arrow-right': '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
        'alert-circle': '<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/>',
        'message-square': '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
        'check': '<path d="M20 6 9 17l-5-5"/>',
        'file-text': '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
        'image': '<rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>',
        'mic': '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/>',
        'download': '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
        'phone': '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>',
        'x': '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
        'clock': '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
        'arrow-left': '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
        'check-check': '<path d="M18 6 7 17l-5-5"/><path d="m22 10-7.5 7.5L13 16"/>',
        'search': '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
        'more-vertical': '<circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/>'
    };

    function lucideIcon(name, options = {}) {
        const size = options.size || 16;
        const className = options.class || '';
        const strokeWidth = options.strokeWidth || 2;
        const paths = LUCIDE_SVGS[name] || '';
        return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${strokeWidth}" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-${name} ${className}">${paths}</svg>`;
    }

    function renderLucideIcons() {
        document.querySelectorAll('[data-lucide]').forEach(el => {
            const name = el.getAttribute('data-lucide');
            const size = el.getAttribute('data-size') || 16;
            const cls = el.getAttribute('class') || '';
            const strokeWidth = el.getAttribute('data-stroke-width') || 2;
            el.outerHTML = lucideIcon(name, { size, class: cls, strokeWidth });
        });
    }
    document.addEventListener("DOMContentLoaded", renderLucideIcons);
</script>
"""


# =========================================================================
# VISTA DE LOGIN Y GESTIÓN DE SESIÓN
# =========================================================================

def generar_html_login(error_msg: str = "") -> str:
    """Genera la interfaz de Login profesional y moderna en tono oscuro con Lucide Icons."""
    display_error = "flex" if error_msg else "none"
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
        <meta name="theme-color" content="#000000">
        <title>Tabersil Chatbots — Iniciar Sesión</title>
        <link rel="icon" type="image/png" sizes="64x64" href="/images/favicon.png">
        <link rel="apple-touch-icon" sizes="192x192" href="/images/icon-192.png">
        <link rel="manifest" href="/manifest.json">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="apple-mobile-web-app-title" content="Tabersil">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <script>
            if ('serviceWorker' in navigator) {{
                window.addEventListener('load', () => {{
                    navigator.serviceWorker.register('/sw.js', {{ scope: '/' }})
                        .catch(err => console.log('SW reg error:', err));
                }});
            }}
        </script>
        <style>
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            }}
            body {{
                background-color: #000000;
                color: #FFFFFF;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
                position: relative;
                overflow: hidden;
            }}
            body::before {{
                content: '';
                position: absolute;
                top: -150px;
                left: 50%;
                transform: translateX(-50%);
                width: 600px;
                height: 400px;
                background: radial-gradient(circle, rgba(37, 99, 235, 0.12) 0%, rgba(0, 0, 0, 0) 70%);
                pointer-events: none;
            }}
            .login-card {{
                width: 100%;
                max-width: 400px;
                background-color: #0A0A0A;
                border: 1px solid #1E1E1E;
                border-radius: 12px;
                padding: 36px 32px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.8), 0 0 1px 1px rgba(255, 255, 255, 0.05);
                position: relative;
                z-index: 1;
                transition: transform 0.2s ease, border-color 0.2s ease;
            }}
            .brand-header {{
                text-align: center;
                margin-bottom: 28px;
            }}
            .brand-logo-container {{
                display: flex;
                justify-content: center;
                margin-bottom: 16px;
            }}
            .brand-logo-login {{
                width: 68px;
                height: 68px;
                border-radius: 16px;
                object-fit: cover;
                border: 1px solid rgba(255, 255, 255, 0.1);
                box-shadow: 0 8px 24px rgba(37, 99, 235, 0.25);
            }}
            .brand-badge {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background: #111111;
                border: 1px solid #222222;
                padding: 6px 14px;
                border-radius: 100px;
                font-size: 0.82rem;
                font-weight: 600;
                letter-spacing: -0.01em;
                margin-bottom: 14px;
            }}
            .brand-badge .pill {{
                background: linear-gradient(135deg, #2563EB, #60A5FA);
                color: #FFFFFF;
                padding: 2px 7px;
                border-radius: 6px;
                font-size: 0.7rem;
                font-weight: 700;
                letter-spacing: 0.04em;
            }}
            .brand-title {{
                font-size: 1.4rem;
                font-weight: 700;
                letter-spacing: -0.03em;
                color: #FFFFFF;
                margin-bottom: 6px;
            }}
            .brand-subtitle {{
                font-size: 0.82rem;
                color: #71717A;
                line-height: 1.4;
            }}
            .error-alert {{
                background-color: #1A0D0D;
                border: 1px solid #4A1D1D;
                color: #F87171;
                padding: 10px 14px;
                border-radius: 8px;
                font-size: 0.82rem;
                margin-bottom: 20px;
                display: {display_error};
                align-items: center;
                gap: 8px;
                animation: fadeIn 0.2s ease;
            }}
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(-4px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            .form-group {{
                margin-bottom: 18px;
            }}
            .form-label {{
                display: block;
                font-size: 0.74rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                color: #A1A1AA;
                margin-bottom: 7px;
            }}
            .input-wrapper {{
                position: relative;
                display: flex;
                align-items: center;
            }}
            .input-icon {{
                position: absolute;
                left: 14px;
                color: #52525B;
                pointer-events: none;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .form-input {{
                width: 100%;
                background-color: #050505;
                border: 1px solid #27272A;
                color: #FFFFFF;
                padding: 11px 40px 11px 40px;
                border-radius: 8px;
                font-size: 0.9rem;
                outline: none;
                transition: border-color 0.15s ease, box-shadow 0.15s ease;
            }}
            .form-input:focus {{
                border-color: #3B82F6;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
            }}
            .form-input::placeholder {{
                color: #3F3F46;
            }}
            .toggle-password {{
                position: absolute;
                right: 12px;
                background: none;
                border: none;
                color: #71717A;
                cursor: pointer;
                padding: 4px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: color 0.15s ease;
            }}
            .toggle-password:hover {{
                color: #FFFFFF;
            }}
            .btn-login {{
                width: 100%;
                background: linear-gradient(135deg, #2563EB, #1D4ED8);
                color: #FFFFFF;
                border: none;
                padding: 12px 18px;
                border-radius: 8px;
                font-size: 0.9rem;
                font-weight: 600;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                transition: opacity 0.2s ease, transform 0.1s ease;
                margin-top: 24px;
            }}
            .btn-login:hover {{
                opacity: 0.92;
                transform: translateY(-1px);
            }}
            .btn-login:active {{
                transform: translateY(0);
            }}
            .btn-login:disabled {{
                opacity: 0.6;
                cursor: not-allowed;
            }}
            .spinner {{
                width: 16px;
                height: 16px;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-top-color: #FFFFFF;
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
                display: none;
            }}
            @keyframes spin {{
                to {{ transform: rotate(360deg); }}
            }}
            .dev-hint {{
                margin-top: 22px;
                padding-top: 18px;
                border-top: 1px solid #18181B;
                text-align: center;
                font-size: 0.75rem;
                color: #52525B;
            }}
            .dev-hint code {{
                background-color: #141416;
                padding: 2px 6px;
                border-radius: 4px;
                color: #93C5FD;
                font-family: monospace;
            }}
            .shake {{
                animation: shake 0.35s ease-in-out;
            }}
            @keyframes shake {{
                0%, 100% {{ transform: translateX(0); }}
                20%, 60% {{ transform: translateX(-6px); }}
                40%, 80% {{ transform: translateX(6px); }}
            }}
        </style>
    </head>
    <body>
        <div class="login-card" id="login-card">
            <div class="brand-header">
                <div class="brand-logo-container">
                    <img src="/images/logo.png" alt="Tabersil Chatbots Logo" class="brand-logo-login">
                </div>
                <div class="brand-badge">
                    <i data-lucide="message-square" data-size="15" style="color: #60A5FA;"></i>
                    <span>WhatsApp</span>
                    <span class="pill">Bot</span>
                </div>
                <h1 class="brand-title">Tabersil Chatbots</h1>
                <p class="brand-subtitle">Panel de gestión y atención al cliente WhatsApp</p>
            </div>

            <div class="error-alert" id="error-alert">
                <i data-lucide="alert-circle" data-size="16"></i>
                <span id="error-text">{error_msg or "Usuario o contraseña incorrectos"}</span>
            </div>

            <form id="login-form" method="POST" action="/login" onsubmit="handleLoginSubmit(event)">
                <div class="form-group">
                    <label class="form-label" for="username">Usuario</label>
                    <div class="input-wrapper">
                        <div class="input-icon">
                            <i data-lucide="user" data-size="15"></i>
                        </div>
                        <input type="text" id="username" name="username" class="form-input" placeholder="admin" required autofocus autocomplete="username">
                    </div>
                </div>

                <div class="form-group">
                    <label class="form-label" for="password">Contraseña</label>
                    <div class="input-wrapper">
                        <div class="input-icon">
                            <i data-lucide="lock" data-size="15"></i>
                        </div>
                        <input type="password" id="password" name="password" class="form-input" placeholder="••••••••" required autocomplete="current-password">
                        <button type="button" class="toggle-password" onclick="togglePasswordVisibility()" title="Mostrar/ocultar contraseña">
                            <span id="eye-icon-container"><i data-lucide="eye" data-size="16"></i></span>
                        </button>
                    </div>
                </div>

                <button type="submit" class="btn-login" id="btn-submit">
                    <span id="btn-text">Entrar al CRM</span>
                    <div class="spinner" id="btn-spinner"></div>
                    <span id="arrow-icon-container"><i data-lucide="arrow-right" data-size="16"></i></span>
                </button>
            </form>

            <div class="dev-hint">
                Credenciales predeterminadas: <code>admin</code> / <code>admin</code>
            </div>
        </div>

        {LUCIDE_JS_HELPER}

        <script>
            function togglePasswordVisibility() {{
                const input = document.getElementById("password");
                const eyeContainer = document.getElementById("eye-icon-container");
                if (input.type === "password") {{
                    input.type = "text";
                    eyeContainer.innerHTML = lucideIcon("eye-off", {{ size: 16 }});
                }} else {{
                    input.type = "password";
                    eyeContainer.innerHTML = lucideIcon("eye", {{ size: 16 }});
                }}
            }}

            async function handleLoginSubmit(e) {{
                e.preventDefault();
                const username = document.getElementById("username").value.trim();
                const password = document.getElementById("password").value;
                const errorAlert = document.getElementById("error-alert");
                const errorText = document.getElementById("error-text");
                const card = document.getElementById("login-card");
                const btnSubmit = document.getElementById("btn-submit");
                const btnText = document.getElementById("btn-text");
                const btnSpinner = document.getElementById("btn-spinner");
                const arrowContainer = document.getElementById("arrow-icon-container");

                if (!username || !password) return;

                btnSubmit.disabled = true;
                btnText.textContent = "Verificando...";
                btnSpinner.style.display = "block";
                arrowContainer.style.display = "none";
                errorAlert.style.display = "none";

                try {{
                    const res = await fetch("/api/login", {{
                        method: "POST",
                        headers: {{ "Content-Type": "application/json" }},
                        body: JSON.stringify({{ username, password }})
                    }});

                    const data = await res.json();

                    if (res.ok && data.status === "ok") {{
                        btnText.textContent = "¡Acceso correcto!";
                        btnSpinner.style.display = "none";
                        btnSubmit.style.background = "#10B981";
                        arrowContainer.innerHTML = lucideIcon("check", {{ size: 16 }});
                        arrowContainer.style.display = "block";
                        setTimeout(() => {{
                            window.location.href = data.redirect || "/admin";
                        }}, 250);
                    }} else {{
                        errorText.textContent = data.detail || "Usuario o contraseña incorrectos";
                        errorAlert.style.display = "flex";
                        card.classList.add("shake");
                        setTimeout(() => card.classList.remove("shake"), 400);

                        btnSubmit.disabled = false;
                        btnText.textContent = "Entrar al CRM";
                        btnSpinner.style.display = "none";
                        arrowContainer.style.display = "block";
                        document.getElementById("password").value = "";
                        document.getElementById("password").focus();
                    }}
                }} catch (err) {{
                    errorText.textContent = "Error de conexión con el servidor";
                    errorAlert.style.display = "flex";
                    btnSubmit.disabled = false;
                    btnText.textContent = "Entrar al CRM";
                    btnSpinner.style.display = "none";
                    arrowContainer.style.display = "block";
                }}
            }}
        </script>
    </body>
    </html>
    """


@app.get("/login", response_class=HTMLResponse)
async def ver_login(request: Request):
    """Muestra la página de inicio de sesión. Si ya tiene sesión, redirige a /admin."""
    user = await obtener_admin_opcional(request)
    if user:
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    return HTMLResponse(content=generar_html_login())


@app.post("/api/login")
async def api_login(payload: dict, response: Response):
    """Endpoint API JSON para autenticación. Genera cookie segura HttpOnly."""
    username = payload.get("username", "").strip()
    password = payload.get("password", "")

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Por favor ingresa usuario y contraseña"
        )

    user = await verificar_credenciales(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos"
        )

    # Crear token firmado
    token = crear_token_sesion(user.username)

    # Guardar en cookie HttpOnly
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=86400 * 7,
        path="/"
    )

    return {
        "status": "ok",
        "redirect": "/admin",
        "user": user.username,
        "debe_cambiar_password": user.debe_cambiar_password
    }


@app.post("/login")
async def form_login(
    username: str = Form(...),
    password: str = Form(...)
):
    """Fallback para envío estándar de formulario HTML."""
    user = await verificar_credenciales(username.strip(), password)
    if not user:
        return HTMLResponse(
            content=generar_html_login("Usuario o contraseña incorrectos"),
            status_code=401
        )

    token = crear_token_sesion(user.username)
    redirect = RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    redirect.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=86400 * 7,
        path="/"
    )
    return redirect


@app.get("/logout")
@app.post("/logout")
async def logout(response: Response):
    """Cierra la sesión eliminando la cookie y redirige a /login."""
    redirect = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    redirect.delete_cookie(key=COOKIE_NAME, path="/")
    return redirect


@app.get("/")
async def health_check():
    """Endpoint de salud."""
    return {"status": "ok", "service": "tabersil-chatbots"}


@app.get("/manifest.json")
async def manifest_endpoint():
    """Manifiesto Web App para PWA."""
    manifest_data = {
        "name": "Tabersil Chatbots",
        "short_name": "Tabersil",
        "description": "Panel CRM y Asistente IA de WhatsApp — Tabersil Studios",
        "start_url": "/admin",
        "scope": "/",
        "display": "standalone",
        "background_color": "#000000",
        "theme_color": "#000000",
        "orientation": "portrait-primary",
        "icons": [
            {
                "src": "/images/favicon.png",
                "sizes": "64x64",
                "type": "image/png"
            },
            {
                "src": "/images/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": "/images/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    }
    return JSONResponse(content=manifest_data, media_type="application/manifest+json")


@app.get("/sw.js")
async def service_worker_endpoint():
    """Service Worker para soporte de instalación PWA."""
    sw_code = """
    const CACHE_NAME = 'tabersil-chatbots-v1';
    const PRECACHE_URLS = [
        '/admin',
        '/login',
        '/manifest.json',
        '/images/favicon.png',
        '/images/icon-192.png',
        '/images/icon-512.png',
        '/images/logo.png'
    ];

    self.addEventListener('install', (event) => {
        event.waitUntil(
            caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS)).then(() => self.skipWaiting())
        );
    });

    self.addEventListener('activate', (event) => {
        event.waitUntil(
            caches.keys().then((keys) => {
                return Promise.all(
                    keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
                );
            }).then(() => self.clients.claim())
        );
    });

    self.addEventListener('fetch', (event) => {
        if (event.request.method !== 'GET') return;
        event.respondWith(
            fetch(event.request)
                .then((response) => {
                    if (response && response.status === 200 && response.type === 'basic') {
                        const clone = response.clone();
                        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
                    }
                    return response;
                })
                .catch(() => caches.match(event.request))
        );
    });
    """
    return Response(
        content=sw_code,
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/"}
    )


@app.get("/webhook")
async def webhook_verificacion(request: Request):
    """Verificación GET del webhook (requerido por Meta Cloud API)."""
    resultado = await proveedor.validar_webhook(request)
    if resultado is not None:
        return PlainTextResponse(str(resultado))
    return {"status": "ok"}


@app.post("/webhook")
async def webhook_handler(request: Request):
    """
    Recibe mensajes de WhatsApp via el proveedor configurado.
    Procesa, audita, deduplica y responde con Gemini si el chat no está pausado.
    """
    try:
        mensajes = await proveedor.parsear_webhook(request)

        for msg in mensajes:
            if msg.es_propio:
                continue

            # 1. Deduplicación de Mensajes
            if msg.mensaje_id and await es_mensaje_duplicado(msg.mensaje_id):
                logger.info(f"Mensaje duplicado detectado y silenciado: {msg.mensaje_id}")
                continue

            logger.info(f"Mensaje entrante de {msg.telefono}: {msg.texto}")

            # 2. Guardar mensaje entrante inmediatamente (con flags multimedia)
            await guardar_mensaje(
                telefono=msg.telefono,
                role="user",
                content=msg.texto,
                mensaje_id=msg.mensaje_id,
                url_media=msg.url_media,
                es_imagen=msg.es_imagen,
                es_audio=msg.es_audio,
                es_documento=msg.es_documento,
                enviado_por_admin=False
            )

            # 3. Verificar si el chat tiene la IA pausada
            is_paused = await obtener_estado_chat(msg.telefono)
            if is_paused:
                logger.info(f"IA Pausada para {msg.telefono}. Registrado en CRM sin respuesta automática.")
                continue

            # 4. Obtener últimos 30 mensajes para el contexto de Gemini
            historial = await obtener_historial(msg.telefono, limite=30)
            
            # Generar respuesta con Gemini AI
            respuesta = await generar_respuesta(msg.texto, historial)

            # Guardar respuesta generada
            await guardar_mensaje(
                telefono=msg.telefono,
                role="assistant",
                content=respuesta,
                enviado_por_admin=False
            )

            # Enviar respuesta por WhatsApp
            await proveedor.enviar_mensaje(msg.telefono, respuesta)
            logger.info(f"Respuesta IA enviada a {msg.telefono}: {respuesta}")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# ENDPOINTS Y VISTA DEL CRM ADMINISTRATIVO (/admin) CON LUCIDE ICONS
# =========================================================================

@app.get("/admin", response_class=HTMLResponse)
async def ver_panel_crm(request: Request):
    """
    Renderiza la interfaz web del CRM responsiva (con comportamiento de WhatsApp en smartphone)
    manteniendo la paleta de color minimalista oscura original (negro absoluto y acentos azules)
    y Lucide Icons 100% locales.
    Si el usuario no está autenticado, redirige limpiamente a /login.
    """
    admin_user = await obtener_admin_opcional(request)
    if not admin_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    debe_cambiar_pw = "true" if admin_user.debe_cambiar_password else "false"
    modal_display = 'flex' if debe_cambiar_pw == 'true' else 'none'
    username_actual = admin_user.username
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
        <meta name="theme-color" content="#000000">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="apple-mobile-web-app-title" content="Tabersil">
        <title>Tabersil Chatbots — Panel CRM</title>
        <link rel="icon" type="image/png" sizes="64x64" href="/images/favicon.png">
        <link rel="shortcut icon" href="/images/favicon.png">
        <link rel="apple-touch-icon" sizes="192x192" href="/images/icon-192.png">
        <link rel="apple-touch-icon" sizes="512x512" href="/images/icon-512.png">
        <link rel="manifest" href="/manifest.json">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <script>
            if ('serviceWorker' in navigator) {{
                window.addEventListener('load', () => {{
                    navigator.serviceWorker.register('/sw.js', {{ scope: '/' }})
                        .then((reg) => console.log('SW Tabersil CRM activo:', reg.scope))
                        .catch((err) => console.warn('SW error:', err));
                }});
            }}
        </script>
        <style>
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                -webkit-tap-highlight-color: transparent;
            }}
            body {{
                background-color: #000000;
                color: #FFFFFF;
                height: 100vh;
                height: 100dvh;
                width: 100%;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }}

            /* Top Navbar */
            .navbar {{
                height: 60px;
                background-color: #000000;
                border-bottom: 1px solid #1A1A1A;
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0 16px;
                z-index: 20;
                flex-shrink: 0;
            }}
            .navbar-brand {{
                font-weight: 700;
                font-size: 1rem;
                letter-spacing: -0.02em;
                display: flex;
                align-items: center;
                gap: 8px;
                color: #FFFFFF;
            }}
            .navbar-logo-img {{
                width: 26px;
                height: 26px;
                border-radius: 6px;
                object-fit: cover;
                border: 1px solid rgba(255, 255, 255, 0.15);
                box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25);
            }}
            .navbar-brand span.highlight {{
                background: linear-gradient(135deg, #2563EB, #60A5FA);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            .navbar-center {{
                font-size: 0.85rem;
                color: #888888;
                font-weight: 500;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .navbar-actions {{
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .user-chip {{
                background: #111111;
                border: 1px solid #222222;
                padding: 5px 12px;
                border-radius: 6px;
                font-size: 0.78rem;
                color: #D4D4D8;
                display: flex;
                align-items: center;
                gap: 6px;
            }}
            .btn {{
                background-color: transparent;
                border: 1px solid #222222;
                color: #FFFFFF;
                padding: 6px 12px;
                font-size: 0.8rem;
                font-weight: 500;
                cursor: pointer;
                border-radius: 6px;
                display: inline-flex;
                align-items: center;
                gap: 6px;
                transition: background-color 0.15s, border-color 0.15s, color 0.15s;
                text-decoration: none;
            }}
            .btn:hover {{
                background-color: #1A1A1A;
                border-color: #333333;
            }}
            .btn-logout {{
                background-color: #161111;
                border-color: #331A1A;
                color: #F87171;
            }}
            .btn-logout:hover {{
                background-color: #2A1515;
                border-color: #552222;
                color: #EF4444;
            }}
            .btn-pwa {{
                background: linear-gradient(135deg, #1E3A8A, #2563EB);
                border-color: #3B82F6;
                color: #FFFFFF;
            }}
            .btn-pwa:hover {{
                background: linear-gradient(135deg, #2563EB, #1D4ED8);
                border-color: #60A5FA;
            }}

            /* Contenedor Principal */
            .main-container {{
                flex: 1;
                display: flex;
                overflow: hidden;
                position: relative;
                width: 100%;
                height: calc(100dvh - 60px);
            }}

            /* Sidebar */
            .sidebar {{
                width: 340px;
                min-width: 300px;
                background-color: #000000;
                border-right: 1px solid #1A1A1A;
                display: flex;
                flex-direction: column;
                flex-shrink: 0;
                z-index: 10;
            }}
            .sidebar-header {{
                padding: 14px 16px;
                border-bottom: 1px solid #1A1A1A;
                font-size: 0.78rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                color: #71717A;
                font-weight: 600;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .sidebar-header-title {{
                display: flex;
                align-items: center;
                gap: 6px;
            }}
            .search-box-row {{
                padding: 10px 14px;
                border-bottom: 1px solid #1A1A1A;
                background-color: #000000;
            }}
            .search-box {{
                background-color: #0A0A0A;
                border: 1px solid #1F1F1F;
                border-radius: 8px;
                display: flex;
                align-items: center;
                padding: 7px 12px;
                gap: 8px;
                transition: border-color 0.15s;
            }}
            .search-box:focus-within {{
                border-color: #3B82F6;
            }}
            .search-box svg {{
                color: #71717A;
                flex-shrink: 0;
            }}
            .search-input {{
                background: transparent;
                border: none;
                outline: none;
                color: #FFFFFF;
                font-size: 0.85rem;
                width: 100%;
            }}
            .search-input::placeholder {{
                color: #52525B;
            }}

            /* Lista de chats */
            .chat-list {{
                flex: 1;
                overflow-y: auto;
                background-color: #000000;
            }}
            .chat-list::-webkit-scrollbar {{
                width: 5px;
            }}
            .chat-list::-webkit-scrollbar-thumb {{
                background: #1A1A1A;
                border-radius: 3px;
            }}
            .chat-item {{
                padding: 14px 16px;
                border-bottom: 1px solid #111111;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 12px;
                transition: background-color 0.15s;
                position: relative;
                user-select: none;
            }}
            .chat-item:hover {{
                background-color: #0B0B0B;
            }}
            .chat-item.active {{
                background-color: #111111;
            }}
            .chat-avatar {{
                width: 44px;
                height: 44px;
                border-radius: 50%;
                background-color: #111111;
                border: 1px solid #222222;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #71717A;
                flex-shrink: 0;
            }}
            .chat-info {{
                flex: 1;
                min-width: 0;
                display: flex;
                flex-direction: column;
                gap: 4px;
            }}
            .chat-item-header {{
                display: flex;
                justify-content: space-between;
                align-items: baseline;
            }}
            .chat-item-phone {{
                font-weight: 600;
                font-size: 0.88rem;
                color: #FFFFFF;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            .chat-item-time {{
                font-size: 0.7rem;
                color: #52525B;
                white-space: nowrap;
                margin-left: 6px;
            }}
            .chat-item-body {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 8px;
            }}
            .chat-item-preview {{
                font-size: 0.78rem;
                color: #71717A;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                display: flex;
                align-items: center;
                gap: 4px;
                flex: 1;
            }}
            .badge-status {{
                font-size: 0.65rem;
                padding: 2px 6px;
                border-radius: 4px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.02em;
                display: inline-flex;
                align-items: center;
                gap: 4px;
                flex-shrink: 0;
            }}
            .badge-paused {{
                background-color: #2D1414;
                color: #EF4444;
                border: 1px solid #4A1D1D;
            }}

            /* Chat Area */
            .chat-area {{
                flex: 1;
                display: flex;
                flex-direction: column;
                background-color: #000000;
                position: relative;
                overflow: hidden;
            }}
            .chat-header {{
                height: 60px;
                padding: 0 16px;
                border-bottom: 1px solid #1A1A1A;
                display: flex;
                justify-content: space-between;
                align-items: center;
                background-color: #000000;
                flex-shrink: 0;
                z-index: 10;
            }}
            .chat-header-left {{
                display: flex;
                align-items: center;
                gap: 10px;
                min-width: 0;
            }}
            .btn-back {{
                display: none;
                background: transparent;
                border: none;
                color: #71717A;
                width: 38px;
                height: 38px;
                border-radius: 50%;
                cursor: pointer;
                align-items: center;
                justify-content: center;
                margin-left: -6px;
                transition: background-color 0.15s, color 0.15s;
            }}
            .btn-back:hover, .btn-back:active {{
                background-color: #1A1A1A;
                color: #FFFFFF;
            }}
            .chat-header-avatar {{
                width: 38px;
                height: 38px;
                border-radius: 50%;
                background-color: #111111;
                border: 1px solid #222222;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #71717A;
                flex-shrink: 0;
            }}
            .chat-header-meta {{
                display: flex;
                flex-direction: column;
                min-width: 0;
            }}
            .chat-header-phone {{
                font-size: 0.95rem;
                font-weight: 600;
                color: #FFFFFF;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            .chat-header-status {{
                font-size: 0.72rem;
                color: #71717A;
                display: flex;
                align-items: center;
                gap: 4px;
            }}
            .chat-header-status.online {{
                color: #60A5FA;
            }}
            .chat-actions {{
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .btn-toggle-ia {{
                background-color: transparent;
                border: 1px solid #222222;
                color: #FFFFFF;
                padding: 6px 12px;
                font-size: 0.8rem;
                font-weight: 500;
                cursor: pointer;
                border-radius: 6px;
                display: inline-flex;
                align-items: center;
                gap: 6px;
                transition: background-color 0.15s, border-color 0.15s, color 0.15s;
            }}
            .btn-toggle-ia:hover {{
                background-color: #1A1A1A;
                border-color: #333333;
            }}
            .btn-toggle-ia.paused {{
                background-color: #3B1E1E;
                border-color: #7F1D1D;
                color: #EF4444;
            }}

            /* Mensajes */
            .messages-viewport {{
                flex: 1;
                padding: 20px;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                gap: 12px;
                background-color: #000000;
            }}
            .messages-viewport::-webkit-scrollbar {{
                width: 5px;
            }}
            .messages-viewport::-webkit-scrollbar-thumb {{
                background: #1A1A1A;
                border-radius: 3px;
            }}
            .chat-info-pill {{
                align-self: center;
                background-color: #0A0A0A;
                border: 1px solid #1E1E1E;
                color: #71717A;
                font-size: 0.73rem;
                padding: 5px 12px;
                border-radius: 6px;
                display: flex;
                align-items: center;
                gap: 6px;
                margin-bottom: 6px;
            }}
            .message-row {{
                display: flex;
                width: 100%;
            }}
            .message-row.user {{
                justify-content: flex-start;
            }}
            .message-row.assistant {{
                justify-content: flex-end;
            }}
            .message-bubble {{
                max-width: 70%;
                padding: 10px 14px;
                font-size: 0.88rem;
                line-height: 1.4;
                display: flex;
                flex-direction: column;
                gap: 6px;
                position: relative;
                word-wrap: break-word;
                overflow-wrap: break-word;
            }}
            .message-row.user .message-bubble {{
                background-color: #161616;
                border: 1px solid #222222;
                border-radius: 8px 8px 8px 2px;
                color: #E5E5E5;
            }}
            .message-row.assistant .message-bubble {{
                background-color: #0B0B0B;
                border: 1px solid #1C1C1C;
                border-radius: 8px 8px 2px 8px;
                color: #D4D4D4;
            }}
            .message-row.assistant .message-bubble.admin-sent {{
                background-color: #0E1E38;
                border: 1px solid #1E3A8A;
                border-radius: 8px 8px 2px 8px;
                color: #E0E7FF;
            }}
            .msg-admin-tag {{
                font-size: 0.68rem;
                font-weight: 600;
                color: #60A5FA;
                display: flex;
                align-items: center;
                gap: 4px;
                margin-bottom: 2px;
                text-transform: uppercase;
                letter-spacing: 0.03em;
            }}
            .message-meta {{
                font-size: 0.65rem;
                color: #555555;
                align-self: flex-end;
                display: flex;
                align-items: center;
                gap: 4px;
                margin-left: 12px;
            }}
            .msg-check {{
                color: #555555;
            }}
            .msg-check.read {{
                color: #3B82F6;
            }}
            .message-media {{
                max-width: 100%;
                border-radius: 6px;
                overflow: hidden;
                border: 1px solid #222222;
            }}
            .message-media img {{
                max-width: 100%;
                max-height: 220px;
                display: block;
            }}
            .message-media audio {{
                width: 100%;
                min-width: 200px;
                display: block;
            }}
            .message-media a.doc-link {{
                color: #60A5FA;
                text-decoration: none;
                font-size: 0.8rem;
                display: flex;
                align-items: center;
                gap: 6px;
                padding: 6px 10px;
                background-color: #111116;
                border-radius: 4px;
                transition: background-color 0.15s;
            }}
            .message-media a.doc-link:hover {{
                background-color: #181822;
            }}

            /* Input Area */
            .input-area {{
                padding: 12px 16px;
                border-top: 1px solid #1A1A1A;
                background-color: #000000;
                display: flex;
                gap: 10px;
                align-items: center;
                flex-shrink: 0;
            }}
            .input-pill-wrapper {{
                flex: 1;
                background-color: #0A0A0A;
                border: 1px solid #1F1F1F;
                border-radius: 24px;
                display: flex;
                align-items: center;
                padding: 0 16px;
                transition: border-color 0.15s;
            }}
            .input-pill-wrapper:focus-within {{
                border-color: #333333;
            }}
            .input-message {{
                flex: 1;
                background: transparent;
                border: none;
                outline: none;
                color: #FFFFFF;
                height: 42px;
                font-size: 16px;
            }}
            .input-message::placeholder {{
                color: #52525B;
            }}
            .btn-send {{
                background-color: #2563EB;
                border: none;
                width: 42px;
                height: 42px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                border-radius: 50%;
                color: #FFFFFF;
                flex-shrink: 0;
                transition: background-color 0.15s, transform 0.1s;
            }}
            .btn-send:hover {{
                background-color: #1D4ED8;
                transform: translateY(-1px);
            }}
            .btn-send:active {{
                transform: translateY(0);
            }}

            /* Estado Vacío Desktop */
            .no-chat-selected {{
                flex: 1;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                color: #52525B;
                font-size: 0.85rem;
                gap: 14px;
                padding: 30px;
                text-align: center;
            }}
            .empty-graphic {{
                width: 120px;
                height: 120px;
                border-radius: 50%;
                background: rgba(37, 99, 235, 0.08);
                border: 1px dashed rgba(37, 99, 235, 0.25);
                display: flex;
                align-items: center;
                justify-content: center;
                color: #3B82F6;
                margin-bottom: 4px;
            }}
            .empty-title {{
                font-size: 1.2rem;
                font-weight: 700;
                color: #FFFFFF;
            }}
            .empty-desc {{
                font-size: 0.85rem;
                color: #71717A;
                max-width: 360px;
                line-height: 1.5;
            }}

            /* Modal Cambio Contraseña */
            .modal-overlay {{
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-color: rgba(0, 0, 0, 0.92);
                backdrop-filter: blur(8px);
                -webkit-backdrop-filter: blur(8px);
                z-index: 1000;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            .modal-card {{
                width: 100%;
                max-width: 400px;
                background-color: #0A0A0A;
                border: 1px solid #1E1E1E;
                border-radius: 12px;
                padding: 36px 32px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.8), 0 0 1px 1px rgba(255, 255, 255, 0.05);
                position: relative;
                z-index: 1;
                transition: transform 0.2s ease, border-color 0.2s ease;
            }}
            .brand-header {{
                text-align: center;
                margin-bottom: 24px;
            }}
            .brand-badge {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background: #111111;
                border: 1px solid #222222;
                padding: 6px 14px;
                border-radius: 100px;
                font-size: 0.82rem;
                font-weight: 600;
                margin-bottom: 12px;
            }}
            .brand-badge .pill {{
                background: linear-gradient(135deg, #2563EB, #60A5FA);
                color: #FFFFFF;
                padding: 2px 7px;
                border-radius: 6px;
                font-size: 0.7rem;
                font-weight: 700;
            }}
            .brand-title {{
                font-size: 1.35rem;
                font-weight: 700;
                color: #FFFFFF;
                margin-bottom: 6px;
            }}
            .brand-subtitle {{
                font-size: 0.82rem;
                color: #71717A;
                line-height: 1.4;
            }}
            .error-alert {{
                background-color: #1A0D0D;
                border: 1px solid #4A1D1D;
                color: #F87171;
                padding: 10px 14px;
                border-radius: 8px;
                font-size: 0.82rem;
                margin-bottom: 18px;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .form-group {{
                margin-bottom: 18px;
            }}
            .form-label {{
                display: block;
                font-size: 0.74rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                color: #A1A1AA;
                margin-bottom: 7px;
            }}
            .input-wrapper {{
                position: relative;
                display: flex;
                align-items: center;
            }}
            .input-icon {{
                position: absolute;
                left: 14px;
                color: #52525B;
                pointer-events: none;
                display: flex;
                align-items: center;
            }}
            .form-input {{
                width: 100%;
                background-color: #050505;
                border: 1px solid #27272A;
                color: #FFFFFF;
                padding: 11px 40px 11px 40px;
                border-radius: 8px;
                font-size: 0.9rem;
                outline: none;
                transition: border-color 0.15s ease, box-shadow 0.15s ease;
            }}
            .form-input:focus {{
                border-color: #3B82F6;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
            }}
            .toggle-password {{
                position: absolute;
                right: 12px;
                background: none;
                border: none;
                color: #71717A;
                cursor: pointer;
                padding: 4px;
                display: flex;
                align-items: center;
            }}
            .btn-login {{
                width: 100%;
                background: linear-gradient(135deg, #2563EB, #1D4ED8);
                color: #FFFFFF;
                border: none;
                padding: 12px 18px;
                border-radius: 8px;
                font-size: 0.9rem;
                font-weight: 600;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                transition: opacity 0.2s ease, transform 0.1s ease;
            }}
            .btn-login:hover {{
                opacity: 0.92;
                transform: translateY(-1px);
            }}
            .btn-cancel {{
                width: 100%;
                margin-top: 10px;
                background: transparent;
                border: 1px solid #27272A;
                color: #71717A;
                padding: 11px 18px;
                border-radius: 8px;
                font-size: 0.88rem;
                font-weight: 500;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
            }}
            .spinner {{
                width: 16px;
                height: 16px;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-top-color: #FFFFFF;
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
                display: none;
            }}
            @keyframes spin {{
                to {{ transform: rotate(360deg); }}
            }}
            .shake {{
                animation: shake 0.35s ease-in-out;
            }}
            @keyframes shake {{
                0%, 100% {{ transform: translateX(0); }}
                20%, 60% {{ transform: translateX(-6px); }}
                40%, 80% {{ transform: translateX(6px); }}
            }}

            /* Responsive media queries */
            @media (max-width: 768px) {{
                .navbar {{
                    height: 54px;
                    padding: 0 12px;
                }}
                .navbar-center {{
                    display: none;
                }}
                .user-chip {{
                    display: none;
                }}
                .btn span {{
                    display: none;
                }}
                .btn {{
                    padding: 8px;
                    border-radius: 50%;
                }}

                .main-container {{
                    height: calc(100dvh - 54px);
                }}

                .main-container:not(.mobile-chat-active) .sidebar {{
                    width: 100%;
                    border-right: none;
                    display: flex;
                }}
                .main-container:not(.mobile-chat-active) .chat-area {{
                    display: none;
                }}

                .main-container.mobile-chat-active .sidebar {{
                    display: none;
                }}
                .main-container.mobile-chat-active .chat-area {{
                    display: flex;
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    width: 100%;
                    height: 100vh;
                    height: 100dvh;
                    z-index: 100;
                }}

                .btn-back {{
                    display: flex !important;
                }}

                .message-bubble {{
                    max-width: 86%;
                }}

                .input-area {{
                    padding: 10px 12px;
                    padding-bottom: max(10px, env(safe-area-inset-bottom));
                }}
            }}

            @media (min-width: 769px) {{
                .btn-back {{
                    display: none !important;
                }}
                .sidebar {{
                    width: 340px !important;
                    display: flex !important;
                }}
                .chat-area {{
                    display: flex !important;
                }}
            }}
        </style>
    </head>
    <body>
        <!-- Modal Cambio Contraseña -->
        <div id="pw-modal" class="modal-overlay" style="display: {modal_display};">
            <div class="modal-card" id="pw-card">
                <div class="brand-header">
                    <div class="brand-badge">
                        <i data-lucide="lock" data-size="15" style="color: #60A5FA;"></i>
                        <span>Tabersil</span>
                        <span class="pill">Seguridad</span>
                    </div>
                    <h1 class="brand-title">Actualizar Clave</h1>
                    <p class="brand-subtitle">Establece una contraseña segura para tu cuenta de administrador</p>
                </div>

                <div class="error-alert" id="pw-error-alert" style="display: none;">
                    <i data-lucide="alert-circle" data-size="16"></i>
                    <span id="pw-error-text"></span>
                </div>

                <div class="form-group">
                    <label class="form-label" for="new-pw">Nueva Contraseña</label>
                    <div class="input-wrapper">
                        <div class="input-icon">
                            <i data-lucide="lock" data-size="15"></i>
                        </div>
                        <input type="password" id="new-pw" class="form-input" placeholder="••••••••" required autocomplete="new-password" onkeypress="handlePwKeyPress(event)">
                        <button type="button" class="toggle-password" onclick="togglePwVisibility('new-pw', 'eye-new-pw')" title="Mostrar/ocultar">
                            <span id="eye-new-pw"><i data-lucide="eye" data-size="16"></i></span>
                        </button>
                    </div>
                </div>

                <div class="form-group">
                    <label class="form-label" for="confirm-pw">Confirmar Contraseña</label>
                    <div class="input-wrapper">
                        <div class="input-icon">
                            <i data-lucide="key" data-size="15"></i>
                        </div>
                        <input type="password" id="confirm-pw" class="form-input" placeholder="••••••••" required autocomplete="new-password" onkeypress="handlePwKeyPress(event)">
                        <button type="button" class="toggle-password" onclick="togglePwVisibility('confirm-pw', 'eye-confirm-pw')" title="Mostrar/ocultar">
                            <span id="eye-confirm-pw"><i data-lucide="eye" data-size="16"></i></span>
                        </button>
                    </div>
                </div>

                <button type="button" class="btn-login" id="btn-save-pw" onclick="cambiarPassword()" style="margin-top: 22px;">
                    <span id="btn-save-pw-text">Guardar Contraseña</span>
                    <div class="spinner" id="btn-save-pw-spinner"></div>
                    <span id="btn-save-pw-icon"><i data-lucide="check" data-size="16"></i></span>
                </button>

                <button type="button" class="btn-cancel" id="btn-cancel-pw" onclick="cerrarModalPassword()" style="display: {'none' if debe_cambiar_pw == 'true' else 'flex'};">
                    <i data-lucide="x" data-size="14"></i>
                    <span>Cancelar</span>
                </button>
            </div>
        </div>

        <!-- Top Navbar -->
        <div class="navbar" id="main-navbar">
            <div class="navbar-brand">
                <img src="/images/favicon.png" alt="Tabersil Logo" class="navbar-logo-img">
                <span>Tabersil <span class="highlight">Chatbots</span></span>
            </div>
            <div class="navbar-center" id="active-client-label">
                <i data-lucide="phone" data-size="14" style="color: #71717A;"></i>
                <span>Ningún chat seleccionado</span>
            </div>
            <div class="navbar-actions">
                <button class="btn btn-pwa" id="btn-pwa-install" onclick="instalarPWA()" style="display: none;" title="Instalar Tabersil Chatbots">
                    <i data-lucide="download" data-size="14"></i>
                    <span>Instalar App</span>
                </button>
                <div class="user-chip">
                    <i data-lucide="user" data-size="14"></i>
                    <span>{username_actual}</span>
                </div>
                <button class="btn" onclick="abrirModalPassword()" title="Cambiar clave">
                    <i data-lucide="key" data-size="14"></i>
                    <span>Clave</span>
                </button>
                <a href="/logout" class="btn btn-logout" title="Cerrar sesión">
                    <i data-lucide="log-out" data-size="14"></i>
                    <span>Salir</span>
                </a>
            </div>
        </div>

        <!-- Contenedor Principal (Sidebar + Chat Area) -->
        <div class="main-container" id="main-container">
            <!-- Barra Lateral de Conversaciones -->
            <div class="sidebar" id="sidebar-container">
                <div class="sidebar-header">
                    <div class="sidebar-header-title">
                        <i data-lucide="message-square" data-size="14"></i>
                        <span>Conversaciones</span>
                    </div>
                    <button class="btn" onclick="cargarChats()" title="Actualizar lista">
                        <i data-lucide="refresh-cw" data-size="13"></i>
                    </button>
                </div>
                <div class="search-box-row">
                    <div class="search-box">
                        <i data-lucide="search" data-size="14"></i>
                        <input type="text" id="chat-search" class="search-input" placeholder="Buscar un chat..." oninput="filtrarChats()">
                    </div>
                </div>
                <div class="chat-list" id="chat-list-container">
                    <!-- Dinámico -->
                </div>
            </div>

            <!-- Ventana de Chat (Conversación) -->
            <div class="chat-area" id="chat-area-container">
                <!-- Header de la Conversación estilo WhatsApp -->
                <div class="chat-header" id="chat-header-actions" style="display: none;">
                    <div class="chat-header-left">
                        <button class="btn-back" onclick="volverALista()" title="Volver a chats">
                            <i data-lucide="arrow-left" data-size="20"></i>
                        </button>
                        <div class="chat-header-avatar">
                            <i data-lucide="user" data-size="18"></i>
                        </div>
                        <div class="chat-header-meta">
                            <span class="chat-header-phone" id="chat-header-phone">+123456789</span>
                            <span class="chat-header-status online" id="chat-header-status">
                                <i data-lucide="bot" data-size="11"></i> IA Activa
                            </span>
                        </div>
                    </div>
                    <div class="chat-actions">
                        <button class="btn-toggle-ia" id="btn-toggle-ia" onclick="toggleIA()">
                            <span id="ia-icon-container"></span>
                            <span id="ia-text-container">IA Activa</span>
                        </button>
                    </div>
                </div>

                <!-- Historial de Mensajes -->
                <div class="messages-viewport" id="messages-container">
                    <div class="no-chat-selected">
                        <div class="empty-graphic">
                            <img src="/images/icon-192.png" alt="Tabersil Chatbots" style="width: 68px; height: 68px; border-radius: 16px; object-fit: cover; box-shadow: 0 4px 16px rgba(0,0,0,0.6);">
                        </div>
                        <h2 class="empty-title">Tabersil Chatbots</h2>
                        <p class="empty-desc">Selecciona una conversación en la lista para ver el historial y responder al cliente.</p>
                    </div>
                </div>

                <!-- Barra de Entrada de Mensajes -->
                <div class="input-area" id="input-container" style="display: none;">
                    <div class="input-pill-wrapper">
                        <input type="text" id="msg-input" class="input-message" placeholder="Escribe un mensaje de venta..." onkeypress="handleKeyPress(event)" autocomplete="off">
                    </div>
                    <button class="btn-send" onclick="enviarMensaje()" title="Enviar mensaje">
                        <i data-lucide="send" data-size="16"></i>
                    </button>
                </div>
            </div>
        </div>

        {LUCIDE_JS_HELPER}

        <script>
            let clienteActivo = null;
            let listaChatsCache = [];
            let filtroBusqueda = "";

            function abrirModalPassword() {{
                document.getElementById("pw-modal").style.display = "flex";
                const errorAlert = document.getElementById("pw-error-alert");
                if (errorAlert) errorAlert.style.display = "none";
                document.getElementById("new-pw").value = "";
                document.getElementById("confirm-pw").value = "";
                setTimeout(() => document.getElementById("new-pw").focus(), 60);
            }}

            function cerrarModalPassword() {{
                document.getElementById("pw-modal").style.display = "none";
            }}

            function togglePwVisibility(inputId, eyeId) {{
                const input = document.getElementById(inputId);
                const eye = document.getElementById(eyeId);
                if (input.type === "password") {{
                    input.type = "text";
                    eye.innerHTML = lucideIcon("eye-off", {{ size: 16 }});
                }} else {{
                    input.type = "password";
                    eye.innerHTML = lucideIcon("eye", {{ size: 16 }});
                }}
            }}

            function handlePwKeyPress(e) {{
                if (e.key === "Enter") {{
                    cambiarPassword();
                }}
            }}

            function parsearMarkdownWhatsapp(texto) {{
                if (!texto) return "";
                let html = texto
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;");
                
                html = html.replace(/\\*([^\\*]+)\\*/g, '<strong>$1</strong>');
                html = html.replace(/_([^_]+)_/g, '<em>$1</em>');
                html = html.replace(/~([^~]+)~/g, '<del>$1</del>');
                html = html.replace(/```([^`]+)```/g, '<code>$1</code>');
                html = html.replace(/(https?:\\/\\/[^\\s<]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer" style="color: #60A5FA;">$1</a>');
                
                return html;
            }}

            async function cambiarPassword() {{
                const newPw = document.getElementById("new-pw").value;
                const confirmPw = document.getElementById("confirm-pw").value;
                const errorAlert = document.getElementById("pw-error-alert");
                const errorText = document.getElementById("pw-error-text");
                const card = document.getElementById("pw-card");
                const btnSubmit = document.getElementById("btn-save-pw");
                const btnText = document.getElementById("btn-save-pw-text");
                const btnSpinner = document.getElementById("btn-save-pw-spinner");
                const btnIcon = document.getElementById("btn-save-pw-icon");

                function mostrarError(msg) {{
                    errorText.textContent = msg;
                    errorAlert.style.display = "flex";
                    card.classList.add("shake");
                    setTimeout(() => card.classList.remove("shake"), 400);
                    btnSubmit.disabled = false;
                    btnText.textContent = "Guardar Contraseña";
                    btnSpinner.style.display = "none";
                    btnIcon.style.display = "block";
                }}

                if (!newPw) {{
                    mostrarError("La contraseña no puede estar vacía.");
                    document.getElementById("new-pw").focus();
                    return;
                }}
                if (newPw.length < 4) {{
                    mostrarError("La contraseña debe tener al menos 4 caracteres.");
                    document.getElementById("new-pw").focus();
                    return;
                }}
                if (newPw !== confirmPw) {{
                    mostrarError("Las contraseñas no coinciden.");
                    document.getElementById("confirm-pw").focus();
                    return;
                }}

                btnSubmit.disabled = true;
                btnText.textContent = "Guardando...";
                btnSpinner.style.display = "block";
                btnIcon.style.display = "none";
                errorAlert.style.display = "none";

                try {{
                    const response = await fetch("/admin/cambiar-password", {{
                        method: "POST",
                        headers: {{ "Content-Type": "application/json" }},
                        body: JSON.stringify({{ password: newPw }})
                    }});

                    if (response.status === 401) {{
                        window.location.href = "/login";
                        return;
                    }}

                    if (response.ok) {{
                        btnText.textContent = "¡Contraseña actualizada!";
                        btnSpinner.style.display = "none";
                        btnSubmit.style.background = "#10B981";
                        btnIcon.innerHTML = lucideIcon("check", {{ size: 16 }});
                        btnIcon.style.display = "block";
                        
                        setTimeout(() => {{
                            document.getElementById("pw-modal").style.display = "none";
                            btnSubmit.disabled = false;
                            btnText.textContent = "Guardar Contraseña";
                            btnSubmit.style.background = "";
                            document.getElementById("new-pw").value = "";
                            document.getElementById("confirm-pw").value = "";
                            cargarChats();
                        }}, 450);
                    }} else {{
                        const data = await response.json();
                        mostrarError(data.detail || "Error al cambiar la contraseña.");
                    }}
                }} catch (e) {{
                    mostrarError("Error de conexión con el servidor.");
                }}
            }}

            function filtrarChats() {{
                const input = document.getElementById("chat-search");
                filtroBusqueda = input ? input.value.toLowerCase().trim() : "";
                renderizarListaChats();
            }}

            async function cargarChats() {{
                try {{
                    const response = await fetch("/admin/chats");
                    if (response.status === 401) {{
                        window.location.href = "/login";
                        return;
                    }}
                    listaChatsCache = await response.json();
                    renderizarListaChats();
                }} catch (e) {{
                    console.error("Error cargando chats", e);
                }}
            }}

            function renderizarListaChats() {{
                const container = document.getElementById("chat-list-container");
                container.innerHTML = "";

                let chats = listaChatsCache;
                if (filtroBusqueda) {{
                    chats = chats.filter(c => 
                        (c.telefono && c.telefono.toLowerCase().includes(filtroBusqueda)) ||
                        (c.preview && c.preview.toLowerCase().includes(filtroBusqueda))
                    );
                }}

                if (chats.length === 0) {{
                    if (filtroBusqueda) {{
                        container.innerHTML = `
                            <div style="padding: 24px 20px; font-size: 0.8rem; color: #71717A; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 8px;">
                                ${{lucideIcon('search', {{ size: 20 }})}}
                                <span>No se encontraron chats para "<strong>${{filtroBusqueda}}</strong>"</span>
                            </div>
                        `;
                    }} else {{
                        container.innerHTML = `
                            <div style="padding: 24px 20px; font-size: 0.8rem; color: #52525B; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 8px;">
                                ${{lucideIcon('message-square', {{ size: 24 }})}}
                                <span>No hay conversaciones aún.<br><br>Inicia una prueba con <code>python tests/test_local.py</code></span>
                            </div>
                        `;
                    }}
                    return;
                }}

                chats.forEach(chat => {{
                    const div = document.createElement("div");
                    div.className = `chat-item ${{clienteActivo === chat.telefono ? 'active' : ''}}`;
                    div.onclick = () => seleccionarChat(chat.telefono, chat.is_ai_paused);
                    
                    const badgeHtml = chat.is_ai_paused ? 
                        `<span class="badge-status badge-paused">${{lucideIcon('bot-off', {{ size: 10 }})}} Pausado</span>` : "";

                    let previewIcon = "";
                    if (chat.es_imagen) {{
                        previewIcon = lucideIcon('image', {{ size: 13 }}) + " ";
                    }} else if (chat.es_audio) {{
                        previewIcon = lucideIcon('mic', {{ size: 13 }}) + " ";
                    }} else if (chat.es_documento) {{
                        previewIcon = lucideIcon('file-text', {{ size: 13 }}) + " ";
                    }} else {{
                        previewIcon = lucideIcon('check-check', {{ size: 13, class: 'msg-check' }}) + " ";
                    }}

                    div.innerHTML = `
                        <div class="chat-avatar">
                            ${{lucideIcon('user', {{ size: 20 }})}}
                        </div>
                        <div class="chat-info">
                            <div class="chat-item-header">
                                <span class="chat-item-phone">${{chat.telefono}}</span>
                                <span class="chat-item-time">${{chat.ultima_actividad || ''}}</span>
                            </div>
                            <div class="chat-item-body">
                                <span class="chat-item-preview">${{previewIcon}}${{chat.preview || 'Sin mensajes'}}</span>
                                ${{badgeHtml}}
                            </div>
                        </div>
                    `;
                    container.appendChild(div);
                }});
            }}

            async function seleccionarChat(telefono, isAiPaused) {{
                clienteActivo = telefono;
                
                document.getElementById("active-client-label").innerHTML = `${{lucideIcon('phone', {{ size: 14 }})}} <span>Cliente: ${{telefono}}</span>`;
                document.getElementById("chat-header-phone").innerText = telefono;
                document.getElementById("chat-header-actions").style.display = "flex";
                document.getElementById("input-container").style.display = "flex";

                // Modo responsivo: Activar vista de chat a pantalla completa en móvil
                const mainContainer = document.getElementById("main-container");
                if (mainContainer) mainContainer.classList.add("mobile-chat-active");

                if (window.innerWidth <= 768) {{
                    history.pushState({{ chat: telefono }}, '', '#chat-' + encodeURIComponent(telefono));
                }}
                
                actualizarBotonIA(isAiPaused);
                renderizarListaChats();
                cargarHistorial();

                if (window.innerWidth > 768) {{
                    setTimeout(() => {{
                        const input = document.getElementById("msg-input");
                        if (input) input.focus();
                    }}, 80);
                }}
            }}

            function volverALista(popHistory = true) {{
                clienteActivo = null;
                const mainContainer = document.getElementById("main-container");
                if (mainContainer) mainContainer.classList.remove("mobile-chat-active");

                document.getElementById("chat-header-actions").style.display = "none";
                document.getElementById("input-container").style.display = "none";
                document.getElementById("active-client-label").innerHTML = `${{lucideIcon('phone', {{ size: 14 }})}} <span>Ningún chat seleccionado</span>`;
                
                document.getElementById("messages-container").innerHTML = `
                    <div class="no-chat-selected">
                        <div class="empty-graphic">
                            <img src="/images/icon-192.png" alt="Tabersil Chatbots" style="width: 68px; height: 68px; border-radius: 16px; object-fit: cover; box-shadow: 0 4px 16px rgba(0,0,0,0.6);">
                        </div>
                        <h2 class="empty-title">Tabersil Chatbots</h2>
                        <p class="empty-desc">Selecciona una conversación en la lista para ver el historial y responder al cliente.</p>
                    </div>
                `;

                if (popHistory && window.location.hash.startsWith("#chat-")) {{
                    history.back();
                }}
                renderizarListaChats();
            }}

            window.addEventListener("popstate", (e) => {{
                if (window.innerWidth <= 768) {{
                    if (!window.location.hash.startsWith("#chat-")) {{
                        volverALista(false);
                    }}
                }}
            }});

            function actualizarBotonIA(isAiPaused) {{
                const btn = document.getElementById("btn-toggle-ia");
                const iconContainer = document.getElementById("ia-icon-container");
                const textContainer = document.getElementById("ia-text-container");
                const statusMeta = document.getElementById("chat-header-status");

                if (isAiPaused) {{
                    iconContainer.innerHTML = lucideIcon('bot-off', {{ size: 14 }});
                    textContainer.innerText = "IA Pausada";
                    btn.className = "btn-toggle-ia paused";
                    statusMeta.className = "chat-header-status";
                    statusMeta.innerHTML = `${{lucideIcon('bot-off', {{ size: 11 }})}} IA Pausada`;
                }} else {{
                    iconContainer.innerHTML = lucideIcon('bot', {{ size: 14 }});
                    textContainer.innerText = "IA Activa";
                    btn.className = "btn-toggle-ia";
                    statusMeta.className = "chat-header-status online";
                    statusMeta.innerHTML = `${{lucideIcon('bot', {{ size: 11 }})}} IA Activa`;
                }}
            }}

            async function cargarHistorial() {{
                if (!clienteActivo) return;
                try {{
                    const response = await fetch(`/admin/historial/${{clienteActivo}}`);
                    if (response.status === 401) {{
                        window.location.href = "/login";
                        return;
                    }}
                    const mensajes = await response.json();
                    const container = document.getElementById("messages-container");
                    
                    let htmlContent = `
                        <div class="chat-info-pill">
                            ${{lucideIcon('lock', {{ size: 12 }})}}
                            <span>Conversación cifrada y gestionada por Tabersil Chatbots</span>
                        </div>
                    `;

                    mensajes.forEach(msg => {{
                        const isAssistant = msg.role === 'assistant';
                        const rowClass = `message-row ${{msg.role}}`;
                        
                        let bubbleClass = "message-bubble";
                        let adminTag = "";
                        if (msg.enviado_por_admin) {{
                            bubbleClass += " admin-sent";
                            adminTag = `<div class="msg-admin-tag">${{lucideIcon('user', {{ size: 10 }})}} Agente</div>`;
                        }}

                        let mediaHtml = "";
                        if (msg.url_media) {{
                            if (msg.es_imagen) {{
                                mediaHtml = `<div class="message-media"><img src="${{msg.url_media}}" alt="Imagen"></div>`;
                            }} else if (msg.es_audio) {{
                                mediaHtml = `<div class="message-media"><audio controls src="${{msg.url_media}}"></audio></div>`;
                            }} else if (msg.es_documento) {{
                                mediaHtml = `<div class="message-media"><a href="${{msg.url_media}}" target="_blank" class="doc-link">${{lucideIcon('file-text', {{ size: 14 }})}} <span>Descargar Documento</span> ${{lucideIcon('download', {{ size: 13 }})}}</a></div>`;
                            }}
                        }}

                        let checkIcon = "";
                        if (isAssistant) {{
                            checkIcon = msg.enviado_por_admin 
                                ? lucideIcon('check-check', {{ size: 13, class: 'msg-check read' }})
                                : lucideIcon('check-check', {{ size: 13, class: 'msg-check' }});
                        }}

                        htmlContent += `
                            <div class="${{rowClass}}">
                                <div class="${{bubbleClass}}">
                                    ${{adminTag}}
                                    ${{mediaHtml}}
                                    <div>${{parsearMarkdownWhatsapp(msg.content)}}</div>
                                    <span class="message-meta">${{msg.timestamp}} ${{checkIcon}}</span>
                                </div>
                            </div>
                        `;
                    }});

                    container.innerHTML = htmlContent;
                    container.scrollTop = container.scrollHeight;
                }} catch (e) {{
                    console.error("Error cargando historial", e);
                }}
            }}

            async function enviarMensaje() {{
                const input = document.getElementById("msg-input");
                const texto = input.value.trim();
                if (!texto || !clienteActivo) return;

                input.value = "";
                try {{
                    const response = await fetch("/admin/enviar", {{
                        method: "POST",
                        headers: {{ "Content-Type": "application/json" }},
                        body: JSON.stringify({{
                            telefono: clienteActivo,
                            mensaje: texto
                        }})
                    }});

                    if (response.status === 401) {{
                        window.location.href = "/login";
                        return;
                    }}

                    if (response.ok) {{
                        cargarHistorial();
                        cargarChats();
                    }}
                }} catch (e) {{
                    console.error("Error al enviar mensaje", e);
                }}
            }}

            async function toggleIA() {{
                if (!clienteActivo) return;
                try {{
                    const response = await fetch("/admin/toggle-ia", {{
                        method: "POST",
                        headers: {{ "Content-Type": "application/json" }},
                        body: JSON.stringify({{ telefono: clienteActivo }})
                    }});

                    if (response.status === 401) {{
                        window.location.href = "/login";
                        return;
                    }}

                    const data = await response.json();
                    actualizarBotonIA(data.is_ai_paused);
                    
                    const item = listaChatsCache.find(c => c.telefono === clienteActivo);
                    if (item) item.is_ai_paused = data.is_ai_paused;
                    renderizarListaChats();
                }} catch (e) {{
                    console.error("Error toggle IA", e);
                }}
            }}

            function handleKeyPress(e) {{
                if (e.key === "Enter") {{
                    enviarMensaje();
                }}
            }}

            // Soporte de instalación PWA
            let deferredPrompt = null;
            window.addEventListener('beforeinstallprompt', (e) => {{
                e.preventDefault();
                deferredPrompt = e;
                const btnInstall = document.getElementById('btn-pwa-install');
                if (btnInstall) {{
                    btnInstall.style.display = 'inline-flex';
                }}
            }});

            async function instalarPWA() {{
                if (!deferredPrompt) return;
                deferredPrompt.prompt();
                const choice = await deferredPrompt.userChoice;
                if (choice && choice.outcome === 'accepted') {{
                    console.log('PWA aceptada por el usuario');
                }}
                deferredPrompt = null;
                const btnInstall = document.getElementById('btn-pwa-install');
                if (btnInstall) {{
                    btnInstall.style.display = 'none';
                }}
            }}

            window.addEventListener('appinstalled', () => {{
                console.log('Tabersil Chatbots CRM instalada como PWA');
                const btnInstall = document.getElementById('btn-pwa-install');
                if (btnInstall) btnInstall.style.display = 'none';
            }});

            if ("{debe_cambiar_pw}" === "false") {{
                cargarChats();
            }}
            setInterval(() => {{
                if ("{debe_cambiar_pw}" === "false") {{
                    cargarChats();
                    if (clienteActivo) cargarHistorial();
                }}
            }}, 3000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.post("/admin/cambiar-password")
async def cambiar_password_endpoint(payload: dict, admin_user: UsuarioAdmin = Depends(obtener_admin_actual)):
    new_password = payload.get("password")
    if not new_password or len(new_password) < 4:
        raise HTTPException(status_code=400, detail="Contraseña inválida (mínimo 4 caracteres)")
    
    await actualizar_password(admin_user.username, new_password)
    return {"status": "ok", "message": "Contraseña actualizada con éxito"}


@app.get("/admin/chats")
async def obtener_chats(admin_user: UsuarioAdmin = Depends(obtener_admin_actual)):
    """Retorna los chats con actividad."""
    chats = await obtener_chats_activos()
    return chats


@app.get("/admin/historial/{telefono}")
async def obtener_historial_chat(telefono: str, admin_user: UsuarioAdmin = Depends(obtener_admin_actual)):
    """Retorna el historial completo del chat seleccionado."""
    historial = await obtener_historial(telefono, limite=1000)
    return historial


@app.post("/admin/enviar")
async def enviar_mensaje_admin(payload: dict, admin_user: UsuarioAdmin = Depends(obtener_admin_actual)):
    """Envía un mensaje manual por WhatsApp y lo registra con flag de admin."""
    telefono = payload.get("telefono")
    mensaje = payload.get("mensaje")

    if not telefono or not mensaje:
        raise HTTPException(status_code=400, detail="Faltan parámetros")

    # Guardar en base de datos inmediatamente
    await guardar_mensaje(
        telefono=telefono,
        role="assistant",
        content=mensaje,
        enviado_por_admin=True
    )

    # Enviar vía Twilio/Meta
    enviado = await proveedor.enviar_mensaje(telefono, mensaje)
    if not enviado:
        raise HTTPException(status_code=502, detail="Error al enviar mensaje por el proveedor de WhatsApp")

    return {"status": "ok"}


@app.post("/admin/toggle-ia")
async def toggle_ia_chat(payload: dict, admin_user: UsuarioAdmin = Depends(obtener_admin_actual)):
    """Cambia el estado de pausa de la IA para una conversación."""
    telefono = payload.get("telefono")
    if not telefono:
        raise HTTPException(status_code=400, detail="Falta el teléfono")

    estado_actual = await obtener_estado_chat(telefono)
    nuevo_estado = not estado_actual
    await actualizar_estado_chat(telefono, nuevo_estado)

    return {"status": "ok", "is_ai_paused": nuevo_estado}
