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
      setError(err instanceof Error ? err.message : '登录失败');
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
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{
            width: 48, height: 48, borderRadius: 12, margin: '0 auto 14px',
            background: 'linear-gradient(135deg, #0071e3, #42a5f5)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 22, color: '#fff', fontWeight: 600,
          }}>
            TT
          </div>
          <h1 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', color: 'var(--gray-800)' }}>
            TT Tools
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
              placeholder="admin@tt-tools.com" required autoFocus
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

        <p style={{ marginTop: 20, textAlign: 'center', fontSize: 11, color: 'var(--gray-400)' }}>
          admin@tt-tools.com / admin123
        </p>
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
