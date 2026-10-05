// src/components/PasswordModal.jsx — Modal de actualización de contraseña
import React, { useState } from 'react';
import { Lock, Key, Eye, EyeOff, AlertCircle, Check, X } from 'lucide-react';

export function PasswordModal({ isOpen, isForced, onClose, onSuccess }) {
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!newPassword || !confirmPassword || loading) return;

    if (newPassword.length < 4) {
      setErrorMsg('La contraseña debe tener al menos 4 caracteres');
      return;
    }

    if (newPassword !== confirmPassword) {
      setErrorMsg('Las contraseñas no coinciden');
      return;
    }

    setLoading(true);
    setErrorMsg('');

    try {
      const res = await fetch('/api/cambiar-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: newPassword })
      });

      const data = await res.json();
      if (res.ok && data.status === 'ok') {
        setNewPassword('');
        setConfirmPassword('');
        onSuccess();
      } else {
        setErrorMsg(data.detail || 'Error al actualizar contraseña');
      }
    } catch (err) {
      setErrorMsg('Error de conexión con el servidor');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-card">
        <div className="brand-header">
          <div className="brand-badge">
            <Lock size={15} color="#60A5FA" />
            <span>Tabersil</span>
            <span className="pill">Seguridad</span>
          </div>
          <h1 className="brand-title">Actualizar Clave</h1>
          <p className="brand-subtitle">
            {isForced
              ? 'Por seguridad, debes cambiar la contraseña por defecto antes de continuar.'
              : 'Establece una contraseña segura para tu cuenta de administrador.'}
          </p>
        </div>

        {errorMsg && (
          <div className="error-alert">
            <AlertCircle size={16} />
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="new-pw">Nueva Contraseña</label>
            <div className="input-wrapper">
              <div className="input-icon">
                <Lock size={15} />
              </div>
              <input
                id="new-pw"
                type={showNew ? 'text' : 'password'}
                className="form-input"
                placeholder="••••••••"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                autoComplete="new-password"
              />
              <button
                type="button"
                className="toggle-password"
                onClick={() => setShowNew(!showNew)}
              >
                {showNew ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="confirm-pw">Confirmar Contraseña</label>
            <div className="input-wrapper">
              <div className="input-icon">
                <Key size={15} />
              </div>
              <input
                id="confirm-pw"
                type={showConfirm ? 'text' : 'password'}
                className="form-input"
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
              />
              <button
                type="button"
                className="toggle-password"
                onClick={() => setShowConfirm(!showConfirm)}
              >
                {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <button type="submit" className="btn-login" disabled={loading} style={{ marginTop: 22 }}>
            {loading ? <div className="spinner" /> : <Check size={16} />}
            <span>{loading ? 'Guardando...' : 'Guardar Contraseña'}</span>
          </button>

          {!isForced && (
            <button type="button" className="btn-cancel" onClick={onClose} disabled={loading}>
              <X size={14} />
              <span>Cancelar</span>
            </button>
          )}
        </form>
      </div>
    </div>
  );
}
