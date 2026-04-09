// Editor.jsx
// The main heavy-lifting page featuring Microsoft's Monaco IDE framework.
// Computes local CRDT actions, injects networked changes rapidly, and updates layout.

import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import { SocketManager } from './socket';

export default function EditorPage() {
  const { roomId } = useParams();
  const navigate = useNavigate();
  const editorRef = useRef(null);
  const managerRef = useRef(null);
  const skipInternalChange = useRef(false);
  const [online, setOnline] = useState(false);
  const [users, setUsers] = useState([]);
  
  // Custom simple CRDT representation in browser memory maps exactly to Python server mapping.
  const crdtDoc = useRef([]);
  const logicalClock = useRef(0);
  const siteId = useRef('u_' + Math.random().toString(36).substr(2, 5));

  // Rebuilds the plain visual text inside Monaco based on active, non-tombstoned CRDT elements.
  const syncEditorValue = () => {
    if (!editorRef.current) return;
    const currentText = crdtDoc.current.filter(c => !c.deleted).map(c => c.char).join("");
    skipInternalChange.current = true;
    
    // We fetch current monaco cursor so we don't accidentally reset the user's cursor mapping position.
    const position = editorRef.current.getPosition();
    editorRef.current.setValue(currentText);
    if(position) editorRef.current.setPosition(position);
    skipInternalChange.current = false;
  };

  // Mounts the WebSocket socket pipe right when the container appears on screen safely.
  useEffect(() => {
    const token = localStorage.getItem('token');
    const user = localStorage.getItem('username');
    if (!token) {
        navigate('/login');
        return;
    }

    const wsUrl = `ws://localhost:8000/ws/${roomId}/${user}_${siteId.current}`;
    managerRef.current = new SocketManager(wsUrl, handleSocketMessage, setOnline);

    return () => { if (managerRef.current?.ws) managerRef.current.ws.close(); };
  }, [roomId, navigate]);

  // Evaluates and applies remote incoming changes onto the internal CRDT mapping buffer layout.
  const handleSocketMessage = (msg) => {
    if (msg.type === "user_joined" || msg.type === "user_left") {
      setUsers(prev => {
        if (msg.type === "user_left") return prev.filter(u => u !== msg.user_id);
        if (!prev.includes(msg.user_id)) return [...prev, msg.user_id];
        return prev;
      });
      return;
    }
    
    if (msg.type === "insert") {
      let idx = 0;
      if (msg.after_id !== null) {
        const found = crdtDoc.current.findIndex(c => c.id === msg.after_id);
        if (found !== -1) idx = found + 1;
      }
      while (idx < crdtDoc.current.length && crdtDoc.current[idx].id > msg.char_obj.id) idx++;
      crdtDoc.current.splice(idx, 0, msg.char_obj);
    } else if (msg.type === "delete") {
      const idx = crdtDoc.current.findIndex(c => c.id === msg.char_obj.id);
      if (idx !== -1) crdtDoc.current[idx].deleted = true;
    }
    syncEditorValue();
  };

  // Captures local developer keystrokes out of Monaco, calculates diffs cleanly, and broadcasts it outward via Socket.
  const handleEditorChange = (value, event) => {
    if (skipInternalChange.current) return;
    
    const changes = event.changes[0];
    const offset = changes.rangeOffset;
    
    // Deletion parsing
    if (changes.text === "") {
        let activeChars = 0, crdtIdx = 0;
        let deleteLength = changes.rangeLength;
        
        while (crdtIdx < crdtDoc.current.length && deleteLength > 0) {
            if (!crdtDoc.current[crdtIdx].deleted) {
                if (activeChars >= offset) {
                    crdtDoc.current[crdtIdx].deleted = true;
                    const op = { type: 'delete', char_obj: crdtDoc.current[crdtIdx], room_id: roomId };
                    managerRef.current.send(op);
                    deleteLength--;
                } else {
                    activeChars++;
                }
            }
            crdtIdx++;
        }
    } 
    // Insertion parsing
    else {
        let activeChars = 0, crdtIdx = 0, prevCrdtId = null;
        while (crdtIdx < crdtDoc.current.length && activeChars < offset) {
            if (!crdtDoc.current[crdtIdx].deleted) activeChars++;
            prevCrdtId = crdtDoc.current[crdtIdx].id;
            crdtIdx++;
        }
        
        for (let i = 0; i < changes.text.length; i++) {
            logicalClock.current++;
            const char_obj = { id: `${siteId.current}_${logicalClock.current}`, char: changes.text[i], deleted: false };
            crdtDoc.current.splice(crdtIdx + i, 0, char_obj);
            managerRef.current.send({ type: 'insert', char_obj, after_id: prevCrdtId, room_id: roomId });
            prevCrdtId = char_obj.id;
        }
    }
  };

  return (
    <div style={{display: 'flex', flexDirection: 'column', height: '100vh'}}>
      <div className="editor-navbar">
        <div style={{display: 'flex', alignItems: 'center'}}>
          <div className={`connection-dot ${!online ? 'offline-dot' : ''}`} />
          <h3 style={{margin: 0}}>Room {roomId.substring(0,8)}</h3>
        </div>
        <div className="active-users-bar">
          {users.map(u => {
              const displayInfo = u.split('_')[0];
              return (
                  <div key={u} className="user-avatar" style={{backgroundColor: `#${displayInfo.charCodeAt(0).toString(16)}00`}} title={displayInfo}>
                    {displayInfo.charAt(0).toUpperCase()}
                  </div>
              );
          })}
        </div>
      </div>
      <Editor
        height="calc(100vh - 50px)"
        defaultLanguage="javascript"
        theme="vs-dark"
        onChange={handleEditorChange}
        onMount={(e) => { editorRef.current = e; }}
        options={{ minimap: { enabled: false }, fontSize: 16 }}
      />
    </div>
  );
}
