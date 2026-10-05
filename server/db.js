// server/db.js — Gestión de base de datos SQLite con node:sqlite nativo
import { DatabaseSync } from 'node:sqlite';
import bcrypt from 'bcryptjs';
import path from 'node:path';
import fs from 'node:fs';

const DB_PATH = process.env.DATABASE_FILE || path.resolve(process.cwd(), 'agentkit.db');

export const db = new DatabaseSync(DB_PATH);

/**
 * Inicializa las tablas de SQLite y crea el administrador por defecto si no existe.
 */
export function initDb() {
  db.exec(`
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

  // Crear usuario administrador por defecto si no existe
  const checkAdmin = db.prepare('SELECT id, password_hash, debe_cambiar_password FROM usuarios_admin WHERE username = ?');
  const admin = checkAdmin.get('admin');

  if (!admin) {
    const salt = bcrypt.genSaltSync(10);
    const hash = bcrypt.hashSync('admin', salt);
    const insertAdmin = db.prepare(`
      INSERT INTO usuarios_admin (username, password_hash, debe_cambiar_password)
      VALUES (?, ?, 1)
    `);
    insertAdmin.run('admin', hash);
    console.log('✅ Usuario administrador por defecto ("admin" / "admin") creado en SQLite.');
  }
}

/**
 * Verifica credenciales del usuario admin.
 */
export function verifyAdminCredentials(username, plainPassword) {
  if (!username || !plainPassword) return null;
  const stmt = db.prepare('SELECT id, username, password_hash, debe_cambiar_password FROM usuarios_admin WHERE username = ?');
  const user = stmt.get(username.trim());
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
export function getAdminByUsername(username) {
  if (!username) return null;
  const stmt = db.prepare('SELECT id, username, password_hash, debe_cambiar_password FROM usuarios_admin WHERE username = ?');
  const user = stmt.get(username);
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
export function updateAdminPassword(username, newPlainPassword) {
  const salt = bcrypt.genSaltSync(10);
  const hash = bcrypt.hashSync(newPlainPassword, salt);
  const stmt = db.prepare(`
    UPDATE usuarios_admin 
    SET password_hash = ?, debe_cambiar_password = 0 
    WHERE username = ?
  `);
  return stmt.run(hash, username);
}

/**
 * Verifica si un mensaje ya existe (deduplicación).
 */
export function isMessageDuplicate(mensajeId) {
  if (!mensajeId) return false;
  const stmt = db.prepare('SELECT id FROM mensajes WHERE mensaje_id = ?');
  const row = stmt.get(mensajeId);
  return Boolean(row);
}

/**
 * Consulta si la IA está pausada para un número.
 */
export function isChatAiPaused(telefono) {
  if (!telefono) return false;
  const stmt = db.prepare('SELECT is_ai_paused FROM chat_status WHERE telefono = ?');
  const row = stmt.get(telefono);
  return row ? Boolean(row.is_ai_paused) : false;
}

/**
 * Pausa o reanuda la IA para un número.
 */
export function setChatAiPaused(telefono, paused) {
  const now = new Date().toISOString();
  const upsert = db.prepare(`
    INSERT INTO chat_status (telefono, is_ai_paused, ultima_actividad)
    VALUES (?, ?, ?)
    ON CONFLICT(telefono) DO UPDATE SET
      is_ai_paused = excluded.is_ai_paused,
      ultima_actividad = excluded.ultima_actividad
  `);
  upsert.run(telefono, paused ? 1 : 0, now);
}

/**
 * Guarda un mensaje en la base de datos y actualiza la actividad del chat.
 */
export function saveMessage({
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

  const insertMsg = db.prepare(`
    INSERT INTO mensajes (
      telefono, mensaje_id, role, content, timestamp, url_media,
      es_imagen, es_audio, es_documento, enviado_por_admin
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);

  insertMsg.run(
    telefono,
    mensajeId,
    role,
    content,
    now,
    urlMedia,
    esImagen ? 1 : 0,
    esAudio ? 1 : 0,
    esDocumento ? 1 : 0,
    enviadoPorAdmin ? 1 : 0
  );

  // Actualizar última actividad del chat
  const upsertStatus = db.prepare(`
    INSERT INTO chat_status (telefono, is_ai_paused, ultima_actividad)
    VALUES (?, 0, ?)
    ON CONFLICT(telefono) DO UPDATE SET
      ultima_actividad = excluded.ultima_actividad
  `);
  upsertStatus.run(telefono, now);
}

/**
 * Obtiene el historial de mensajes de un teléfono ordenado cronológicamente.
 */
export function getChatHistory(telefono, limit = 100) {
  const stmt = db.prepare(`
    SELECT id, role, content, timestamp, url_media, es_imagen, es_audio, es_documento, enviado_por_admin
    FROM mensajes
    WHERE telefono = ?
    ORDER BY timestamp DESC
    LIMIT ?
  `);

  const rows = stmt.all(telefono, limit);
  // Invertir para orden cronológico (pasado -> presente)
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
export function getActiveChats() {
  const stmt = db.prepare(`
    SELECT telefono, is_ai_paused, ultima_actividad
    FROM chat_status
    ORDER BY ultima_actividad DESC
  `);
  const statuses = stmt.all();

  const getLatestMsg = db.prepare(`
    SELECT content, es_imagen, es_audio, es_documento, timestamp
    FROM mensajes
    WHERE telefono = ?
    ORDER BY timestamp DESC
    LIMIT 1
  `);

  return statuses.map((status) => {
    const latest = getLatestMsg.get(status.telefono);
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

    // Formatear fecha amigable (ej: 01/10 16:30)
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
  });
}
