// server/db.js — Gestión de base de datos híbrida (PostgreSQL en producción / SQLite en local)
import { DatabaseSync } from 'node:sqlite';
import pg from 'pg';
import bcrypt from 'bcryptjs';
import path from 'node:path';

const { Pool } = pg;

const rawDbUrl = (process.env.DATABASE_URL || '').trim();
// Detectar si la URL corresponde a PostgreSQL
export const isPostgres = rawDbUrl.startsWith('postgres://') || rawDbUrl.startsWith('postgresql://');

let pgPool = null;
let sqliteDb = null;

if (isPostgres) {
  // Conexión a PostgreSQL (Railway / Producción)
  pgPool = new Pool({
    connectionString: rawDbUrl,
    ssl: rawDbUrl.includes('localhost') ? false : { rejectUnauthorized: false }
  });
  console.log('🐘 Modo de base de datos: PostgreSQL (producción / Railway)');
} else {
  // Conexión a SQLite nativo (Desarrollo local)
  const DB_PATH = process.env.DATABASE_FILE || path.resolve(process.cwd(), 'agentkit.db');
  sqliteDb = new DatabaseSync(DB_PATH);
  console.log(`📦 Modo de base de datos: SQLite nativo (${DB_PATH})`);
}

/**
 * Inicializa las tablas en la base de datos (PostgreSQL o SQLite) y asegura el admin.
 */
export async function initDb() {
  const initialAdminPassword = process.env.ADMIN_PASSWORD || 'admin';

  if (isPostgres) {
    await pgPool.query(`
      CREATE TABLE IF NOT EXISTS usuarios_admin (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        debe_cambiar_password INTEGER DEFAULT 1
      );

      CREATE TABLE IF NOT EXISTS chat_status (
        telefono VARCHAR(50) PRIMARY KEY,
        is_ai_paused INTEGER DEFAULT 0,
        ultima_actividad VARCHAR(50)
      );

      CREATE TABLE IF NOT EXISTS mensajes (
        id SERIAL PRIMARY KEY,
        telefono VARCHAR(50) NOT NULL,
        mensaje_id VARCHAR(150) UNIQUE,
        role VARCHAR(20) NOT NULL,
        content TEXT NOT NULL,
        timestamp VARCHAR(50) NOT NULL,
        url_media TEXT,
        es_imagen INTEGER DEFAULT 0,
        es_audio INTEGER DEFAULT 0,
        es_documento INTEGER DEFAULT 0,
        enviado_por_admin INTEGER DEFAULT 0
      );

      CREATE INDEX IF NOT EXISTS ix_mensajes_telefono ON mensajes(telefono);
      CREATE INDEX IF NOT EXISTS ix_mensajes_mensaje_id ON mensajes(mensaje_id);
      CREATE INDEX IF NOT EXISTS ix_usuarios_admin_username ON usuarios_admin(username);
    `);

    // Comprobar / Crear admin en PostgreSQL
    const res = await pgPool.query('SELECT id FROM usuarios_admin WHERE username = $1', ['admin']);
    if (res.rows.length === 0) {
      const salt = bcrypt.genSaltSync(10);
      const hash = bcrypt.hashSync(initialAdminPassword, salt);
      await pgPool.query(
        'INSERT INTO usuarios_admin (username, password_hash, debe_cambiar_password) VALUES ($1, $2, 1)',
        ['admin', hash]
      );
      console.log(`✅ Usuario administrador por defecto ("admin" / "${initialAdminPassword}") creado en PostgreSQL.`);
    }
  } else {
    sqliteDb.exec(`
      CREATE TABLE IF NOT EXISTS usuarios_admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        debe_cambiar_password INTEGER DEFAULT 1
      );

      CREATE TABLE IF NOT EXISTS chat_status (
        telefono TEXT PRIMARY KEY,
        is_ai_paused INTEGER DEFAULT 0,
        ultima_actividad TEXT
      );

      CREATE TABLE IF NOT EXISTS mensajes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telefono TEXT NOT NULL,
        mensaje_id TEXT UNIQUE,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        url_media TEXT,
        es_imagen INTEGER DEFAULT 0,
        es_audio INTEGER DEFAULT 0,
        es_documento INTEGER DEFAULT 0,
        enviado_por_admin INTEGER DEFAULT 0
      );

      CREATE INDEX IF NOT EXISTS ix_mensajes_telefono ON mensajes(telefono);
      CREATE INDEX IF NOT EXISTS ix_mensajes_mensaje_id ON mensajes(mensaje_id);
      CREATE INDEX IF NOT EXISTS ix_usuarios_admin_username ON usuarios_admin(username);
    `);

    // Comprobar / Crear admin en SQLite
    const checkAdmin = sqliteDb.prepare('SELECT id FROM usuarios_admin WHERE username = ?');
    const admin = checkAdmin.get('admin');

    if (!admin) {
      const salt = bcrypt.genSaltSync(10);
      const hash = bcrypt.hashSync(initialAdminPassword, salt);
      sqliteDb.prepare(`
        INSERT INTO usuarios_admin (username, password_hash, debe_cambiar_password)
        VALUES (?, ?, 1)
      `).run('admin', hash);
      console.log(`✅ Usuario administrador por defecto ("admin" / "${initialAdminPassword}") creado en SQLite.`);
    }
  }
}

