import React, { useState } from 'react';

const AddProduct = () => {
  const [productType, setProductType] = useState(''); // 'digital' or 'ai'
  const [name, setName] = useState('');
  const [category, setCategory] = useState('');
  const [price, setPrice] = useState('');
  const [description, setDescription] = useState('');
  const [file, setFile] = useState(null);
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleDigitalSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      const token = localStorage.getItem('token');
      
      // Create FormData for file upload
      const formData = new FormData();
      formData.append('product_name', name);
      formData.append('product_category', category);
      formData.append('price', price);
      formData.append('description', description);
      formData.append('file', file);

      const response = await fetch('http://localhost:5000/api/products/digital', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json();
      
      if (data.success) {
        setMessage('Digital product created and uploaded successfully!');
        // Reset form
        setName('');
        setCategory('');
        setPrice('');
        setDescription('');
        setFile(null);
        setProductType('');
      } else {
        setMessage('Error: ' + data.message);
      }
    } catch (error) {
      setMessage('Network error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAISubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      const token = localStorage.getItem('token');
      
      // First create the AI training product
      const productResponse = await fetch('http://localhost:5000/api/products/ai-training', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          product_name: name,
          product_category: category,
          price: parseFloat(price),
          number_of_videos: videos.length
        }),
      });

      const productData = await productResponse.json();
      
      if (productData.success) {
        const productId = productData.product_id;
        
        // Now process the videos through AI pipeline
        const formData = new FormData();
        formData.append('product_id', productId);
        formData.append('product_name', name);
        
        // Add all video files
        videos.forEach((video, index) => {
          formData.append('videos', video);
        });
        
        setMessage('Product created! Processing videos through AI pipeline...');
        
        const aiResponse = await fetch('http://127.0.0.1:8000/api/ai-processing/process-ai-product', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
          body: formData,
        });

        const aiData = await aiResponse.json();
        
        if (aiData.success) {
          setMessage(`AI training product created and processed successfully! 
            Course ID: ${aiData.data.course_id}
            Videos processed: ${aiData.data.successful_videos}/${aiData.data.total_videos}
            Embeddings created: ${aiData.data.embeddings_created}
            Root directory: ${aiData.data.root_directory}`);
          
          // Reset form
          setName('');
          setCategory('');
          setPrice('');
          setVideos([]);
          setProductType('');
        } else {
          setMessage('Product created but AI processing failed: ' + aiData.message);
        }
      } else {
        setMessage('Error creating product: ' + productData.message);
      }
    } catch (error) {
      setMessage('Network error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleVideosChange = (e) => {
    setVideos(Array.from(e.target.files));
  };

  return (
    <div>
      <h1 className="page-title">Add Product</h1>
      <div className="product-form">
        {message && (
          <div style={{ 
            padding: '15px', 
            marginBottom: '20px', 
            borderRadius: '5px',
            backgroundColor: message.includes('Error') || message.includes('failed') ? '#f8d7da' : '#d4edda',
            color: message.includes('Error') || message.includes('failed') ? '#721c24' : '#155724',
            border: message.includes('Error') || message.includes('failed') ? '1px solid #f5c6cb' : '1px solid #c3e6cb',
            whiteSpace: 'pre-line',
            fontSize: '14px',
            maxHeight: '200px',
            overflowY: 'auto'
          }}>
            {message}
          </div>
        )}
        <div className="product-options">
          <button
            className={productType === 'digital' ? 'active' : ''}
            onClick={() => setProductType('digital')}
            disabled={loading}
          >
            Upload Digital Product
          </button>
          <button
            className={productType === 'ai' ? 'active' : ''}
            onClick={() => setProductType('ai')}
            disabled={loading}
          >
            Upload AI Product
          </button>
        </div>
        {productType === 'digital' && (
          <form onSubmit={handleDigitalSubmit}>
            <div className="form-group">
              <label>Product Name:</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                disabled={loading}
              />
            </div>
            <div className="form-group">
              <label>Product Category:</label>
              <input
                type="text"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                required
                disabled={loading}
              />
            </div>
            <div className="form-group">
              <label>Product Description:</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Enter a short description of the digital product..."
                required
                disabled={loading}
                rows="4"
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
              <label>Product File:</label>
              <input
                type="file"
                onChange={handleFileChange}
                required
                className="file-input"
                disabled={loading}
              />
            </div>
            <div className="form-group">
              <label>Product Price ($):</label>
              <input
                type="number"
                step="0.01"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                required
                disabled={loading}
              />
            </div>
            <button type="submit" className="btn" disabled={loading}>
              {loading ? 'Creating...' : 'Submit'}
            </button>
          </form>
        )}
        {productType === 'ai' && (
          <form onSubmit={handleAISubmit}>
            <div className="form-group">
              <label>Product Name:</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                disabled={loading}
              />
            </div>
            <div className="form-group">
              <label>Product Category:</label>
              <input
                type="text"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                required
                disabled={loading}
              />
            </div>
            <div className="form-group">
              <label>Upload All Videos:</label>
              <input
                type="file"
                multiple
                accept="video/*"
                onChange={handleVideosChange}
                required
                className="file-input"
                disabled={loading}
              />
              {videos.length > 0 && <p>Selected {videos.length} video(s)</p>}
            </div>
            <div className="form-group">
              <label>Product Price ($):</label>
              <input
                type="number"
                step="0.01"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                required
                disabled={loading}
              />
            </div>
            <button type="submit" className="btn" disabled={loading}>
              {loading ? 'Processing...' : 'Submit'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default AddProduct;