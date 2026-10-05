// src/components/Navbar.jsx — Barra superior de navegación y acciones
import React from 'react';
import { Download, Key, LogOut, Phone, User } from 'lucide-react';
import { usePwaInstall } from '../hooks/usePwaInstall';

export function Navbar({ currentUser, activeChat, onOpenPasswordModal, onLogout }) {
  const { canInstall, installApp } = usePwaInstall();

  return (
    <header className="navbar">
      <div className="navbar-brand">
        <img src="/images/favicon.png" alt="Tabersil Logo" className="navbar-logo-img" />
        <span>Tabersil <span className="highlight">Chatbots</span></span>
      </div>

      <div className="navbar-center">
        <Phone size={14} color="#71717A" />
        <span>
          {activeChat ? `Cliente: ${activeChat}` : 'Ningún chat seleccionado'}
        </span>
      </div>

      <div className="navbar-actions">
        {canInstall && (
          <button className="btn btn-pwa" onClick={installApp} title="Instalar Tabersil Chatbots como App">
            <Download size={14} />
            <span>Instalar App</span>
          </button>
        )}

        <div className="user-chip">
          <User size={14} />
          <span>{currentUser?.username || 'admin'}</span>
        </div>

        <button className="btn" onClick={onOpenPasswordModal} title="Cambiar contraseña">
          <Key size={14} />
          <span>Clave</span>
        </button>

        <button className="btn btn-logout" onClick={onLogout} title="Cerrar sesión">
          <LogOut size={14} />
          <span>Salir</span>
        </button>
      </div>
    </header>
  );
}
