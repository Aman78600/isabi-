import React, { useState } from 'react';

const AddAIProduct = () => {
  const [formData, setFormData] = useState({
    product_name: '',
    product_category: '',
    suggestion_questions: '',
    price: '',
    videos: []
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

  const handleVideosChange = (e) => {
    const files = Array.from(e.target.files);
    setFormData(prev => ({
      ...prev,
      videos: files
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');
    setResponseData(null);

    try {
      // Get admin info from localStorage (assuming it's stored during login)
      const adminId = localStorage.getItem('admin_id') || '550e8400-e29b-41d4-a716-446655440000'; // Default UUID if not set
      const adminType = localStorage.getItem('admin_type') || 'super_admin';

      // Create FormData for multipart upload
      const submitData = new FormData();
      submitData.append('admin_id', adminId);
      submitData.append('admin_type', adminType);
      submitData.append('product_name', formData.product_name);
      submitData.append('product_category', formData.product_category);
      submitData.append('suggestion_questions', formData.suggestion_questions);
      submitData.append('price', formData.price);

      // Add all video files
      formData.videos.forEach((video) => {
        submitData.append('videos', video);
      });

      setMessage('Processing AI training product... This may take several minutes.');

      const response = await fetch('http://127.0.0.1:8000/api/add-ai-train-product', {
        method: 'POST',
        body: submitData,
      });

      const data = await response.json();

      if (data.success) {
        setMessage('AI training product created and processed successfully!');
        setResponseData(data.data);

        // Reset form
        setFormData({
          product_name: '',
          product_category: '',
          suggestion_questions: '',
          price: '',
          videos: []
        });

        // Reset file input
        const fileInput = document.getElementById('videos-input');
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
      <h1 className="page-title">Add AI Product (Course)</h1>
      <div className="product-form">
        {message && (
          <div style={{
            padding: '15px',
            marginBottom: '20px',
            borderRadius: '5px',
            backgroundColor: message.includes('Error') || message.includes('error') ? '#f8d7da' : '#d4edda',
            color: message.includes('Error') || message.includes('error') ? '#721c24' : '#155724',
            border: message.includes('Error') || message.includes('error') ? '1px solid #f5c6cb' : '1px solid #c3e6cb',
            whiteSpace: 'pre-line',
            fontSize: '14px',
            maxHeight: '200px',
            overflowY: 'auto'
          }}>
            {message}
          </div>
        )}

        {responseData && (
          <div style={{
            padding: '15px',
            marginBottom: '20px',
            borderRadius: '5px',
            backgroundColor: '#e7f3ff',
            border: '1px solid #b3d9ff',
            fontSize: '14px'
          }}>
            <h3 style={{ marginTop: 0, color: '#0066cc' }}>Processing Results:</h3>
            <p><strong>Product ID:</strong> {responseData.product_id}</p>
            <p><strong>Product Name:</strong> {responseData.product_name}</p>
            <p><strong>Bucket Root:</strong> {responseData.bucket_root}</p>
            <p><strong>Vector Index:</strong> {responseData.vector_index}</p>
            <p><strong>Videos Processed:</strong> {responseData.number_of_videos}</p>
            <p><strong>Total Vectors Created:</strong> {responseData.total_vectors}</p>

            {responseData.items && responseData.items.length > 0 && (
              <div>
                <h4>Processed Videos:</h4>
                <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                  {responseData.items.map((item, index) => (
                    <div key={index} style={{
                      border: '1px solid #ddd',
                      padding: '10px',
                      marginBottom: '10px',
                      borderRadius: '5px',
                      backgroundColor: '#f9f9f9'
                    }}>
                      <p><strong>Lesson Title:</strong> {item.lesson_title}</p>
                      <p><strong>Video:</strong> {item.video_gcs}</p>
                      <p><strong>Audio:</strong> {item.audio_gcs}</p>
                      <p><strong>Text:</strong> {item.text_gcs}</p>
                      <p><strong>PDF:</strong> {item.pdf_gcs}</p>
                      <p><strong>Vectors Created:</strong> {item.vectors ? item.vectors.length : 0}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Product Name:</label>
            <input
              type="text"
              name="product_name"
              value={formData.product_name}
              onChange={handleInputChange}
              required
              disabled={loading}
              placeholder="Enter AI training product name"
            />
          </div>

          <div className="form-group">
            <label>Product Category:</label>
            <input
              type="text"
              name="product_category"
              value={formData.product_category}
              onChange={handleInputChange}
              required
              disabled={loading}
              placeholder="e.g., Python Programming, Data Science, etc."
            />
          </div>

          <div className="form-group">
            <label>Suggestion Questions:</label>
            <textarea
              name="suggestion_questions"
              value={formData.suggestion_questions}
              onChange={handleInputChange}
              disabled={loading}
              rows="4"
              placeholder="Enter JSON array of suggestion questions or plain text (optional)"
              style={{
                width: '100%',
                padding: '10px',
                border: '1px solid #ddd',
                borderRadius: '5px',
                fontSize: '14px',
                resize: 'vertical'
              }}
            />
          </div>

          <div className="form-group">
            <label>Upload Videos:</label>
            <input
              id="videos-input"
              type="file"
              multiple
              accept="video/*"
              onChange={handleVideosChange}
              required
              className="file-input"
              disabled={loading}
            />
            {formData.videos.length > 0 && (
              <div style={{ marginTop: '10px' }}>
                <p>Selected {formData.videos.length} video(s):</p>
                <ul style={{ fontSize: '12px', color: '#666' }}>
                  {formData.videos.map((video, index) => (
                    <li key={index}>{video.name} ({(video.size / 1024 / 1024).toFixed(2)} MB)</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="form-group">
            <label>Product Price ($):</label>
            <input
              type="number"
              name="price"
              step="0.01"
              min="0"
              value={formData.price}
              onChange={handleInputChange}
              required
              disabled={loading}
              placeholder="0.00"
            />
          </div>

          <button type="submit" className="btn" disabled={loading}>
            {loading ? 'Processing AI Product...' : 'Create AI Training Product'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default AddAIProduct;