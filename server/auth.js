// server/auth.js — Sistema de autenticación con sesiones firmadas HMAC-SHA256
import crypto from 'node:crypto';
import { getAdminByUsername } from './db.js';

const SECRET_KEY = Buffer.from(process.env.SECRET_KEY || 'agentkit_secret_key_crm_2026_change_in_production', 'utf-8');
export const COOKIE_NAME = 'agentkit_session';

/**
 * Crea un token firmado HMAC-SHA256 con validez de 7 días.
 */
export function createSessionToken(username, hours = 168) {
  const exp = Math.floor(Date.now() / 1000) + hours * 3600;
  const payload = {
    sub: username,
    exp,
    iat: Math.floor(Date.now() / 1000)
  };

  const payloadB64 = Buffer.from(JSON.stringify(payload), 'utf-8')
    .toString('base64url');

  const hmac = crypto.createHmac('sha256', SECRET_KEY);
  hmac.update(payloadB64);
  const signature = hmac.digest('hex');

  return `${payloadB64}.${signature}`;
}

/**
 * Verifica la firma y vigencia del token de sesión.
 */
export function verifySessionToken(token) {
  if (!token || !token.includes('.')) return null;

  try {
    const [payloadB64, signature] = token.split('.');
    if (!payloadB64 || !signature) return null;

    const hmac = crypto.createHmac('sha256', SECRET_KEY);
    hmac.update(payloadB64);
    const expectedSignature = hmac.digest('hex');

    // Comparación segura en tiempo constante
    const sigBuffer = Buffer.from(signature, 'utf-8');
    const expectedBuffer = Buffer.from(expectedSignature, 'utf-8');

    if (sigBuffer.length !== expectedBuffer.length || !crypto.timingSafeEqual(sigBuffer, expectedBuffer)) {
      return null;
    }

    const jsonStr = Buffer.from(payloadB64, 'base64url').toString('utf-8');
    const payload = JSON.parse(jsonStr);

    if (payload.exp && payload.exp < Math.floor(Date.now() / 1000)) {
      return null; // Expirado
    }

    return payload.sub;
  } catch (err) {
    return null;
  }
}

/**
 * Middleware para rutas protegidas del CRM.
 */
export function requireAdmin(req, res, next) {
  let token = req.cookies?.[COOKIE_NAME];

  if (!token && req.headers.authorization?.startsWith('Bearer ')) {
    token = req.headers.authorization.split(' ')[1].trim();
  }

  if (!token) {
    return res.status(401).json({ detail: 'Sesión no iniciada o expirada' });
  }

  const username = verifySessionToken(token);
  if (!username) {
    return res.status(401).json({ detail: 'Sesión inválida o expirada' });
  }

  const admin = getAdminByUsername(username);
  if (!admin) {
    return res.status(401).json({ detail: 'Usuario no encontrado' });
  }

  req.user = admin;
  next();
}
