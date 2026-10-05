// src/components/Sidebar.jsx — Lista lateral de conversaciones estilo WhatsApp
import React, { useState } from 'react';
import { MessageSquare, RefreshCw, Search, User, Bot, Image as ImageIcon, Mic, FileText } from 'lucide-react';

export function Sidebar({ chats, activeChat, onSelectChat, onRefresh, loading }) {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredChats = chats.filter((c) => {
    const term = searchTerm.toLowerCase();
    return (
      c.telefono.toLowerCase().includes(term) ||
      (c.preview && c.preview.toLowerCase().includes(term))
    );
  });

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-header-title">
          <MessageSquare size={14} />
          <span>Conversaciones</span>
          <span className="sidebar-count-badge">{chats.length}</span>
        </div>
        <button className="btn" onClick={onRefresh} title="Actualizar lista" disabled={loading}>
          <RefreshCw size={13} className={loading ? 'spinner' : ''} />
        </button>
      </div>

      <div className="search-box-row">
        <div className="search-box">
          <Search size={14} />
          <input
            type="text"
            className="search-input"
            placeholder="Buscar por teléfono o texto..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      <div className="chat-list">
        {filteredChats.length === 0 ? (
          <div style={{ padding: '30px 16px', textAlign: 'center', color: '#52525B', fontSize: '0.85rem' }}>
            {searchTerm ? 'No se encontraron conversaciones' : 'No hay chats activos aún'}
          </div>
        ) : (
          filteredChats.map((chat) => {
            const isActive = activeChat === chat.telefono;

            return (
              <div
                key={chat.telefono}
                className={`chat-item ${isActive ? 'active' : ''}`}
                onClick={() => onSelectChat(chat.telefono)}
              >
                <div className="chat-avatar">
                  <User size={20} />
                </div>

                <div className="chat-info">
                  <div className="chat-item-header">
                    <span className="chat-item-phone">{chat.telefono}</span>
                    <span className="chat-item-time">{chat.ultima_actividad}</span>
                  </div>

                  <div className="chat-item-footer">
                    <span className="chat-item-preview">
                      {chat.es_imagen && <ImageIcon size={12} style={{ display: 'inline', marginRight: 4 }} />}
                      {chat.es_audio && <Mic size={12} style={{ display: 'inline', marginRight: 4 }} />}
                      {chat.es_documento && <FileText size={12} style={{ display: 'inline', marginRight: 4 }} />}
                      {chat.preview || 'Sin mensajes'}
                    </span>

                    <span className={`badge-ai ${chat.is_ai_paused ? 'paused' : 'active'}`}>
                      <Bot size={10} />
                      {chat.is_ai_paused ? 'IA Pausada' : 'IA Activa'}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