/**
 * Verifica credenciales del usuario admin.
 */
export async function verifyAdminCredentials(username, plainPassword) {
  if (!username || !plainPassword) return null;
  const cleanUsername = username.trim();

  let user = null;
  if (isPostgres) {
    const res = await pgPool.query(
      'SELECT id, username, password_hash, debe_cambiar_password FROM usuarios_admin WHERE username = $1',
      [cleanUsername]
    );
    user = res.rows[0] || null;
  } else {
    const stmt = sqliteDb.prepare(
      'SELECT id, username, password_hash, debe_cambiar_password FROM usuarios_admin WHERE username = ?'
    );
    user = stmt.get(cleanUsername) || null;
  }

  if (!user) return null;

  const valid = bcrypt.compareSync(plainPassword, user.password_hash);
  if (!valid) return null;

  return {
    id: user.id,
    username: user.username,
    debe_cambiar_password: Boolean(user.debe_cambiar_password)
  };
}

/**
 * Obtiene usuario admin por username.
 */
export async function getAdminByUsername(username) {
  if (!username) return null;

  let user = null;
  if (isPostgres) {
    const res = await pgPool.query(
      'SELECT id, username, password_hash, debe_cambiar_password FROM usuarios_admin WHERE username = $1',
      [username.trim()]
    );
    user = res.rows[0] || null;
  } else {
    const stmt = sqliteDb.prepare(
      'SELECT id, username, password_hash, debe_cambiar_password FROM usuarios_admin WHERE username = ?'
    );
    user = stmt.get(username.trim()) || null;
  }

  if (!user) return null;

  return {
    id: user.id,
    username: user.username,
    debe_cambiar_password: Boolean(user.debe_cambiar_password)
  };
}

/**
 * Actualiza la contraseña del administrador.
 */
export async function updateAdminPassword(username, newPlainPassword) {
  const salt = bcrypt.genSaltSync(10);
  const hash = bcrypt.hashSync(newPlainPassword, salt);

  if (isPostgres) {
    await pgPool.query(
      'UPDATE usuarios_admin SET password_hash = $1, debe_cambiar_password = 0 WHERE username = $2',
      [hash, username]
    );
  } else {
    const stmt = sqliteDb.prepare(`
      UPDATE usuarios_admin 
      SET password_hash = ?, debe_cambiar_password = 0 
      WHERE username = ?
    `);
    stmt.run(hash, username);
  }
}

/**
 * Verifica si un mensaje ya existe (deduplicación).
 */
