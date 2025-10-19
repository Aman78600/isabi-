import React, { useState } from 'react';
import ViewTable from './ViewTable';
import AddSuperAdmin from './AddSuperAdmin';
import AddSubadmin from './AddSubadmin';
import AddAIProduct from './AddAIProduct';
import VectorSearch from './VectorSearch';
import UploadDigitalProduct from './UploadDigitalProduct';
import SearchDigitalProduct from './SearchDigitalProduct';

const SuperAdminPanel = () => {
  const [currentPage, setCurrentPage] = useState('viewTable');

  const renderPage = () => {
    switch (currentPage) {
      case 'viewTable':
        return <ViewTable />;
      case 'addSuperAdmin':
        return <AddSuperAdmin />;
      case 'addSubadmin':
        return <AddSubadmin />;
      case 'addAIProduct':
        return <AddAIProduct />;
      case 'vectorSearch':
        return <VectorSearch />;
      case 'uploadDigitalProduct':
        return <UploadDigitalProduct />;
      case 'searchDigitalProduct':
        return <SearchDigitalProduct />;
      default:
        return <ViewTable />;
    }
  };

  return (
    <div className="panel-container">
      <div className="sidebar">
        <h3>Super Admin Panel</h3>
        <ul>
          <li><button className={currentPage === 'viewTable' ? 'active' : ''} onClick={() => setCurrentPage('viewTable')}>View Tables</button></li>
          <li><button className={currentPage === 'addSuperAdmin' ? 'active' : ''} onClick={() => setCurrentPage('addSuperAdmin')}>Add Super Admin</button></li>
          <li><button className={currentPage === 'addSubadmin' ? 'active' : ''} onClick={() => setCurrentPage('addSubadmin')}>Add Sub Admin</button></li>
          <li className="section-divider">AI Training Products</li>
          <li><button className={currentPage === 'addAIProduct' ? 'active' : ''} onClick={() => setCurrentPage('addAIProduct')}>Add AI Product (Course)</button></li>
          <li><button className={currentPage === 'vectorSearch' ? 'active' : ''} onClick={() => setCurrentPage('vectorSearch')}>Vector Search (AI)</button></li>
          <li className="section-divider">Digital Products</li>
          <li><button className={currentPage === 'uploadDigitalProduct' ? 'active' : ''} onClick={() => setCurrentPage('uploadDigitalProduct')}>Upload Digital Product</button></li>
          <li><button className={currentPage === 'searchDigitalProduct' ? 'active' : ''} onClick={() => setCurrentPage('searchDigitalProduct')}>Search Digital Products</button></li>
        </ul>
      </div>
      <div className="main-content">
        {renderPage()}
      </div>
    </div>
  );
};

export default SuperAdminPanel;