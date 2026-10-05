// scripts/reset-client.js — Limpieza de datos y reseteo para nuevo cliente
import { DatabaseSync } from 'node:sqlite';
import fs from 'node:fs';
import path from 'node:path';
import bcrypt from 'bcryptjs';

const DB_PATH = process.env.DATABASE_FILE || path.resolve(process.cwd(), 'agentkit.db');
const CLIENT_DIR = path.resolve(process.cwd(), 'client');
const TEMPLATE_DIR = path.resolve(process.cwd(), 'client.template');

console.log('🔄 Iniciando reseteo de entorno para nuevo cliente...\n');

// 1. Limpieza de base de datos
try {
  const db = new DatabaseSync(DB_PATH);
  
  // Borrar mensajes y estados de chats de prueba
  db.exec('DELETE FROM mensajes;');
  db.exec('DELETE FROM chat_status;');
  db.exec('VACUUM;');

  // Verificar o restaurar usuario admin
  const checkAdmin = db.prepare('SELECT id FROM usuarios_admin WHERE username = ?');
  const admin = checkAdmin.get('admin');

  if (!admin) {
    const salt = bcrypt.genSaltSync(10);
    const hash = bcrypt.hashSync('admin', salt);
    db.prepare('INSERT INTO usuarios_admin (username, password_hash, debe_cambiar_password) VALUES (?, ?, 1)')
      .run('admin', hash);
    console.log('✅ Usuario admin ("admin" / "admin") verificado/creado.');
  }

  console.log('✅ Base de datos limpia: chats y mensajes de prueba eliminados.');
} catch (err) {
  console.error('❌ Error limpiando base de datos:', err.message);
}

// 2. Verificar o restaurar carpeta client/
const shouldRestoreTemplate = process.argv.includes('--restore-template');

if (!fs.existsSync(CLIENT_DIR) || shouldRestoreTemplate) {
  if (fs.existsSync(TEMPLATE_DIR)) {
    fs.cpSync(TEMPLATE_DIR, CLIENT_DIR, { recursive: true });
    console.log('✅ Carpeta client/ restaurada con la plantilla base en blanco.');
  } else {
    console.warn('⚠️ client.template/ no encontrada.');
  }
} else {
  console.log('ℹ️ Carpeta client/ conservada (usa --restore-template si deseas sobreescribirla con la plantilla en blanco).');
}

console.log('\n🎉 ¡Entorno listo y 100% limpio para un nuevo cliente!');
console.log('👉 Personaliza la configuración en: client/config.yaml');
console.log('👉 Agrega documentos o precios en: client/knowledge/\n');
