// server/providers/twilio.js — Adaptador de WhatsApp para Twilio
export class TwilioProvider {
  constructor() {
    this.accountSid = process.env.TWILIO_ACCOUNT_SID;
    this.authToken = process.env.TWILIO_AUTH_TOKEN;
    this.phoneNumber = process.env.TWILIO_PHONE_NUMBER;
  }

  /**
   * Parsea el webhook entrante de Twilio (form-data / urlencoded).
   */
  async parseWebhook(body) {
    const rawFrom = body.From || '';
    const telefono = rawFrom.replace('whatsapp:', '').trim();
    let texto = body.Body || '';
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
      console.warn('⚠️ Variables de Twilio no configuradas en .env');
      return false;
    }

    const url = `https://api.twilio.com/2010-04-01/Accounts/${this.accountSid}/Messages.json`;
    const auth = Buffer.from(`${this.accountSid}:${this.authToken}`).toString('base64');

    const params = new URLSearchParams();
    params.append('From', `whatsapp:${this.phoneNumber}`);
    params.append('To', `whatsapp:${telefono}`);
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

      return true;
    } catch (err) {
      console.error('❌ Excepción al enviar mensaje con Twilio:', err);
      return false;
    }
  }
}
