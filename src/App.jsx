// src/App.jsx — Componente principal de la aplicación Tabersil Chatbots CRM
import React, { useState, useEffect, useCallback } from 'react';
import { LoginPage } from './components/LoginPage';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { ChatArea } from './components/ChatArea';
import { PasswordModal } from './components/PasswordModal';

export function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(null); // null = cargando
  const [currentUser, setCurrentUser] = useState(null);
  const [activeChat, setActiveChat] = useState(null);
  const [chats, setChats] = useState([]);
  const [messages, setMessages] = useState([]);
  const [loadingChats, setLoadingChats] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);

  // 1. Verificar sesión activa al inicio
  useEffect(() => {
    async function checkAuth() {
      try {
        const res = await fetch('/api/me');
        if (res.ok) {
          const data = await res.json();
          setCurrentUser(data);
          setIsAuthenticated(true);
          if (data.debe_cambiar_password) {
            setIsPasswordModalOpen(true);
          }
        } else {
          setIsAuthenticated(false);
        }
      } catch {
        setIsAuthenticated(false);
      }
    }
    checkAuth();
  }, []);

  // 2. Cargar lista de chats
  const fetchChats = useCallback(async (silent = false) => {
    if (!silent) setLoadingChats(true);
    try {
      const res = await fetch('/api/chats');
      if (res.status === 401) {
        setIsAuthenticated(false);
        return;
      }
      if (res.ok) {
        const data = await res.json();
        setChats(data);
      }
    } catch (err) {
      console.error('Error cargando chats:', err);
    } finally {
      if (!silent) setLoadingChats(false);
    }
  }, []);

  // 3. Cargar historial del chat seleccionado
  const fetchMessages = useCallback(async (phone, silent = false) => {
    if (!phone) return;
    if (!silent) setLoadingMessages(true);
    try {
      const res = await fetch(`/api/historial/${encodeURIComponent(phone)}`);
      if (res.status === 401) {
        setIsAuthenticated(false);
        return;
      }
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
      }
    } catch (err) {
      console.error('Error cargando mensajes:', err);
    } finally {
      if (!silent) setLoadingMessages(false);
    }
  }, []);

  // 4. Polling periódico cada 3 segundos
  useEffect(() => {
    if (!isAuthenticated) return;

    fetchChats(true);

    const interval = setInterval(() => {
      fetchChats(true);
      if (activeChat) {
        fetchMessages(activeChat, true);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [isAuthenticated, activeChat, fetchChats, fetchMessages]);

  // 5. Cargar mensajes cuando cambia el chat activo
  useEffect(() => {
    if (activeChat) {
      fetchMessages(activeChat, false);
    } else {
      setMessages([]);
    }
  }, [activeChat, fetchMessages]);

  // 6. Soporte para botón atrás en móviles con popstate
  useEffect(() => {
    const handlePopState = () => {
      if (window.innerWidth <= 768 && !window.location.hash.startsWith('#chat-')) {
        setActiveChat(null);
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const handleSelectChat = (phone) => {
    setActiveChat(phone);
    if (window.innerWidth <= 768) {
      window.history.pushState({ chat: phone }, '', `#chat-${encodeURIComponent(phone)}`);
    }
  };

  const handleBackFromChat = () => {
    setActiveChat(null);
    if (window.location.hash.startsWith('#chat-')) {
      window.history.back();
    }
  };

  const handleSendMessage = async (text) => {
    if (!activeChat || !text.trim() || sending) return;

    setSending(true);

    // Actualización optimista inmediata en la UI
    const optimisticMsg = {
      id: Date.now(),
      role: 'assistant',
      content: text,
      timestamp: new Date().toISOString(),
      enviado_por_admin: true
    };
    setMessages((prev) => [...prev, optimisticMsg]);

    try {
      const res = await fetch('/api/enviar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          telefono: activeChat,
          mensaje: text
        })
      });

      if (res.status === 401) {
        setIsAuthenticated(false);
        return;
      }

      if (res.ok) {
        fetchMessages(activeChat, true);
        fetchChats(true);
      }
    } catch (err) {
      console.error('Error enviando mensaje:', err);
    } finally {
      setSending(false);
    }
  };

  const handleToggleAi = async () => {
    if (!activeChat) return;

    try {
      const res = await fetch('/api/toggle-ia', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ telefono: activeChat })
      });

      if (res.status === 401) {
        setIsAuthenticated(false);
        return;
      }

      if (res.ok) {
        const data = await res.json();
        // Actualizar chat local
        setChats((prev) =>
          prev.map((c) =>
            c.telefono === activeChat ? { ...c, is_ai_paused: data.is_ai_paused } : c
          )
        );
      }
    } catch (err) {
      console.error('Error toggle IA:', err);
    }
  };

  const handleLogout = async () => {
    try {
      await fetch('/api/logout', { method: 'POST' });
    } catch {
      // Ignorar error de red
    }
    setIsAuthenticated(false);
    setCurrentUser(null);
    setActiveChat(null);
  };

  const handleLoginSuccess = (user) => {
    setCurrentUser(user);
    setIsAuthenticated(true);
    if (user.debe_cambiar_password) {
      setIsPasswordModalOpen(true);
    }
    fetchChats();
  };

  // Pantalla de carga inicial
  if (isAuthenticated === null) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#000000' }}>
        <div className="spinner" style={{ width: 28, height: 28, borderWidth: 3, display: 'block' }} />
      </div>
    );
  }

  // Si no está autenticado, mostrar Login
  if (!isAuthenticated) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  const activeChatInfo = chats.find((c) => c.telefono === activeChat);

  return (
    <div className="app-container">
      {/* Barra superior */}
      <Navbar
        currentUser={currentUser}
        activeChat={activeChat}
        onOpenPasswordModal={() => setIsPasswordModalOpen(true)}
        onLogout={handleLogout}
      />

      {/* Contenedor principal responsive WhatsApp */}
      <div className={`crm-layout ${activeChat ? 'mobile-chat-active' : ''}`}>
        <Sidebar
          chats={chats}
          activeChat={activeChat}
          onSelectChat={handleSelectChat}
          onRefresh={() => fetchChats(false)}
          loading={loadingChats}
        />

        <ChatArea
          activeChat={activeChat}
          chatInfo={activeChatInfo}
          messages={messages}
          loadingMessages={loadingMessages}
          onBack={handleBackFromChat}
          onSendMessage={handleSendMessage}
          onToggleAi={handleToggleAi}
          sending={sending}
        />
      </div>

      {/* Modal cambio de contraseña */}
      <PasswordModal
        isOpen={isPasswordModalOpen}
        isForced={Boolean(currentUser?.debe_cambiar_password)}
        onClose={() => setIsPasswordModalOpen(false)}
        onSuccess={() => {
          setIsPasswordModalOpen(false);
          setCurrentUser((prev) => (prev ? { ...prev, debe_cambiar_password: false } : null));
        }}
      />
    </div>
  );
}
