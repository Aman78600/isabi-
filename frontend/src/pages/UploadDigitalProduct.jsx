import React, { useState } from 'react';

const UploadDigitalProduct = () => {
  const [formData, setFormData] = useState({
    product_name: '',
    product_category: '',
    product_description: '',
    price: '',
    product_file: null
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [responseData, setResponseData] = useState(null);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setFormData(prev => ({
        ...prev,
        product_file: file
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');
    setResponseData(null);

    try {
      // Validate inputs
      if (!formData.product_file) {
        setMessage('Error: Please select a product file');
        return;
      }

      // Get admin info from localStorage
      const adminId = localStorage.getItem('admin_id') || '550e8400-e29b-41d4-a716-446655440000';
      const adminType = localStorage.getItem('admin_type') || 'super_admin';

      // Create FormData for multipart upload
      const submitData = new FormData();
      submitData.append('admin_id', adminId);
      submitData.append('admin_type', adminType);
      submitData.append('product_name', formData.product_name);
      submitData.append('product_category', formData.product_category);
      submitData.append('product_description', formData.product_description);
      submitData.append('price', formData.price);
      submitData.append('product_file', formData.product_file);

      setMessage('Uploading digital product...');

      const response = await fetch('http://127.0.0.1:8000/api/add-digital-product', {
        method: 'POST',
        body: submitData,
      });

      const data = await response.json();

      if (data.success) {
        setMessage('Digital product uploaded successfully!');
        setResponseData(data.data);

        // Reset form
        setFormData({
          product_name: '',
          product_category: '',
          product_description: '',
          price: '',
          product_file: null
        });

        // Reset file input
        const fileInput = document.getElementById('product-file-input');
        if (fileInput) fileInput.value = '';
      } else {
        setMessage('Error: ' + (data.message || 'Unknown error occurred'));
      }
    } catch (error) {
      setMessage('Network error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 className="page-title">Upload Digital Product</h1>
      <div className="product-form">
        {message && (
          <div style={{
            padding: '15px',
            marginBottom: '20px',
            borderRadius: '5px',
            backgroundColor: message.includes('Error') || message.includes('error') ? '#f8d7da' : '#d4edda',
            color: message.includes('Error') || message.includes('error') ? '#721c24' : '#155724',
            border: message.includes('Error') || message.includes('error') ? '1px solid #f5c6cb' : '1px solid #c3e6cb',
          }}>
            {message}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="product_name">Product Name:</label>
            <input
              type="text"
              id="product_name"
              name="product_name"
              value={formData.product_name}
              onChange={handleInputChange}
              required
              placeholder="Enter product name"
            />
          </div>

          <div className="form-group">
            <label htmlFor="product_category">Product Category:</label>
            <input
              type="text"
              id="product_category"
              name="product_category"
              value={formData.product_category}
              onChange={handleInputChange}
              required
              placeholder="e.g., eBook, Software, Template, Course Material"
            />
          </div>

          <div className="form-group">
            <label htmlFor="product_description">Product Description:</label>
            <textarea
              id="product_description"
              name="product_description"
              value={formData.product_description}
              onChange={handleInputChange}
              required
              placeholder="Enter detailed product description (will be used for search)"
              rows="5"
            />
            <small>This description will be embedded into the vector database for search functionality</small>
          </div>

          <div className="form-group">
            <label htmlFor="price">Price (USD):</label>
            <input
              type="number"
              id="price"
              name="price"
              value={formData.price}
              onChange={handleInputChange}
              required
              min="0"
              step="0.01"
              placeholder="0.00"
            />
          </div>

          <div className="form-group">
            <label htmlFor="product_file">Product File (any format):</label>
            <input
              type="file"
              id="product-file-input"
              name="product_file"
              onChange={handleFileChange}
              required
              accept="*/*"
            />
            <small>Supported formats: PDF, ZIP, MP4, DOCX, XLSX, and any other digital format</small>
            {formData.product_file && (
              <div style={{ marginTop: '10px', color: '#28a745' }}>
                Selected: {formData.product_file.name} ({(formData.product_file.size / (1024 * 1024)).toFixed(2)} MB)
              </div>
            )}
          </div>

          <button type="submit" disabled={loading}>
            {loading ? 'Uploading...' : 'Upload Digital Product'}
          </button>
        </form>

        {responseData && (
          <div className="response-data">
            <h3>Upload Details</h3>
            <div className="response-item">
              <strong>Product ID:</strong> {responseData.product_id}
            </div>
            <div className="response-item">
              <strong>Product Name:</strong> {responseData.product_name}
            </div>
            <div className="response-item">
              <strong>Category:</strong> {responseData.product_category}
            </div>
            <div className="response-item">
              <strong>File Size:</strong> {responseData.file_size_mb} MB
            </div>
            <div className="response-item">
              <strong>File Format:</strong> {responseData.file_format}
            </div>
            <div className="response-item">
              <strong>Storage Location:</strong> {responseData.product_location}
            </div>
            <div className="response-item">
              <strong>Vector Index:</strong> {responseData.vector_index}
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .page-title {
          text-align: center;
          color: #333;
          margin-bottom: 30px;
        }

        .product-form {
          max-width: 800px;
          margin: 0 auto;
          padding: 30px;
          background-color: #f9f9f9;
          border-radius: 8px;
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

        .form-group textarea {
          resize: vertical;
        }

        .form-group small {
          display: block;
          margin-top: 5px;
          color: #666;
          font-size: 12px;
        }

        button {
          width: 100%;
          background-color: #28a745;
          color: white;
          padding: 15px;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 16px;
          font-weight: bold;
        }

        button:hover {
          background-color: #218838;
        }

        button:disabled {
          background-color: #6c757d;
          cursor: not-allowed;
        }

        .response-data {
          margin-top: 30px;
          padding: 20px;
          background-color: #e3f2fd;
          border-radius: 8px;
        }

        .response-data h3 {
          margin-top: 0;
          color: #1976d2;
        }

        .response-item {
          margin: 10px 0;
          padding: 8px;
          background-color: white;
          border-radius: 4px;
        }

        .response-item strong {
          color: #333;
          margin-right: 10px;
        }
      `}</style>
    </div>
  );
};

export default UploadDigitalProduct;
