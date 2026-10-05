// src/components/LoginPage.jsx — Pantalla de login elegante con branding Tabersil
import React, { useState } from 'react';
import { User, Lock, Eye, EyeOff, MessageSquare, AlertCircle, ArrowRight, Check } from 'lucide-react';

export function LoginPage({ onLoginSuccess }) {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [shake, setShake] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username || !password || loading) return;

    setLoading(true);
    setErrorMsg('');

    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      const data = await res.json();

      if (res.ok && data.status === 'ok') {
        setSuccess(true);
        setTimeout(() => {
          onLoginSuccess(data.user);
        }, 350);
      } else {
        setErrorMsg(data.detail || 'Usuario o contraseña incorrectos');
        setShake(true);
        setTimeout(() => setShake(false), 400);
      }
    } catch (err) {
      setErrorMsg('Error de conexión con el servidor');
      setShake(true);
      setTimeout(() => setShake(false), 400);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className={`login-card ${shake ? 'shake' : ''}`}>
        <div className="brand-header">
          <div className="brand-logo-container">
            <img src="/images/logo.png" alt="Tabersil Chatbots Logo" className="brand-logo-login" />
          </div>
          <div className="brand-badge">
            <MessageSquare size={15} color="#60A5FA" />
            <span>WhatsApp</span>
            <span className="pill">Bot</span>
          </div>
          <h1 className="brand-title">Tabersil Chatbots</h1>
          <p className="brand-subtitle">Panel de gestión y atención al cliente WhatsApp</p>
        </div>

        {errorMsg && (
          <div className="error-alert">
            <AlertCircle size={16} />
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="username">Usuario</label>
            <div className="input-wrapper">
              <div className="input-icon">
                <User size={15} />
              </div>
              <input
                id="username"
                type="text"
                className="form-input"
                placeholder="admin"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
                autoComplete="username"
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">Contraseña</label>
            <div className="input-wrapper">
              <div className="input-icon">
                <Lock size={15} />
              </div>
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                className="form-input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
              <button
                type="button"
                className="toggle-password"
                onClick={() => setShowPassword(!showPassword)}
                title={showPassword ? 'Ocultar' : 'Mostrar'}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="btn-login"
            disabled={loading}
            style={success ? { background: '#10B981' } : {}}
          >
            {loading && <div className="spinner" />}
            {success ? (
              <>
                <span>¡Acceso correcto!</span>
                <Check size={16} />
              </>
            ) : (
              <>
                <span>{loading ? 'Verificando...' : 'Entrar al CRM'}</span>
                {!loading && <ArrowRight size={16} />}
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
