// server/brain.js — Conexión con Google Gemini AI (@google/genai)
// Carga configuración dinámica y base de conocimiento desde la carpeta 'client/'
import fs from 'node:fs';
import path from 'node:path';
import yaml from 'js-yaml';
import { GoogleGenAI } from '@google/genai';

let geminiClient = null;
const apiKey = process.env.GEMINI_API_KEY;

if (apiKey && apiKey !== 'dummy-key-local-development') {
  try {
    geminiClient = new GoogleGenAI({ apiKey });
  } catch (err) {
    console.warn('⚠️ No se pudo inicializar GoogleGenAI:', err.message);
  }
}

/**
 * Carga la configuración del cliente activo.
 * Prioridad: client/config.yaml -> client.template/config.yaml -> config/prompts.yaml
 */
export function loadClientConfig() {
  const pathsToTry = [
    path.resolve(process.cwd(), 'client', 'config.yaml'),
    path.resolve(process.cwd(), 'client.template', 'config.yaml'),
    path.resolve(process.cwd(), 'config', 'prompts.yaml')
  ];

  for (const filePath of pathsToTry) {
    if (fs.existsSync(filePath)) {
      try {
        const content = fs.readFileSync(filePath, 'utf-8');
        const parsed = yaml.load(content) || {};
        return parsed;
      } catch (err) {
        console.error(`Error leyendo configuración en ${filePath}:`, err.message);
      }
    }
  }

  return {};
}

/**
 * Escanea y lee todos los documentos de texto en client/knowledge/
 * Ignora archivos de documentación como README.md o .gitkeep.
 */
export function loadKnowledgeBase() {
  const knowledgeDir = path.resolve(process.cwd(), 'client', 'knowledge');
  if (!fs.existsSync(knowledgeDir)) {
    return '';
  }

  try {
    const files = fs.readdirSync(knowledgeDir);
    const validExtensions = ['.txt', '.md', '.json', '.csv'];
    const documents = [];

    for (const file of files) {
      if (file.toLowerCase() === 'readme.md' || file.startsWith('.')) {
        continue;
      }

      const ext = path.extname(file).toLowerCase();
      if (validExtensions.includes(ext)) {
        const fullPath = path.join(knowledgeDir, file);
        const stat = fs.statSync(fullPath);
        if (stat.isFile()) {
          const fileContent = fs.readFileSync(fullPath, 'utf-8').trim();
          if (fileContent) {
            documents.push(`### Documento: ${file}\n${fileContent}`);
          }
        }
      }
    }

    if (documents.length > 0) {
      return `\n\n## BASE DE CONOCIMIENTO DEL NEGOCIO (INFORMACIÓN OFICIAL Y DE REFERENCIA):\n${documents.join('\n\n')}`;
    }
  } catch (err) {
    console.warn('⚠️ Error leyendo carpeta client/knowledge:', err.message);
  }

  return '';
}

/**
 * Construye dinámicamente el System Prompt para Gemini a partir de client/config.yaml
 * y la base de conocimiento cargada en client/knowledge/.
 */
export function getSystemPrompt() {
  const cfg = loadClientConfig();

  // Si tiene la estructura nueva client/config.yaml:
  if (cfg.agent || cfg.business) {
    const agent = cfg.agent || {};
    const business = cfg.business || {};

    const name = agent.name || 'Asistente';
    const role = agent.role || 'Asistente virtual de atención y ventas por WhatsApp';
    const tone = agent.tone || 'amigable, profesional y empático';
    const language = agent.language || 'Español';

    const bizName = business.name || 'nuestra empresa';
    const bizDesc = business.description || '';
    const bizSchedule = business.schedule || '';
    const bizContact = business.contact_email || '';
    const bizPhone = business.phone || '';
    const bizAddress = business.address || '';

    const rulesList = Array.isArray(agent.rules) && agent.rules.length > 0
      ? agent.rules.map((r) => `- ${r}`).join('\n')
      : '- Responde siempre de manera concisa y respetuosa.\n- Responde siempre en español.';

    const knowledgeText = loadKnowledgeBase();

    return `Eres ${name}, ${role} para ${bizName}.

## Tu Identidad y Tono
- Tu nombre: ${name}
- Negocio al que representas: ${bizName}
- Tu tono: ${tone}
- Idioma de respuesta: ${language}

## Sobre el Negocio
${bizDesc ? `- Descripción: ${bizDesc}` : ''}
${bizSchedule ? `- Horario de atención: ${bizSchedule}` : ''}
${bizContact ? `- Correo de contacto: ${bizContact}` : ''}
${bizPhone ? `- Teléfono: ${bizPhone}` : ''}
${bizAddress ? `- Ubicación: ${bizAddress}` : ''}

## Reglas Obligatorias de Comportamiento:
${rulesList}${knowledgeText}
`;
  }

  // Compatibilidad con prompt plano legacy (prompts.yaml)
  return cfg.system_prompt || 'Eres Alex, el asistente virtual de Tabersil Studios. Responde siempre en español de manera profesional y amigable.';
}

export function getFallbackMessage() {
  const cfg = loadClientConfig();
  return cfg.agent?.fallback_message || cfg.fallback_message || 'Disculpa, no entendí del todo tu mensaje. ¿Podrías reformularlo para ayudarte mejor?';
}

export function getErrorMessage() {
  const cfg = loadClientConfig();
  return cfg.agent?.error_message || cfg.error_message || 'Lo siento, tenemos dificultades técnicas temporales. Por favor intenta de nuevo en unos minutos.';
}

/**
 * Genera una respuesta usando Gemini 2.5 Flash con historial conversacional.
 */
export async function generateAiReply(message, history = []) {
  if (!message || message.trim().length < 2) {
    return getFallbackMessage();
  }

  if (!geminiClient) {
    return '¡Hola! El servidor y CRM de Tabersil Chatbots están funcionando en Node.js. Para habilitar las respuestas automáticas de la IA, agrega tu GEMINI_API_KEY en el archivo .env.';
  }

  const systemPrompt = getSystemPrompt();

  // Convertir historial a formato de Google Gen AI
  const contents = [];
  for (const item of history) {
    const role = item.role === 'assistant' ? 'model' : 'user';
    contents.push({
      role,
      parts: [{ text: item.content }]
    });
  }

  // Agregar el mensaje actual del usuario
  contents.push({
    role: 'user',
    parts: [{ text: message }]
  });

  try {
    const response = await geminiClient.models.generateContent({
      model: 'gemini-2.5-flash',
      contents,
      config: {
        systemInstruction: systemPrompt,
        maxOutputTokens: 1024
      }
    });

    const replyText = response.text;
    console.log('🤖 Respuesta generada por Gemini con éxito');
    return replyText;
  } catch (err) {
    console.error('❌ Error llamando a Gemini API:', err);
    return getErrorMessage();
  }
}
