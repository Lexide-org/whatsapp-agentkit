# agent/providers/meta.py — Adaptador para Meta WhatsApp Cloud API
# Generado por AgentKit

import os
import logging
import httpx
from fastapi import Request
from agent.providers.base import ProveedorWhatsApp, MensajeEntrante

logger = logging.getLogger("agentkit")


class ProveedorMeta(ProveedorWhatsApp):
    """Proveedor de WhatsApp usando la API oficial de Meta (Cloud API)."""

    def __init__(self):
        self.access_token = os.getenv("META_ACCESS_TOKEN")
        self.phone_number_id = os.getenv("META_PHONE_NUMBER_ID")
        self.verify_token = os.getenv("META_VERIFY_TOKEN", "agentkit-verify")
        self.api_version = "v21.0"

    async def validar_webhook(self, request: Request) -> dict | int | None:
        """Meta requiere verificación GET con hub.verify_token."""
        params = request.query_params
        mode = params.get("hub.mode")
        token = params.get("hub.verify_token")
        challenge = params.get("hub.challenge")
        if mode == "subscribe" and token == self.verify_token:
            return int(challenge)
        return None

    async def parsear_webhook(self, request: Request) -> list[MensajeEntrante]:
        """Parsea el payload anidado de Meta Cloud API."""
        body = await request.json()
        mensajes = []
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):
                    tipo = msg.get("type")
                    telefono = msg.get("from", "")
                    mensaje_id = msg.get("id", "")
                    
                    texto = ""
                    url_media = None
                    es_imagen = False
                    es_audio = False
                    es_documento = False
                    
                    if tipo == "text":
                        texto = msg.get("text", {}).get("body", "")
                    elif tipo in ["image", "audio", "document"]:
                        media_obj = msg.get(tipo, {})
                        media_id = media_obj.get("id")
                        url_media = f"https://graph.facebook.com/v21.0/{media_id}"
                        
                        if tipo == "image":
                            es_imagen = True
                            texto = media_obj.get("caption", "[Imagen recibida]")
                            if not texto:
                                texto = "[Imagen recibida]"
                        elif tipo == "audio":
                            es_audio = True
                            texto = "[Nota de voz recibida]"
                        else:
                            es_documento = True
                            texto = media_obj.get("filename", "[Documento recibido]")
                            if not texto:
                                texto = "[Documento recibido]"
                    
                    if texto or url_media:
                        mensajes.append(MensajeEntrante(
                            telefono=telefono,
                            texto=texto,
                            mensaje_id=mensaje_id,
                            es_propio=False,
                            url_media=url_media,
                            es_imagen=es_imagen,
                            es_audio=es_audio,
                            es_documento=es_documento
                        ))
        return mensajes

    async def enviar_mensaje(self, telefono: str, mensaje: str) -> bool:
        """Envía mensaje via Meta WhatsApp Cloud API."""
        if not self.access_token or not self.phone_number_id:
            logger.warning("META_ACCESS_TOKEN o META_PHONE_NUMBER_ID no configurados")
            return False
        url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": telefono,
            "type": "text",
            "text": {"body": mensaje},
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(url, json=payload, headers=headers)
            if r.status_code != 200:
                logger.error(f"Error Meta API: {r.status_code} — {r.text}")
            return r.status_code == 200
