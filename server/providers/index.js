// server/providers/index.js — Factoría del proveedor de WhatsApp
import { TwilioProvider } from './twilio.js';
import { MetaProvider } from './meta.js';

export function getWhatsAppProvider() {
  const providerType = (process.env.WHATSAPP_PROVIDER || 'twilio').toLowerCase();

  if (providerType === 'meta') {
    return new MetaProvider();
  }

  return new TwilioProvider();
}
