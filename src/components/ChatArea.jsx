// src/components/ChatArea.jsx — Ventana central de conversación WhatsApp
import React, { useEffect, useRef } from 'react';
import { ArrowLeft, User, Bot, BotOff } from 'lucide-react';
import { MessageBubble } from './MessageBubble';
import { MessageInput } from './MessageInput';
import { EmptyState } from './EmptyState';

export function ChatArea({
  activeChat,
  chatInfo,
  messages,
  loadingMessages,
  onBack,
  onSendMessage,
  onToggleAi,
  sending
}) {
  const messagesEndRef = useRef(null);

  const scrollToBottom = (smooth = true) => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' });
    }
  };

  useEffect(() => {
    scrollToBottom(false);
  }, [activeChat]);

  useEffect(() => {
    scrollToBottom(true);
  }, [messages]);

  if (!activeChat) {
    return (
      <main className="chat-area">
        <EmptyState />
      </main>
    );
  }

  const isAiPaused = Boolean(chatInfo?.is_ai_paused);

  return (
    <main className="chat-area">
      {/* Header estilo WhatsApp */}
      <div className="chat-header">
        <div className="chat-header-left">
          <button className="btn-back" onClick={onBack} title="Volver a lista de chats">
            <ArrowLeft size={20} />
          </button>

          <div className="chat-header-avatar">
            <User size={18} />
          </div>

          <div className="chat-header-meta">
            <span className="chat-header-phone">{activeChat}</span>
            <span className={`chat-header-status ${isAiPaused ? 'offline' : 'online'}`}>
              <Bot size={11} />
              <span>{isAiPaused ? 'IA Pausada' : 'IA Activa'}</span>
            </span>
          </div>
        </div>

        <div className="chat-actions">
          <button
            className={`btn-toggle-ia ${isAiPaused ? 'paused' : ''}`}
            onClick={onToggleAi}
            title={isAiPaused ? 'Reanudar respuestas automáticas de la IA' : 'Pausar respuestas automáticas de la IA'}
          >
            {isAiPaused ? <BotOff size={15} /> : <Bot size={15} />}
            <span>{isAiPaused ? 'IA Pausada' : 'IA Activa'}</span>
          </button>
        </div>
      </div>

      {/* Historial de Mensajes */}
      <div className="messages-viewport">
        {loadingMessages && messages.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '30px 0', color: '#71717A', fontSize: '0.85rem' }}>
            Cargando historial de mensajes...
          </div>
        ) : messages.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '30px 0', color: '#71717A', fontSize: '0.85rem' }}>
            No hay mensajes previos en esta conversación.
          </div>
        ) : (
          messages.map((msg, idx) => (
            <MessageBubble key={msg.id || idx} message={msg} />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Barra de entrada de texto */}
      <MessageInput onSendMessage={onSendMessage} disabled={sending} />
    </main>
  );
}