export async function isMessageDuplicate(mensajeId) {
  if (!mensajeId) return false;

  if (isPostgres) {
    const res = await pgPool.query('SELECT id FROM mensajes WHERE mensaje_id = $1 LIMIT 1', [mensajeId]);
    return res.rows.length > 0;
  } else {
    const stmt = sqliteDb.prepare('SELECT id FROM mensajes WHERE mensaje_id = ?');
    const row = stmt.get(mensajeId);
    return Boolean(row);
  }
}

/**
 * Consulta si la IA está pausada para un número.
 */
export async function isChatAiPaused(telefono) {
  if (!telefono) return false;

  if (isPostgres) {
    const res = await pgPool.query('SELECT is_ai_paused FROM chat_status WHERE telefono = $1', [telefono]);
    return res.rows.length > 0 ? Boolean(res.rows[0].is_ai_paused) : false;
  } else {
    const stmt = sqliteDb.prepare('SELECT is_ai_paused FROM chat_status WHERE telefono = ?');
    const row = stmt.get(telefono);
    return row ? Boolean(row.is_ai_paused) : false;
  }
}

/**
 * Pausa o reanuda la IA para un número.
 */
export async function setChatAiPaused(telefono, paused) {
  const now = new Date().toISOString();
  const val = paused ? 1 : 0;

  if (isPostgres) {
    await pgPool.query(`
      INSERT INTO chat_status (telefono, is_ai_paused, ultima_actividad)
      VALUES ($1, $2, $3)
      ON CONFLICT (telefono) DO UPDATE SET
        is_ai_paused = EXCLUDED.is_ai_paused,
        ultima_actividad = EXCLUDED.ultima_actividad
    `, [telefono, val, now]);
  } else {
    const upsert = sqliteDb.prepare(`
      INSERT INTO chat_status (telefono, is_ai_paused, ultima_actividad)
      VALUES (?, ?, ?)
      ON CONFLICT(telefono) DO UPDATE SET
        is_ai_paused = excluded.is_ai_paused,
        ultima_actividad = excluded.ultima_actividad
    `);
    upsert.run(telefono, val, now);
  }
}

/**
 * Guarda un mensaje en la base de datos y actualiza la actividad del chat.
 */
