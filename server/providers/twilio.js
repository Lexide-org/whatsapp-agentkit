// server/providers/twilio.js — Adaptador de WhatsApp para Twilio
export class TwilioProvider {
  constructor() {
    this.name = 'twilio';
    this.accountSid = process.env.TWILIO_ACCOUNT_SID;
    this.authToken = process.env.TWILIO_AUTH_TOKEN;
    this.phoneNumber = process.env.TWILIO_PHONE_NUMBER;
  }

  /**
   * Respuesta estándar esperada por Twilio para confirmar recepción de webhook.
   */
  sendWebhookResponse(res) {
    res.setHeader('Content-Type', 'text/xml');
    return res.status(200).send('<Response></Response>');
  }

  /**
   * Validación GET (Twilio no la requiere, pero previene errores).
   */
  validateWebhook() {
    return null;
  }

  /**
   * Parsea el webhook entrante de Twilio (form-data / urlencoded / json).
   */
  async parseWebhook(body) {
    if (!body || typeof body !== 'object') {
      return [];
    }

    // Si es un callback de estado de entrega de Twilio (sent, delivered, read, etc.), ignorar
    if (body.MessageStatus && !body.Body && (!body.NumMedia || body.NumMedia === '0')) {
      return [];
    }

    const rawFrom = body.From || '';
    let telefono = rawFrom.replace('whatsapp:', '').trim();
    if (telefono && !telefono.startsWith('+')) {
      telefono = `+${telefono}`;
    }

    let texto = (body.Body || '').trim();
    const mensajeId = body.MessageSid || null;

    let urlMedia = null;
    let esImagen = false;
    let esAudio = false;
    let esDocumento = false;

    const numMedia = parseInt(body.NumMedia || '0', 10);
    if (numMedia > 0) {
      urlMedia = body.MediaUrl0 || null;
      const contentType = (body.MediaContentType0 || '').toLowerCase();

      if (contentType.startsWith('image/')) {
        esImagen = true;
      } else if (contentType.startsWith('audio/')) {
        esAudio = true;
      } else {
        esDocumento = true;
      }

      if (!texto) {
        if (esImagen) texto = '[Imagen recibida]';
        else if (esAudio) texto = '[Nota de voz recibida]';
        else texto = '[Documento recibido]';
      }
    }

    if (!texto && numMedia === 0) {
      return [];
    }

    return [{
      telefono,
      texto,
      mensajeId,
      urlMedia,
      esImagen,
      esAudio,
      esDocumento,
      esPropio: false
    }];
  }

  /**
   * Envía un mensaje de texto por WhatsApp a través de la API de Twilio.
   */
  async sendMessage(telefono, mensaje) {
    if (!this.accountSid || !this.authToken || !this.phoneNumber) {
      console.warn('⚠️ Variables de Twilio no configuradas en el entorno (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER)');
      return false;
    }

    const url = `https://api.twilio.com/2010-04-01/Accounts/${this.accountSid}/Messages.json`;
    const auth = Buffer.from(`${this.accountSid}:${this.authToken}`).toString('base64');

    // Normalizar emisor (From)
    let cleanFromNumber = this.phoneNumber.replace('whatsapp:', '').trim();
    if (!cleanFromNumber.startsWith('+')) {
      cleanFromNumber = `+${cleanFromNumber}`;
    }
    const from = `whatsapp:${cleanFromNumber}`;

    // Normalizar receptor (To)
    let cleanToNumber = telefono.replace('whatsapp:', '').trim();
    if (!cleanToNumber.startsWith('+')) {
      cleanToNumber = `+${cleanToNumber}`;
    }
    const to = `whatsapp:${cleanToNumber}`;

    const params = new URLSearchParams();
    params.append('From', from);
    params.append('To', to);
    params.append('Body', mensaje);

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${auth}`,
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: params.toString()
      });

      if (!res.ok) {
        const errorText = await res.text();
        console.error(`❌ Error Twilio ${res.status}:`, errorText);
        return false;
      }

      const data = await res.json();
      console.log(`✅ Mensaje de Twilio enviado con éxito a ${to} (SID: ${data.sid})`);
      return true;
    } catch (err) {
      console.error('❌ Excepción al enviar mensaje con Twilio:', err);
      return false;
    }
  }
}
