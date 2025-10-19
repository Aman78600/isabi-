import React, { useState, useEffect } from 'react';

const VectorSearch = () => {
  const [formData, setFormData] = useState({
    question: '',
    product_ids: '',
    n: 5
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [availableProducts, setAvailableProducts] = useState([]);

  // Fetch available products on component mount
  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/products');
      const data = await response.json();
      
      if (data.success) {
        setAvailableProducts(data.products);
      } else {
        console.error('Failed to fetch products:', data.message);
      }
    } catch (error) {
      console.error('Error fetching products:', error);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');
    setSearchResults(null);

    try {
      if (!formData.question.trim()) {
        setMessage('Error: Please enter a search question');
        return;
      }

      if (!formData.product_ids.trim()) {
        setMessage('Error: Please enter at least one product ID');
        return;
      }

      const params = new URLSearchParams({
        question: formData.question,
        product_ids: formData.product_ids,
        n: formData.n.toString()
      });

      const response = await fetch(`http://127.0.0.1:8000/api/search-vectors?${params}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      const data = await response.json();

      if (data.success) {
        setMessage(`Found ${data.total_results} results for your search`);
        setSearchResults(data);
      } else {
        setMessage('Error: ' + (data.message || 'Search failed'));
      }
    } catch (error) {
      setMessage('Network error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const renderResults = () => {
    if (!searchResults || !searchResults.results) return null;

    return (
      <div className="search-results">
        <h3>Search Results</h3>
        <div className="results-summary">
          <p><strong>Query:</strong> {searchResults.query}</p>
          <p><strong>Product IDs:</strong> {searchResults.product_ids.join(', ')}</p>
          <p><strong>Total Results:</strong> {searchResults.total_results}</p>
        </div>
        
        <div className="results-list">
          {searchResults.results.map((result, index) => (
            <div key={index} className="result-item">
              <div className="result-header">
                <span className="result-rank">#{index + 1}</span>
                <span className="similarity-score">
                  Similarity: {(result.similarity_score * 100).toFixed(2)}%
                </span>
              </div>
              
              <div className="result-content">
                <h4>Content</h4>
                <p>{result.content}</p>
              </div>
              
              <div className="result-metadata">
                <div className="metadata-item">
                  <strong>Product ID:</strong> {result.product_id}
                </div>
                <div className="metadata-item">
                  <strong>Source File:</strong> {result.source_file}
                </div>
                <div className="metadata-item">
                  <strong>Lesson:</strong> {result.lesson_no}
                </div>
                <div className="metadata-item">
                  <strong>Page:</strong> {result.page}
                </div>
                <div className="metadata-item">
                  <strong>Vector ID:</strong> {result.vector_id}
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
      <h1 className="page-title">Vector Search</h1>
      
      <div className="search-form">
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="question">Search Question:</label>
            <textarea
              id="question"
              name="question"
              value={formData.question}
              onChange={handleInputChange}
              placeholder="Enter your search question..."
              rows="3"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="product_ids">Product IDs (comma-separated):</label>
            <input
              type="text"
              id="product_ids"
              name="product_ids"
              value={formData.product_ids}
              onChange={handleInputChange}
              placeholder="e.g., 1,2,3 or just 1"
              required
            />
            <small>Enter the product IDs you want to search in, separated by commas</small>
          </div>

          <div className="form-group">
            <label htmlFor="n">Number of Results:</label>
            <input
              type="number"
              id="n"
              name="n"
              value={formData.n}
              onChange={handleInputChange}
              min="1"
              max="50"
              required
            />
          </div>

          <button type="submit" disabled={loading}>
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>

        {message && (
          <div style={{
            padding: '15px',
            marginTop: '20px',
            borderRadius: '5px',
            backgroundColor: message.includes('Error') || message.includes('error') ? '#f8d7da' : '#d4edda',
            color: message.includes('Error') || message.includes('error') ? '#721c24' : '#155724',
            border: message.includes('Error') || message.includes('error') ? '1px solid #f5c6cb' : '1px solid #c3e6cb',
          }}>
            {message}
          </div>
        )}
      </div>

      {/* Available Products Reference */}
      {availableProducts.length > 0 && (
        <div className="available-products">
          <h3>Available Products</h3>
          <div className="products-list">
            {availableProducts.map((product) => (
              <div key={product.product_id} className="product-item">
                <div><strong>ID:</strong> {product.product_id}</div>
                <div><strong>Name:</strong> {product.product_name}</div>
                <div><strong>Category:</strong> {product.product_category}</div>
                <div><strong>Videos:</strong> {product.number_of_videos}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {renderResults()}

      <style jsx>{`
        .search-form {
          max-width: 800px;
          margin: 0 auto;
          padding: 20px;
          background-color: #f9f9f9;
          border-radius: 8px;
          margin-bottom: 30px;
        }

        .form-group {
          margin-bottom: 20px;
        }

        .form-group label {
          display: block;
          margin-bottom: 5px;
          font-weight: bold;
          color: #333;
        }

        .form-group input,
        .form-group textarea {
          width: 100%;
          padding: 10px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 14px;
          box-sizing: border-box;
        }

        .form-group small {
          display: block;
          margin-top: 5px;
          color: #666;
          font-size: 12px;
        }

        button {
          background-color: #007bff;
          color: white;
          padding: 12px 24px;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 16px;
        }

        button:hover {
          background-color: #0056b3;
        }

        button:disabled {
          background-color: #6c757d;
          cursor: not-allowed;
        }

        .available-products {
          margin: 30px 0;
          padding: 20px;
          background-color: #f8f9fa;
          border-radius: 8px;
        }

        .products-list {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 15px;
          margin-top: 15px;
        }

        .product-item {
          padding: 15px;
          background-color: white;
          border: 1px solid #dee2e6;
          border-radius: 4px;
          font-size: 14px;
        }

        .search-results {
          margin-top: 30px;
        }

        .results-summary {
          background-color: #e3f2fd;
          padding: 15px;
          border-radius: 8px;
          margin-bottom: 20px;
        }

        .results-summary p {
          margin: 5px 0;
        }

        .results-list {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .result-item {
          border: 1px solid #ddd;
          border-radius: 8px;
          padding: 20px;
          background-color: white;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .result-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 15px;
          padding-bottom: 10px;
          border-bottom: 1px solid #eee;
        }

        .result-rank {
          background-color: #007bff;
          color: white;
          padding: 4px 8px;
          border-radius: 4px;
          font-weight: bold;
        }

        .similarity-score {
          background-color: #28a745;
          color: white;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
        }

        .result-content {
          margin-bottom: 15px;
        }

        .result-content h4 {
          margin: 0 0 10px 0;
          color: #333;
        }

        .result-content p {
          line-height: 1.6;
          color: #555;
          background-color: #f8f9fa;
          padding: 10px;
          border-radius: 4px;
          border-left: 4px solid #007bff;
        }

        .result-metadata {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 10px;
          margin-top: 15px;
          padding-top: 15px;
          border-top: 1px solid #eee;
        }

        .metadata-item {
          font-size: 12px;
          color: #666;
        }

        .metadata-item strong {
          color: #333;
        }

        .page-title {
          text-align: center;
          color: #333;
          margin-bottom: 30px;
        }
      `}</style>
    </div>
  );
};

export default VectorSearch;