import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import SuperAdminLogin from './pages/SuperAdminLogin';
import SubAdminLogin from './pages/SubAdminLogin';
import SuperAdminPanel from './pages/SuperAdminPanel';
import SubAdminPanel from './pages/SubAdminPanel';
import VectorSearch from './pages/VectorSearch';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/super-admin-login" element={<SuperAdminLogin />} />
          <Route path="/sub-admin-login" element={<SubAdminLogin />} />
          <Route path="/super-admin-panel" element={<SuperAdminPanel />} />
          <Route path="/sub-admin-panel" element={<SubAdminPanel />} />
          <Route path="/vector-search" element={<VectorSearch />} />
          <Route path="/" element={<SuperAdminLogin />} /> {/* Default to super admin login */}
        </Routes>
      </div>
    </Router>
  );
}

export default App;
