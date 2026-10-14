// server/providers/index.js — Factoría del proveedor de WhatsApp
import { TwilioProvider } from './twilio.js';
import { MetaProvider } from './meta.js';

export function getWhatsAppProvider() {
  const envProvider = (process.env.WHATSAPP_PROVIDER || '').toLowerCase();

  if (envProvider === 'meta') {
    return new MetaProvider();
  }

  if (envProvider === 'twilio') {
    return new TwilioProvider();
  }

  // Si no se especifica WHATSAPP_PROVIDER, inferir según las credenciales presentes:
  if (process.env.TWILIO_ACCOUNT_SID) {
    return new TwilioProvider();
  }

  if (process.env.META_ACCESS_TOKEN) {
    return new MetaProvider();
  }

  // Por defecto usar Twilio
  return new TwilioProvider();
}
