import React, { useState } from 'react';

const SearchDigitalProduct = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [numResults, setNumResults] = useState(5);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [searchResults, setSearchResults] = useState(null);

  const handleSearch = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');
    setSearchResults(null);

    try {
      if (!searchQuery.trim()) {
        setMessage('Error: Please enter a search query');
        return;
      }

      const params = new URLSearchParams({
        query: searchQuery,
        n: numResults.toString()
      });

      const response = await fetch(`http://127.0.0.1:8000/api/search-digital-products?${params}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      const data = await response.json();

      if (data.success) {
        setMessage(`Found ${data.total_results} digital products matching your search`);
        setSearchResults(data);
      } else {
        setMessage('Error: ' + (data.message || 'Search failed'));
        setSearchResults(null);
      }
    } catch (error) {
      setMessage('Network error: ' + error.message);
      setSearchResults(null);
    } finally {
      setLoading(false);
    }
  };

  const renderResults = () => {
    if (!searchResults || !searchResults.results || searchResults.results.length === 0) {
      return null;
    }

    return (
      <div className="search-results">
        <h3>Search Results</h3>
        <div className="results-summary">
          <p><strong>Query:</strong> {searchResults.query}</p>
          <p><strong>Total Results:</strong> {searchResults.total_results}</p>
        </div>
        
        <div className="results-grid">
          {searchResults.results.map((result, index) => (
            <div key={index} className="result-card">
              <div className="result-header">
                <span className="result-rank">#{index + 1}</span>
                <span className="similarity-badge">
                  Match: {(result.similarity_score * 100).toFixed(1)}%
                </span>
              </div>
              
              <div className="result-body">
                <h4>{result.product_name}</h4>
                
                <div className="result-info">
                  <div className="info-item">
                    <span className="info-label">Category:</span>
                    <span className="info-value">{result.product_category}</span>
                  </div>
                  
                  <div className="info-item">
                    <span className="info-label">Format:</span>
                    <span className="info-value">{result.file_format.toUpperCase()}</span>
                  </div>
                  
                  <div className="info-item">
                    <span className="info-label">Size:</span>
                    <span className="info-value">{result.product_size_mb.toFixed(2)} MB</span>
                  </div>
                  
                  <div className="info-item">
                    <span className="info-label">Price:</span>
                    <span className="info-value price">${result.price.toFixed(2)}</span>
                  </div>
                </div>
                
                <div className="result-location">
                  <strong>Location:</strong>
                  <div className="location-text">{result.product_location}</div>
                </div>
                
                <div className="result-id">
                  <strong>Product ID:</strong> {result.product_id}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div>
      <h1 className="page-title">Search Digital Products</h1>
      
      <div className="search-container">
        <form onSubmit={handleSearch} className="search-form">
          <div className="search-input-group">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder='Search for products (e.g., "python course", "business template")'
              className="search-input"
              required
            />
            
            <div className="num-results-group">
              <label htmlFor="numResults">Results:</label>
              <input
                type="number"
                id="numResults"
                value={numResults}
                onChange={(e) => setNumResults(parseInt(e.target.value))}
                min="1"
                max="50"
                className="num-results-input"
              />
            </div>
            
            <button type="submit" disabled={loading} className="search-button">
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>
        </form>

        {message && (
          <div className={`message ${message.includes('Error') ? 'error' : 'success'}`}>
            {message}
          </div>
        )}

        {renderResults()}
      </div>

      <style jsx>{`
        .page-title {
          text-align: center;
          color: #333;
          margin-bottom: 30px;
        }

        .search-container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 20px;
        }

        .search-form {
          background-color: #f8f9fa;
          padding: 25px;
          border-radius: 8px;
          margin-bottom: 30px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .search-input-group {
          display: flex;
          gap: 15px;
          align-items: center;
        }

        .search-input {
          flex: 1;
          padding: 12px 15px;
          border: 2px solid #ddd;
          border-radius: 4px;
          font-size: 16px;
          transition: border-color 0.3s;
        }

        .search-input:focus {
          outline: none;
          border-color: #007bff;
        }

        .num-results-group {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .num-results-group label {
          font-weight: bold;
          color: #555;
          white-space: nowrap;
        }

        .num-results-input {
          width: 70px;
          padding: 12px 8px;
          border: 2px solid #ddd;
          border-radius: 4px;
          font-size: 16px;
          text-align: center;
        }

        .search-button {
          padding: 12px 30px;
          background-color: #007bff;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 16px;
          font-weight: bold;
          white-space: nowrap;
          transition: background-color 0.3s;
        }

        .search-button:hover:not(:disabled) {
          background-color: #0056b3;
        }

        .search-button:disabled {
          background-color: #6c757d;
          cursor: not-allowed;
        }

        .message {
          padding: 15px;
          border-radius: 5px;
          margin-bottom: 20px;
        }

        .message.success {
          background-color: #d4edda;
          color: #155724;
          border: 1px solid #c3e6cb;
        }

        .message.error {
          background-color: #f8d7da;
          color: #721c24;
          border: 1px solid #f5c6cb;
        }

        .search-results {
          animation: fadeIn 0.5s;
        }

        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .results-summary {
          background-color: #e3f2fd;
          padding: 15px 20px;
          border-radius: 8px;
          margin-bottom: 25px;
        }

        .results-summary p {
          margin: 5px 0;
          font-size: 14px;
        }

        .results-summary strong {
          color: #1976d2;
        }

        .results-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
          gap: 20px;
        }

        .result-card {
          background: white;
          border: 1px solid #ddd;
          border-radius: 8px;
          overflow: hidden;
          transition: transform 0.2s, box-shadow 0.2s;
        }

        .result-card:hover {
          transform: translateY(-5px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .result-header {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          padding: 15px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .result-rank {
          background-color: rgba(255,255,255,0.3);
          color: white;
          padding: 5px 12px;
          border-radius: 20px;
          font-weight: bold;
          font-size: 14px;
        }

        .similarity-badge {
          background-color: rgba(255,255,255,0.9);
          color: #667eea;
          padding: 5px 12px;
          border-radius: 20px;
          font-weight: bold;
          font-size: 12px;
        }

        .result-body {
          padding: 20px;
        }

        .result-body h4 {
          margin: 0 0 15px 0;
          color: #333;
          font-size: 18px;
        }

        .result-info {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
          margin-bottom: 15px;
        }

        .info-item {
          display: flex;
          flex-direction: column;
          padding: 8px;
          background-color: #f8f9fa;
          border-radius: 4px;
        }

        .info-label {
          font-size: 11px;
          color: #666;
          text-transform: uppercase;
          margin-bottom: 3px;
        }

        .info-value {
          font-size: 14px;
          color: #333;
          font-weight: 600;
        }

        .info-value.price {
          color: #28a745;
          font-size: 16px;
        }

        .result-location {
          margin: 15px 0;
          padding: 10px;
          background-color: #fff3cd;
          border-left: 4px solid #ffc107;
          border-radius: 4px;
        }

        .result-location strong {
          display: block;
          margin-bottom: 5px;
          color: #856404;
        }

        .location-text {
          font-size: 12px;
          color: #666;
          word-break: break-all;
        }

        .result-id {
          font-size: 12px;
          color: #999;
          margin-top: 10px;
          padding-top: 10px;
          border-top: 1px solid #eee;
        }

        @media (max-width: 768px) {
          .search-input-group {
            flex-direction: column;
            align-items: stretch;
          }

          .search-button,
          .num-results-group {
            width: 100%;
          }

          .results-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
};

export default SearchDigitalProduct;
