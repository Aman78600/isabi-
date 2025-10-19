import React, { useState } from 'react';

const ViewTable = () => {
  const [selectedTable, setSelectedTable] = useState('');
  const [tableData, setTableData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const tables = [
    'super_admins', 'sub_admins', 'users', 'product_types', 'products',
    'digital_products', 'ai_train_products', 'ai_train_product_details',
    'payments', 'user_purchases', 'user_activity_log', 'sub_admin_activity_log',
    'super_admin_activity_log', 'chat_sessions', 'vector_metadata'
  ];

  const fetchTableData = async () => {
    if (!selectedTable) return;

    setLoading(true);
    setError('');

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`http://localhost:5000/admin/view_table?table=${selectedTable}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (response.ok) {
        setTableData(data.data || []);
      } else {
        setError(data.error || 'Failed to fetch data');
      }
    } catch (error) {
      setError('Network error. Please check if backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleTableChange = (e) => {
    setSelectedTable(e.target.value);
    setTableData([]);
    setError('');
  };

  const handleView = () => {
    fetchTableData();
  };

  return (
    <div className="view-table-container">
      <h2>View Table Data</h2>
      <div className="form-group">
        <label>Select Table:</label>
        <select value={selectedTable} onChange={handleTableChange}>
          <option value="">-- Select a table --</option>
          {tables.map(table => (
            <option key={table} value={table}>{table}</option>
          ))}
        </select>
        <button onClick={handleView} disabled={!selectedTable || loading} className="btn">
          {loading ? 'Loading...' : 'View Data'}
        </button>
      </div>
      {error && <div className="error-message">{error}</div>}
      {tableData.length > 0 && (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                {Object.keys(tableData[0]).map(key => (
                  <th key={key}>{key}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tableData.map((row, index) => (
                <tr key={index}>
                  {Object.values(row).map((value, i) => (
                    <td key={i}>{String(value)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default ViewTable;