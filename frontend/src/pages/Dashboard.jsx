import React, { useState, useEffect } from 'react';

const Dashboard = () => {
  const [stats, setStats] = useState({
    totalProducts: 0,
    totalUsers: 0,
    totalSubadmins: 0,
    totalRevenue: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchDashboardStats();
  }, []);

  const fetchDashboardStats = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:5000/api/dashboard/stats', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setStats(data.data);
        } else {
          setError('Failed to fetch dashboard data');
        }
      } else {
        setError('Failed to fetch dashboard data');
      }
    } catch (error) {
      setError('Network error. Please check if backend is running.');
      // Use mock data if backend is not available
      setStats({
        totalProducts: 150,
        totalUsers: 1250,
        totalSubadmins: 15,
        totalRevenue: 45000
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div>
        <h1 className="page-title">Dashboard</h1>
        <p>Loading dashboard data...</p>
      </div>
    );
  }

  return (
    <div>
      <h1 className="page-title">Dashboard</h1>
      {error && (
        <div style={{ color: 'orange', marginBottom: '20px', padding: '10px', background: '#fff3cd', borderRadius: '5px' }}>
          {error} (Showing sample data)
        </div>
      )}
      <div className="dashboard-cards">
        <div className="card">
          <h3>Total Products</h3>
          <p>{stats.totalProducts}</p>
        </div>
        <div className="card">
          <h3>Total Users</h3>
          <p>{stats.totalUsers}</p>
        </div>
        <div className="card">
          <h3>Total Subadmins</h3>
          <p>{stats.totalSubadmins}</p>
        </div>
        <div className="card">
          <h3>Total Revenue</h3>
          <p>${stats.totalRevenue}</p>
        </div>
      </div>
      <div style={{ background: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)' }}>
        <h3>Recent Activity</h3>
        <p>Recent activities will be displayed here...</p>
        <button onClick={fetchDashboardStats} className="btn" style={{ marginTop: '10px', width: 'auto', padding: '8px 16px' }}>
          Refresh Data
        </button>
      </div>
    </div>
  );
};

export default Dashboard;