import React, { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [account, setAccount] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault(); setError(''); setLoading(true);
    try {
      await login(account, password);
      navigate('/dashboard');
    } catch (err: unknown) {
      const msg = (err && typeof err === 'object' && 'message' in (err as object))
        ? String((err as { message: unknown }).message)
        : '登录失败';
      setError(msg);
    } finally { setLoading(false); }
  };

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      minHeight: '100vh', background: 'var(--gray-100)',
    }}>
      <div style={{
        width: 380, background: 'var(--white)', borderRadius: 'var(--radius-xl)',
        padding: '44px 40px 36px',
        boxShadow: 'var(--shadow-lg)',
      }}>
        {/* Logo — 使用桌面端同款图标 */}
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <img src="/admin/app-icon.png" alt="Alphoria" style={{
            width: 56, height: 56, borderRadius: 14, margin: '0 auto 14px',
            display: 'block', objectFit: 'contain',
            boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
          }} />
          <h1 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', color: 'var(--gray-800)' }}>
            Alphoria
          </h1>
          <p style={{ fontSize: 13, color: 'var(--gray-500)', marginTop: 4 }}>
            管理后台
          </p>
        </div>

        {error && (
          <div style={{
            background: '#fff2f0', border: '1px solid #ffccc7',
            borderRadius: 'var(--radius-sm)', padding: '10px 14px',
            marginBottom: 18, fontSize: 12, color: 'var(--red)',
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>账号</label>
            <input type="text" value={account} onChange={e => setAccount(e.target.value)}
              placeholder="管理员账号" required autoFocus
              style={inputStyle} />
          </div>
          <div style={{ marginBottom: 24 }}>
            <label style={labelStyle}>密码</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)}
              placeholder="••••••••" required
              style={inputStyle} />
          </div>
          <button type="submit" disabled={loading} style={{
            width: '100%', padding: '11px 0', borderRadius: 'var(--radius-md)',
            border: 'none', background: loading ? 'var(--gray-400)' : 'var(--blue)',
            color: '#fff', fontSize: 15, fontWeight: 500, letterSpacing: '-0.01em',
            transition: 'all 0.15s ease',
            cursor: loading ? 'not-allowed' : 'pointer',
          }}>
            {loading ? '登录中…' : '登录'}
          </button>
        </form>

      </div>
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  display: 'block', marginBottom: 6, fontSize: 12, fontWeight: 500,
  color: 'var(--gray-700)', letterSpacing: '-0.01em',
};
const inputStyle: React.CSSProperties = {
  width: '100%', padding: '10px 14px', border: '1px solid var(--gray-300)',
  borderRadius: 'var(--radius-md)', fontSize: 14, outline: 'none',
  color: 'var(--gray-800)', background: 'var(--gray-100)',
  boxSizing: 'border-box', transition: 'border-color 0.15s ease',
};
