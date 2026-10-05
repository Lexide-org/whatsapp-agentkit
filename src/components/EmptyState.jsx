// src/components/EmptyState.jsx — Estado vacío cuando no hay chat seleccionado
import React from 'react';

export function EmptyState() {
  return (
    <div className="no-chat-selected">
      <div className="empty-graphic">
        <img
          src="/images/icon-192.png"
          alt="Tabersil Chatbots"
          className="empty-logo-img"
        />
      </div>
      <h2 className="empty-title">Tabersil Chatbots</h2>
      <p className="empty-desc">
        Selecciona una conversación en la lista lateral para ver el historial completo y responder directamente al cliente.
      </p>
    </div>
  );
}
