// server/index.js — Servidor Express para Tabersil Chatbots
import 'dotenv/config';
import express from 'express';
import cookieParser from 'cookie-parser';
import cors from 'cors';
import path from 'node:path';
import fs from 'node:fs';

import {
  initDb,
  verifyAdminCredentials,
  getAdminByUsername,
  updateAdminPassword,
  isMessageDuplicate,
  isChatAiPaused,
  setChatAiPaused,
  saveMessage,
  getChatHistory,
  getActiveChats
} from './db.js';

import {
  createSessionToken,
  requireAdmin,
  COOKIE_NAME,
  verifySessionToken
} from './auth.js';

import { generateAiReply } from './brain.js';
import { getWhatsAppProvider } from './providers/index.js';

// Inicializar base de datos (PostgreSQL o SQLite)
await initDb();

const app = express();
const PORT = parseInt(process.env.PORT || '8000', 10);
const provider = getWhatsAppProvider();

// Middlewares estándar
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(cookieParser());

// Archivos estáticos de imágenes (logos, favicons, etc.)
app.use('/images', express.static(path.resolve(process.cwd(), 'images')));

// -------------------------------------------------------------
// PWA: Manifiesto Web App
// -------------------------------------------------------------
app.get('/manifest.json', (req, res) => {
  res.setHeader('Content-Type', 'application/manifest+json');
  res.json({
    name: 'Tabersil Chatbots',
    short_name: 'Tabersil',
    description: 'Panel CRM y Asistente IA de WhatsApp — Tabersil Studios',
    start_url: '/admin',
    scope: '/',
    display: 'standalone',
    background_color: '#000000',
    theme_color: '#000000',
    orientation: 'portrait-primary',
    icons: [
      {
        src: '/images/favicon.png',
        sizes: '64x64',
        type: 'image/png'
      },
      {
        src: '/images/icon-192.png',
        sizes: '192x192',
        type: 'image/png',
        purpose: 'any maskable'
      },
      {
        src: '/images/icon-512.png',
        sizes: '512x512',
        type: 'image/png',
        purpose: 'any maskable'
      }
    ]
  });
});

// -------------------------------------------------------------
// PWA: Service Worker
// -------------------------------------------------------------
app.get('/sw.js', (req, res) => {
  res.setHeader('Content-Type', 'application/javascript');
  res.setHeader('Service-Worker-Allowed', '/');
  res.send(`
    const CACHE_NAME = 'tabersil-chatbots-v2';
    const PRECACHE_URLS = [
      '/',
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
  `);
});

// -------------------------------------------------------------
// Webhooks de WhatsApp (Twilio / Meta)
// -------------------------------------------------------------
app.get('/webhook', (req, res) => {
  if (typeof provider.validateWebhook === 'function') {
    const challenge = provider.validateWebhook(req.query);
    if (challenge !== null && challenge !== undefined) {
      return res.send(String(challenge));
    }
  }
  return res.json({ status: 'ok', service: 'tabersil-chatbots' });
});

app.post('/webhook', async (req, res) => {
  try {
    const body = req.body;
    const mensajes = await provider.parseWebhook(body);

    for (const msg of mensajes) {
      if (msg.esPropio) continue;

      // 1. Deduplicación
      if (msg.mensajeId && (await isMessageDuplicate(msg.mensajeId))) {
        console.log(`⚠️ Mensaje duplicado omitido: ${msg.mensajeId}`);
        continue;
      }

      console.log(`📩 Mensaje entrante de ${msg.telefono}: "${msg.texto}"`);

      // 2. Guardar mensaje del cliente
      await saveMessage({
        telefono: msg.telefono,
        role: 'user',
        content: msg.texto,
        mensajeId: msg.mensajeId,
        urlMedia: msg.urlMedia,
        esImagen: msg.esImagen,
        esAudio: msg.esAudio,
        esDocumento: msg.esDocumento,
        enviadoPorAdmin: false
      });

      // 3. Comprobar si la IA está pausada para este chat
      const isPaused = await isChatAiPaused(msg.telefono);
      if (isPaused) {
        console.log(`⏸️ IA en pausa para ${msg.telefono}. Registrado en CRM sin respuesta automática.`);
        continue;
      }

      // 4. Obtener historial para contexto de Gemini
      const historial = await getChatHistory(msg.telefono, 30);

      // 5. Generar respuesta con Gemini
      const respuestaIA = await generateAiReply(msg.texto, historial);

      // 6. Guardar respuesta del asistente
      await saveMessage({
        telefono: msg.telefono,
        role: 'assistant',
        content: respuestaIA,
        enviadoPorAdmin: false
      });

      // 7. Enviar respuesta por WhatsApp
      await provider.sendMessage(msg.telefono, respuestaIA);
    }

    return res.json({ status: 'ok' });
  } catch (err) {
    console.error('❌ Error procesando webhook:', err);
    return res.status(500).json({ error: 'Error procesando webhook' });
  }
});