export async function saveMessage({
  telefono,
  role,
  content,
  mensajeId = null,
  urlMedia = null,
  esImagen = false,
  esAudio = false,
  esDocumento = false,
  enviadoPorAdmin = false
}) {
  const now = new Date().toISOString();
  const imgVal = esImagen ? 1 : 0;
  const audioVal = esAudio ? 1 : 0;
  const docVal = esDocumento ? 1 : 0;
  const adminVal = enviadoPorAdmin ? 1 : 0;

  if (isPostgres) {
    await pgPool.query(`
      INSERT INTO mensajes (
        telefono, mensaje_id, role, content, timestamp, url_media,
        es_imagen, es_audio, es_documento, enviado_por_admin
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
    `, [
      telefono, mensajeId, role, content, now, urlMedia,
      imgVal, audioVal, docVal, adminVal
    ]);

    await pgPool.query(`
      INSERT INTO chat_status (telefono, is_ai_paused, ultima_actividad)
      VALUES ($1, 0, $2)
      ON CONFLICT (telefono) DO UPDATE SET
        ultima_actividad = EXCLUDED.ultima_actividad
    `, [telefono, now]);
  } else {
    const insertMsg = sqliteDb.prepare(`
      INSERT INTO mensajes (
        telefono, mensaje_id, role, content, timestamp, url_media,
        es_imagen, es_audio, es_documento, enviado_por_admin
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);

    insertMsg.run(
      telefono, mensajeId, role, content, now, urlMedia,
      imgVal, audioVal, docVal, adminVal
    );

    const upsertStatus = sqliteDb.prepare(`
      INSERT INTO chat_status (telefono, is_ai_paused, ultima_actividad)
      VALUES (?, 0, ?)
      ON CONFLICT(telefono) DO UPDATE SET
        ultima_actividad = excluded.ultima_actividad
    `);
    upsertStatus.run(telefono, now);
  }
}

/**
 * Obtiene el historial de mensajes de un teléfono ordenado cronológicamente.
 */
export async function getChatHistory(telefono, limit = 100) {
  let rows = [];

  if (isPostgres) {
    const res = await pgPool.query(`
      SELECT id, role, content, timestamp, url_media, es_imagen, es_audio, es_documento, enviado_por_admin
      FROM mensajes
      WHERE telefono = $1
      ORDER BY timestamp DESC
      LIMIT $2
    `, [telefono, limit]);
    rows = res.rows;
  } else {
    const stmt = sqliteDb.prepare(`
      SELECT id, role, content, timestamp, url_media, es_imagen, es_audio, es_documento, enviado_por_admin
      FROM mensajes
      WHERE telefono = ?
      ORDER BY timestamp DESC
      LIMIT ?
    `);
    rows = stmt.all(telefono, limit);
  }

  // Invertir para orden cronológico (antiguo -> reciente)
  rows.reverse();

  return rows.map((row) => ({
    id: row.id,
    role: row.role,
    content: row.content,
    timestamp: row.timestamp,
    url_media: row.url_media,
    es_imagen: Boolean(row.es_imagen),
    es_audio: Boolean(row.es_audio),
    es_documento: Boolean(row.es_documento),
    enviado_por_admin: Boolean(row.enviado_por_admin)
  }));
}

/**
 * Obtiene la lista de chats activos para el CRM.
 */
export async function getActiveChats() {
  if (isPostgres) {
    const resStatuses = await pgPool.query(`
      SELECT telefono, is_ai_paused, ultima_actividad
      FROM chat_status
      ORDER BY ultima_actividad DESC
    `);
    const statuses = resStatuses.rows;

    const chats = [];
    for (const status of statuses) {
      const msgRes = await pgPool.query(`
        SELECT content, es_imagen, es_audio, es_documento, timestamp
        FROM mensajes
        WHERE telefono = $1
        ORDER BY timestamp DESC
        LIMIT 1
      `, [status.telefono]);
      const latest = msgRes.rows[0] || null;

      chats.push(formatChatSummary(status, latest));
    }
    return chats;
  } else {
    const stmt = sqliteDb.prepare(`
      SELECT telefono, is_ai_paused, ultima_actividad
      FROM chat_status
      ORDER BY ultima_actividad DESC
    `);
    const statuses = stmt.all();

    const getLatestMsg = sqliteDb.prepare(`
      SELECT content, es_imagen, es_audio, es_documento, timestamp
      FROM mensajes
      WHERE telefono = ?
      ORDER BY timestamp DESC
      LIMIT 1
    `);

    return statuses.map((status) => {
      const latest = getLatestMsg.get(status.telefono);
      return formatChatSummary(status, latest);
    });
  }
}

function formatChatSummary(status, latest) {
  let preview = '';
  let esImagen = false;
  let esAudio = false;
  let esDocumento = false;

  if (latest) {
    esImagen = Boolean(latest.es_imagen);
    esAudio = Boolean(latest.es_audio);
    esDocumento = Boolean(latest.es_documento);

    if (esImagen) preview = '📷 Imagen';
    else if (esAudio) preview = '🎤 Nota de voz';
    else if (esDocumento) preview = '📄 Documento';
    else {
      preview = latest.content.length > 35 ? latest.content.slice(0, 35) + '...' : latest.content;
    }
  }

  let fechaFormateada = '';
  try {
    const d = new Date(status.ultima_actividad);
    const dia = String(d.getDate()).padStart(2, '0');
    const mes = String(d.getMonth() + 1).padStart(2, '0');
    const horas = String(d.getHours()).padStart(2, '0');
    const minutos = String(d.getMinutes()).padStart(2, '0');
    fechaFormateada = `${dia}/${mes} ${horas}:${minutos}`;
  } catch {
    fechaFormateada = status.ultima_actividad;
  }

  return {
    telefono: status.telefono,
    is_ai_paused: Boolean(status.is_ai_paused),
    ultima_actividad: fechaFormateada,
    preview,
    es_imagen: esImagen,
    es_audio: esAudio,
    es_documento: esDocumento
  };
}
