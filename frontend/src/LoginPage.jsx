// LoginPage.jsx
// Interactive portal allowing users to log into or sign up for the platform.
// Stores obtained security tokens directly inside HTTP local storage safely.

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { loginUser, registerUser } from './api';

export default function LoginPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  // Coordinates data submission depending on whether it is a registration or login.
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const resp = isLogin 
        ? await loginUser(username, password)
        : await registerUser(username, password);
      localStorage.setItem('token', resp.data.access_token);
      localStorage.setItem('username', username);
      navigate('/rooms');
    } catch (err) {
      setError(err.response?.data?.detail || "Authentication Failed");
    }
  };

  return (
    <div className="auth-wrapper">
      <div className="card auth-form">
        <h2>{isLogin ? 'Hello again.' : 'Join the Space.'}</h2>
        {error && <p style={{color: 'var(--danger)'}}>{error}</p>}
        <form onSubmit={handleSubmit}>
          <input required placeholder="Username" value={username} onChange={e=>setUsername(e.target.value)} />
          <input required type="password" placeholder="Password" value={password} onChange={e=>setPassword(e.target.value)} />
          <button type="submit">{isLogin ? 'Enter Workspace' : 'Create Credentials'}</button>
        </form>
        <p style={{textAlign: 'center', cursor: 'pointer', color: 'var(--muted)', marginTop: '20px'}} onClick={() => setIsLogin(!isLogin)}>
          {isLogin ? "Need an account? Sign up" : "Already have an account? Log in"}
        </p>
      </div>
    </div>
  );
}
