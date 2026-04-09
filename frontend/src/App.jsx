// App.jsx
// Configures application scaffolding and browser routing mechanisms.
// Orchestrates navigation between Login, Dashboard, and editing sessions.

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './LoginPage';
import RoomPage from './RoomPage';
import EditorPage from './Editor';

function App() {
  return (
    <BrowserRouter>
      <div className="app-container">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/rooms" element={<RoomPage />} />
          <Route path="/editor/:roomId" element={<EditorPage />} />
          <Route path="/" element={<Navigate to="/login" />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
