# agent/auth.py — Sistema de autenticación robusto basado en sesiones firmadas
# Generado por AgentKit

import os
import hmac
import hashlib
import base64
import json
import time
import logging
from fastapi import Request, HTTPException, status
from agent.memory import obtener_usuario_admin, UsuarioAdmin

logger = logging.getLogger("agentkit")

SECRET_KEY = os.getenv("SECRET_KEY", "agentkit_secret_key_crm_2026_change_in_production").encode("utf-8")
COOKIE_NAME = "agentkit_session"


def crear_token_sesion(username: str, horas_validez: int = 168) -> str:
    """
    Crea un token de sesión firmado criptográficamente con HMAC-SHA256.
    Por defecto dura 7 días (168 horas).
    """
    expira_en = int(time.time()) + (horas_validez * 3600)
    payload = {
        "sub": username,
        "exp": expira_en,
        "iat": int(time.time())
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8").rstrip("=")
    firma = hmac.new(SECRET_KEY, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{firma}"


def verificar_token_sesion(token: str) -> str | None:
    """
    Verifica la autenticidad y vigencia de un token de sesión.
    Retorna el nombre de usuario si es válido, o None si expiró o fue manipulado.
    """
    if not token or "." not in token:
        return None
    try:
        partes = token.split(".")
        if len(partes) != 2:
            return None
        payload_b64, firma = partes
        firma_esperada = hmac.new(SECRET_KEY, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        
        # Comparación en tiempo constante contra ataques de timing
        if not hmac.compare_digest(firma, firma_esperada):
            return None

        # Rellenar padding base64 si fue recortado
        padding_necesario = 4 - (len(payload_b64) % 4)
        if padding_necesario and padding_necesario != 4:
            payload_b64 += "=" * padding_necesario

        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8"))
        
        # Validar expiración
        if payload.get("exp", 0) < time.time():
            return None

        return payload.get("sub")
    except Exception as e:
        logger.warning(f"Error verificando token de sesión: {e}")
        return None


async def obtener_admin_opcional(request: Request) -> UsuarioAdmin | None:
    """
    Obtiene el usuario administrador actual a partir de la cookie de sesión
    o el header Authorization (Bearer). Retorna None si no está autenticado.
    """
    token = request.cookies.get(COOKIE_NAME)
    
    # También soportar Bearer token en headers si se usa por API
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()

    if not token:
        return None

    username = verificar_token_sesion(token)
    if not username:
        return None

    return await obtener_usuario_admin(username)


async def obtener_admin_actual(request: Request) -> UsuarioAdmin:
    """
    Dependencia de FastAPI para endpoints protegidos.
    Lanza HTTPException 401 SIN cabecera WWW-Authenticate para evitar la ventana nativa del navegador.
    """
    user = await obtener_admin_opcional(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión no iniciada o expirada"
        )
    return user
