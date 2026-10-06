// scripts/test-chat.js — Simulador interactivo de chat en terminal (WhatsApp Simulator)
import 'dotenv/config';
import readline from 'node:readline';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';

const PORT = process.env.PORT || 8000;
const WEBHOOK_URL = `http://localhost:${PORT}/webhook`;
const DB_PATH = process.env.DATABASE_FILE || path.resolve(process.cwd(), 'agentkit.db');
const PROVIDER = (process.env.WHATSAPP_PROVIDER || 'meta').toLowerCase();
const DEFAULT_PHONE = (process.env.TEST_PHONE || '584121234567').replace(/^\+/, '');

let db = null;
try {
  db = new DatabaseSync(DB_PATH);
} catch (err) {
  console.warn('⚠️ No se pudo conectar directamente a agentkit.db:', err.message);
}

function getLatestMessageId(phone) {
  if (!db) return 0;
  try {
    const row = db.prepare('SELECT MAX(id) as maxId FROM mensajes WHERE telefono = ? OR telefono = ?')
      .get(phone, `+${phone}`);
    return row?.maxId || 0;
  } catch {
    return 0;
  }
}

function getNewMessages(phone, afterId) {
  if (!db) return [];
  try {
    const rows = db.prepare(`
      SELECT id, role, content, enviado_por_admin, timestamp 
      FROM mensajes 
      WHERE (telefono = ? OR telefono = ?) AND id > ?
      ORDER BY id ASC
    `).all(phone, `+${phone}`, afterId);
    return rows || [];
  } catch {
    return [];
  }
}

async function sendWebhookMessage(phone, text) {
  let payload;

  if (PROVIDER === 'meta') {
    payload = {
      object: 'whatsapp_business_account',
      entry: [
        {
          id: 'meta_sim_account',
          changes: [
            {
              value: {
                messaging_product: 'whatsapp',
                metadata: {
                  display_phone_number: '15551234567',
                  phone_number_id: 'meta_sim_phone_id'
                },
                messages: [
                  {
                    from: phone,
                    id: `wamid.sim_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
                    type: 'text',
                    text: { body: text }
                  }
                ]
              },
              field: 'messages'
            }
          ]
        }
      ]
    };
  } else {
    payload = {
      From: `whatsapp:+${phone}`,
      Body: text,
      MessageSid: `sim_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`
    };
  }

  const response = await fetch(WEBHOOK_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`Servidor respondió con código ${response.status}`);
  }
  return response.json();
}

async function startSimulator() {
  console.log('\n============================================================');
  console.log('   💬 Simulador de Cliente WhatsApp — Tabersil Chatbots');
  console.log('============================================================');
  console.log(`📱 Teléfono de prueba: ${DEFAULT_PHONE}`);
  console.log(`📡 Conectado al webhook: ${WEBHOOK_URL}`);
  console.log('💻 Panel CRM web: http://localhost:5173');
  console.log('------------------------------------------------------------');
  console.log('Escribe tus mensajes como si fueras un cliente en WhatsApp.');
  console.log('Escribe "salir" para terminar o "limpiar" para borrar este chat.');
  console.log('============================================================\n');

  // Verificar conexión con el servidor
  try {
    const check = await fetch(WEBHOOK_URL);
    if (!check.ok) {
      console.warn('⚠️ El servidor no respondió adecuadamente en /webhook.');
    }
  } catch {
    console.error('❌ No se pudo conectar al servidor en http://localhost:8000.');
    console.error('👉 Asegúrate de tener el servidor corriendo con: npm run dev\n');
    process.exit(1);
  }

  let lastSeenId = getLatestMessageId(DEFAULT_PHONE);

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: '\x1b[36mTú:\x1b[0m '
  });

  // Tarea de monitoreo en segundo plano (para capturar respuestas del CRM en tiempo real)
  const monitorInterval = setInterval(() => {
    const newMsgs = getNewMessages(DEFAULT_PHONE, lastSeenId);
    for (const msg of newMsgs) {
      lastSeenId = Math.max(lastSeenId, msg.id);
      if (msg.role === 'assistant') {
        const remitente = msg.enviado_por_admin ? '👤 Asesor (desde CRM)' : '🤖 Asistente (IA)';
        const color = msg.enviado_por_admin ? '\x1b[33m' : '\x1b[32m';
        console.log(`\n${color}${remitente}:\x1b[0m ${msg.content}\n`);
        rl.prompt();
      }
    }
  }, 1000);

  rl.prompt();

  rl.on('line', async (line) => {
    const input = line.trim();
    if (!input) {
      rl.prompt();
      return;
    }

    if (input.toLowerCase() === 'salir') {
      clearInterval(monitorInterval);
      rl.close();
      console.log('\n👋 Simulador cerrado. ¡Hasta luego!\n');
      process.exit(0);
    }

    if (input.toLowerCase() === 'limpiar') {
      if (db) {
        db.prepare('DELETE FROM mensajes WHERE telefono = ?').run(DEFAULT_PHONE);
        db.prepare('DELETE FROM chat_status WHERE telefono = ?').run(DEFAULT_PHONE);
        lastSeenId = 0;
        console.log('🧹 Conversación borrada para el número de prueba.\n');
      }
      rl.prompt();
      return;
    }

    try {
      await sendWebhookMessage(DEFAULT_PHONE, input);
      // El monitorInterval detectará la respuesta en ~1 segundo
    } catch (err) {
      console.error(`\n❌ Error enviando mensaje: ${err.message}\n`);
      rl.prompt();
    }
  });

  rl.on('close', () => {
    clearInterval(monitorInterval);
    process.exit(0);
  });
}

startSimulator();
