// server/providers/meta.js — Adaptador de WhatsApp para Meta Cloud API
export class MetaProvider {
  constructor() {
    this.accessToken = process.env.META_ACCESS_TOKEN;
    this.phoneNumberId = process.env.META_PHONE_NUMBER_ID;
    this.verifyToken = process.env.META_VERIFY_TOKEN || 'agentkit-verify';
    this.apiVersion = 'v21.0';
  }

  /**
   * Meta requiere verificación GET con hub.challenge.
   */
  validateWebhook(query) {
    const mode = query['hub.mode'];
    const token = query['hub.verify_token'];
    const challenge = query['hub.challenge'];

    if (mode === 'subscribe' && token === this.verifyToken) {
      return challenge;
    }
    return null;
  }

  /**
   * Parsea el webhook entrante de Meta Cloud API (JSON anidado).
   */
  async parseWebhook(body) {
    const mensajes = [];
    const entries = body?.entry || [];

    for (const entry of entries) {
      for (const change of entry.changes || []) {
        const value = change.value || {};
        for (const msg of value.messages || []) {
          const tipo = msg.type;
          const telefono = msg.from || '';
          const mensajeId = msg.id || null;

          let texto = '';
          let urlMedia = null;
          let esImagen = false;
          let esAudio = false;
          let esDocumento = false;

          if (tipo === 'text') {
            texto = msg.text?.body || '';
          } else if (['image', 'audio', 'document'].includes(tipo)) {
            const mediaObj = msg[tipo] || {};
            const mediaId = mediaObj.id;
            urlMedia = `https://graph.facebook.com/${this.apiVersion}/${mediaId}`;

            if (tipo === 'image') {
              esImagen = true;
              texto = mediaObj.caption || '[Imagen recibida]';
            } else if (tipo === 'audio') {
              esAudio = true;
              texto = '[Nota de voz recibida]';
            } else {
              esDocumento = true;
              texto = mediaObj.filename || '[Documento recibido]';
            }
          }

          if (texto || urlMedia) {
            mensajes.push({
              telefono,
              texto,
              mensajeId,
              urlMedia,
              esImagen,
              esAudio,
              esDocumento,
              esPropio: false
            });
          }
        }
      }
    }

    return mensajes;
  }

  /**
   * Envía un mensaje de texto a través de Meta Graph API.
   */
  async sendMessage(telefono, mensaje) {
    if (!this.accessToken || !this.phoneNumberId) {
      console.warn('⚠️ META_ACCESS_TOKEN o META_PHONE_NUMBER_ID no configurados');
      return false;
    }

    const url = `https://graph.facebook.com/${this.apiVersion}/${this.phoneNumberId}/messages`;

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.accessToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          messaging_product: 'whatsapp',
          to: telefono,
          type: 'text',
          text: { body: mensaje }
        })
      });

      if (!res.ok) {
        const errText = await res.text();
        console.error(`❌ Error Meta API ${res.status}:`, errText);
        return false;
      }

      return true;
    } catch (err) {
      console.error('❌ Excepción al enviar mensaje con Meta:', err);
      return false;
    }
  }
}
