// RoomPage.jsx
// A central dashboard where authenticated users can spin up brand-new editor rooms.
// Serves as the primary branching hub prior to jumping into a specific document.

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createRoom } from './api';

export default function RoomPage() {
  const [roomName, setRoomName] = useState('');
  const navigate = useNavigate();

  // Requests the backend to formulate a new document instance.
  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      const res = await createRoom(roomName);
      navigate(`/editor/${res.data.id}`);
    } catch (err) {
      alert("Failed to spawn new room structure.");
    }
  };

  return (
    <div className="room-dashboard">
      <div className="room-header">
        <h1>Your Workspace Control</h1>
        <button onClick={() => {
          localStorage.removeItem('token');
          navigate('/login');
        }}>Log Out</button>
      </div>
      
      <div className="card">
        <h3>Launch New Space</h3>
        <form onSubmit={handleCreate} style={{display:'flex', gap:'12px'}}>
          <input 
            required 
            placeholder="Room Title (e.g. Next Big Feature)" 
            value={roomName} 
            onChange={e => setRoomName(e.target.value)} 
            style={{flex: 1}}
          />
          <button type="submit">Create Space</button>
        </form>
      </div>
      
      <div className="card" style={{marginTop: '20px'}}>
        <h3>Quick Diagnostics / Helpful Debug</h3>
        <p style={{color: 'var(--muted)'}}>
          Direct connections using the raw URL pathing (/editor/UUID) work instantly. 
          Use the dashboard above to formulate a new unique UUID environment first!
        </p>
      </div>
    </div>
  );
}
