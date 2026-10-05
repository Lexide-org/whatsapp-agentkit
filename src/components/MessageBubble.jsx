// src/components/MessageBubble.jsx — Burbuja de mensaje individual estilo WhatsApp
import React from 'react';
import { CheckCheck, User, Bot, FileText, Download } from 'lucide-react';

export function MessageBubble({ message }) {
  const isUser = message.role === 'user';
  const isAdmin = Boolean(message.enviado_por_admin);

  // Formatear hora de timestamp
  let timeStr = '';
  try {
    const d = new Date(message.timestamp);
    const h = String(d.getHours()).padStart(2, '0');
    const m = String(d.getMinutes()).padStart(2, '0');
    timeStr = `${h}:${m}`;
  } catch {
    timeStr = message.timestamp;
  }

  return (
    <div className={`message-row ${isUser ? 'user' : 'assistant'}`}>
      <div className={`message-bubble ${isAdmin ? 'admin-sent' : ''}`}>
        {/* Etiqueta distintiva si fue respondido por un asesor humano */}
        {isAdmin && (
          <div className="msg-admin-tag">
            <User size={11} />
            <span>Asesor (Tú)</span>
          </div>
        )}

        {/* Contenido Multimedia */}
        {message.es_imagen && message.url_media && (
          <div className="message-media">
            <img src={message.url_media} alt="WhatsApp multimedia" loading="lazy" />
          </div>
        )}

        {message.es_audio && message.url_media && (
          <div className="message-media">
            <audio controls src={message.url_media}>
              Tu navegador no soporta el reproductor de audio.
            </audio>
          </div>
        )}

        {message.es_documento && message.url_media && (
          <div className="message-media">
            <a
              href={message.url_media}
              target="_blank"
              rel="noopener noreferrer"
              className="btn"
              style={{ padding: '6px 10px', fontSize: '0.8rem', background: '#111116' }}
            >
              <FileText size={15} color="#60A5FA" />
              <span>Descargar documento</span>
              <Download size={13} />
            </a>
          </div>
        )}

        {/* Texto del mensaje */}
        {message.content && (
          <div style={{ wordBreak: 'break-word' }}>
            {message.content}
          </div>
        )}

        {/* Hora y checks de lectura */}
        <div className="message-meta">
          <span>{timeStr}</span>
          {!isUser && (
            <span className="msg-check">
              <CheckCheck size={13} />
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
