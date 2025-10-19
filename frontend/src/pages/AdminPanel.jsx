import React, { useState } from 'react';
import ViewTable from './ViewTable';
import AddSubadmin from './AddSubadmin';
import VectorSearch from './VectorSearch';

const SubAdminPanel = () => {
  const [currentPage, setCurrentPage] = useState('viewTable');

  const renderPage = () => {
    switch (currentPage) {
      case 'viewTable':
        return <ViewTable />;
      case 'addSubadmin':
        return <AddSubadmin />;
      case 'vectorSearch':
        return <VectorSearch />;
      default:
        return <ViewTable />;
    }
  };

  return (
    <div className="panel-container">
      <div className="sidebar">
        <h3>Sub Admin Panel</h3>
        <ul>
          <li><button className={currentPage === 'viewTable' ? 'active' : ''} onClick={() => setCurrentPage('viewTable')}>View Tables</button></li>
          <li><button className={currentPage === 'addSubadmin' ? 'active' : ''} onClick={() => setCurrentPage('addSubadmin')}>Add Sub Admin</button></li>
          <li><button className={currentPage === 'vectorSearch' ? 'active' : ''} onClick={() => setCurrentPage('vectorSearch')}>Vector Search</button></li>
        </ul>
      </div>
      <div className="main-content">
        {renderPage()}
      </div>
    </div>
  );
};

export default SubAdminPanel;