import { useState } from 'react';
import axios from 'axios';

export default function Home() {
  const [file, setFile] = useState(null);
  const [results, setResults] = useState([]);
  const [downloadLink, setDownloadLink] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [processedBatches, setProcessedBatches] = useState(new Set());

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) {
      alert('Please select a file.');
      return;
    }

    setIsProcessing(true);
    setResults([]);
    setProgress(0);
    const processedIds = new Set();
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post('http://127.0.0.1:8000/uploadfile/', formData, {
        onDownloadProgress: (progressEvent) => {
          const chunk = progressEvent.event.target.responseText;
          try {
            // Split the chunk by newlines and process each line
            const lines = chunk.split('\n').filter(line => line.trim() !== '');
            
            for (const line of lines) {
              const data = JSON.parse(line);
              
              // Skip if we've already processed this message
              if (processedIds.has(data.id)) {
                continue;
              }
              processedIds.add(data.id);

              if (data.batch) {
                setProgress((data.batch / data.total_batches) * 100);
                
                setResults(prev => [
                  ...prev,
                  {
                    id: data.id,
                    type: 'progress',
                    message: data.message,
                    data: data.batch_result,
                  }
                ]);
              } else if (data.message) {
                setResults(prev => [
                  ...prev,
                  {
                    id: data.id,
                    type: 'completion',
                    message: data.message,
                  }
                ]);
              }
            }
          } catch (error) {
            console.error('Error parsing JSON:', error);
          }
        },
        responseType: 'text',
      });

      setDownloadLink(`http://127.0.0.1:8000/downloadfile/${file.name.replace('.xlsx', '_ui_output.xlsx')}`);
    } catch (error) {
      console.error('Error:', error);
      alert('An error occurred while processing the file.');
    } finally {
      setIsProcessing(false);
    }
  };

  // Update the render function to use unique IDs
  const renderResultItem = (result) => {
    switch (result.type) {
      case 'progress':
        return (
          <div key={result.id} className="result-item progress">
            <pre>{result.message}</pre>
            {result.data && (
              <pre className="batch-data">
                {JSON.stringify(result.data, null, 2)}
              </pre>
            )}
          </div>
        );
      case 'completion':
        return (
          <div key={result.id} className="result-item completion">
            <pre>{result.message}</pre>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto', fontFamily: 'Arial, sans-serif' }}>
      <h1 style={{ textAlign: 'center', marginBottom: '20px', color: '#333', fontSize: '2rem', fontWeight: 'bold' }}>Excel File Processor</h1>

      {/* File Upload Section */}
      <div style={{ marginBottom: '20px', textAlign: 'center' }}>
        <input
          type="file"
          accept=".xlsx"
          onChange={handleFileChange}
          disabled={isProcessing}
          style={{ marginBottom: '10px', padding: '10px', border: '1px solid #ccc', borderRadius: '5px', width: '100%', maxWidth: '400px' }}
        />
        <button
          onClick={handleUpload}
          disabled={isProcessing}
          style={{
            padding: '10px 20px',
            backgroundColor: isProcessing ? '#ccc' : '#0070f3',
            color: '#fff',
            border: 'none',
            borderRadius: '5px',
            cursor: 'pointer',
            fontSize: '1rem',
            fontWeight: 'bold',
          }}
        >
          {isProcessing ? 'Processing...' : 'Upload and Process'}
        </button>
      </div>

      {/* Progress Bar */}
      {isProcessing && (
        <div style={{ marginBottom: '20px' }}>
          <div style={{ width: '100%', backgroundColor: '#f0f0f0', borderRadius: '5px', overflow: 'hidden' }}>
            <div
              style={{
                width: `${progress}%`,
                height: '10px',
                backgroundColor: '#0070f3',
                transition: 'width 0.3s ease',
              }}
            ></div>
          </div>
          <div style={{ textAlign: 'center', marginTop: '5px', color: '#555' }}>{progress.toFixed(2)}%</div>
        </div>
      )}

      {/* Results Section */}
      <div style={{ marginBottom: '20px' }}>
        <h2 style={{ color: '#333', marginBottom: '10px', fontSize: '1.5rem', fontWeight: 'bold' }}>Processing Results:</h2>
        <div
          style={{
            backgroundColor: '#f9f9f9',
            padding: '10px',
            borderRadius: '5px',
            maxHeight: '300px',
            overflowY: 'auto',
          }}
        >
          {results.map((result) => renderResultItem(result))}
        </div>
      </div>

      {/* Download Section */}
      {downloadLink && (
        <div style={{ marginBottom: '20px', textAlign: 'center' }}>
          <h2 style={{ color: '#333', marginBottom: '10px', fontSize: '1.5rem', fontWeight: 'bold' }}>Download Processed File:</h2>
          <a
            href={downloadLink}
            download
            style={{
              padding: '10px 20px',
              backgroundColor: '#28a745',
              color: '#fff',
              textDecoration: 'none',
              borderRadius: '5px',
              display: 'inline-block',
              fontSize: '1rem',
              fontWeight: 'bold',
            }}
          >
            Download Excel File
          </a>
        </div>
      )}

      {/* Plot Section */}
      {downloadLink && (
        <div style={{ textAlign: 'center' }}>
          <h2 style={{ color: '#333', marginBottom: '10px', fontSize: '1.5rem', fontWeight: 'bold' }}>Generated Plot:</h2>
          <img
            src={`http://127.0.0.1:8000/uploads/plot.png?${new Date().getTime()}`}  // Add timestamp to avoid caching
            alt="Generated Plot"
            style={{ maxWidth: '100%', borderRadius: '5px', border: '1px solid #ddd' }}
          />
        </div>
      )}
    </div>
  );
}