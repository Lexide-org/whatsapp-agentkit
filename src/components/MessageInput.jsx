// src/components/MessageInput.jsx — Barra inferior de redacción y envío
import React, { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';

export function MessageInput({ onSendMessage, disabled }) {
  const [text, setText] = useState('');
  const inputRef = useRef(null);

  useEffect(() => {
    if (!disabled && inputRef.current) {
      inputRef.current.focus();
    }
  }, [disabled]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || disabled) return;

    onSendMessage(trimmed);
    setText('');
    if (inputRef.current) inputRef.current.focus();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form className="input-area" onSubmit={handleSubmit}>
      <div className="input-pill-wrapper">
        <input
          ref={inputRef}
          type="text"
          className="input-message"
          placeholder="Escribe un mensaje de venta..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          autoComplete="off"
        />
      </div>

      <button
        type="submit"
        className="btn-send"
        disabled={disabled || !text.trim()}
        title="Enviar mensaje (Enter)"
      >
        <Send size={16} />
      </button>
    </form>
  );
}