// -------------------------------------------------------------
// Autenticación API
// -------------------------------------------------------------
app.post('/api/login', async (req, res) => {
  const { username, password } = req.body || {};
  if (!username || !password) {
    return res.status(400).json({ detail: 'Faltan credenciales' });
  }

  const user = await verifyAdminCredentials(username, password);
  if (!user) {
    return res.status(401).json({ detail: 'Usuario o contraseña incorrectos' });
  }

  const token = createSessionToken(user.username);
  res.cookie(COOKIE_NAME, token, {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    maxAge: 7 * 24 * 3600 * 1000,
    path: '/'
  });

  return res.json({
    status: 'ok',
    redirect: '/admin',
    user: {
      username: user.username,
      debe_cambiar_password: user.debe_cambiar_password
    }
  });
});

app.post('/login', async (req, res) => {
  const { username, password } = req.body || {};
  const user = await verifyAdminCredentials(username, password);
  if (!user) {
    return res.redirect('/login?error=1');
  }

  const token = createSessionToken(user.username);
  res.cookie(COOKIE_NAME, token, {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    maxAge: 7 * 24 * 3600 * 1000,
    path: '/'
  });

  return res.redirect('/admin');
});

app.get('/api/me', async (req, res) => {
  const token = req.cookies?.[COOKIE_NAME];
  if (!token) {
    return res.status(401).json({ detail: 'No autenticado' });
  }
  const username = verifySessionToken(token);
  if (!username) {
    return res.status(401).json({ detail: 'Sesión expirada' });
  }
  const user = await getAdminByUsername(username);
  if (!user) {
    return res.status(401).json({ detail: 'Usuario no encontrado' });
  }
  return res.json({
    username: user.username,
    debe_cambiar_password: user.debe_cambiar_password
  });
});

app.all(['/logout', '/api/logout'], (req, res) => {
  res.clearCookie(COOKIE_NAME, { path: '/' });
  if (req.path === '/api/logout') {
    return res.json({ status: 'ok' });
  }
  return res.redirect('/login');
});

// -------------------------------------------------------------
// Rutas del CRM (Protegidas) — Compatibles con Frontend React
// -------------------------------------------------------------
app.get(['/admin/chats', '/api/chats'], requireAdmin, async (req, res) => {
  const chats = await getActiveChats();
  res.json(chats);
});

app.get(['/admin/historial/:telefono', '/api/historial/:telefono'], requireAdmin, async (req, res) => {
  const { telefono } = req.params;
  const historial = await getChatHistory(telefono, 1000);
  res.json(historial);
});

app.post(['/admin/enviar', '/api/enviar'], requireAdmin, async (req, res) => {
  const { telefono, mensaje } = req.body || {};
  if (!telefono || !mensaje) {
    return res.status(400).json({ detail: 'Faltan parámetros' });
  }

  // Guardar mensaje manual del asesor en la base de datos
  await saveMessage({
    telefono,
    role: 'assistant',
    content: mensaje,
    enviadoPorAdmin: true
  });

  // Enviar mensaje por el proveedor de WhatsApp (Twilio / Meta)
  const enviado = await provider.sendMessage(telefono, mensaje);
  if (!enviado) {
    return res.status(502).json({ detail: 'Error al enviar por el proveedor de WhatsApp' });
  }

  return res.json({ status: 'ok' });
});

app.post(['/admin/toggle-ia', '/api/toggle-ia'], requireAdmin, async (req, res) => {
  const { telefono } = req.body || {};
  if (!telefono) {
    return res.status(400).json({ detail: 'Falta el teléfono' });
  }

  const estadoActual = await isChatAiPaused(telefono);
  const nuevoEstado = !estadoActual;
  await setChatAiPaused(telefono, nuevoEstado);

  return res.json({ status: 'ok', is_ai_paused: nuevoEstado });
});

app.post(['/admin/cambiar-password', '/api/cambiar-password'], requireAdmin, async (req, res) => {
  const { password } = req.body || {};
  if (!password || password.length < 4) {
    return res.status(400).json({ detail: 'Contraseña inválida (mínimo 4 caracteres)' });
  }

  await updateAdminPassword(req.user.username, password);
  return res.json({ status: 'ok', message: 'Contraseña actualizada con éxito' });
});

// -------------------------------------------------------------
// Servir la aplicación React (Single Page Application)
// -------------------------------------------------------------
const distPath = path.resolve(process.cwd(), 'dist');

if (fs.existsSync(distPath)) {
  app.use(express.static(distPath));
  app.get('*', (req, res) => {
    if (req.path.startsWith('/api/') || req.path.startsWith('/webhook')) {
      return res.status(404).json({ error: 'Endpoint no encontrado' });
    }
    res.sendFile(path.resolve(distPath, 'index.html'));
  });
} else {
  // Modo inicial si aún no se ha compilado Vite
  app.get(['/', '/admin', '/login'], (req, res) => {
    res.send(`
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <title>Tabersil Chatbots</title>
        <style>
          body { background: #000; color: #fff; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        </style>
      </head>
      <body>
        <div style="text-align: center;">
          <h2>Tabersil Chatbots — Servidor Node.js Activo</h2>
          <p>Compilando frontend React... Por favor espera unos momentos o ejecuta <code>npm run build</code>.</p>
        </div>
      </body>
      </html>
    `);
  });
}

// Iniciar servidor
app.listen(PORT, () => {
  console.log(`🚀 Servidor Tabersil Chatbots (Node.js) corriendo en http://127.0.0.1:${PORT}`);
  console.log(`📡 Proveedor de WhatsApp: ${process.env.WHATSAPP_PROVIDER || 'twilio'}`);
});
