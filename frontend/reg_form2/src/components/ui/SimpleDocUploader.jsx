import React, { useState } from 'react';

const SimpleDocUploader = ({ label, onUpload, required }) => {
  const [fileName, setFileName] = useState("");

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setFileName(file.name);
      // Pass the file back to the parent component
      if (onUpload) {
        onUpload(file);
      }
    }
  };

  return (
    <div className="flex flex-col gap-2 mb-4">
      {/* Label */}
      <label className="text-gray-700 font-semibold text-sm">
        {label} {required && <span className="text-red-500">*</span>}
      </label>

      {/* Upload Box */}
      <div className="flex items-center gap-4">
        <label className="flex-shrink-0 cursor-pointer">
          <span className="px-4 py-2 bg-gray-100 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-200 transition-colors text-sm font-medium">
            Choose File
          </span>
          <input 
            type="file" 
            className="hidden" 
            accept="image/*,.pdf" // Optional: Restrict to images/pdf
            onChange={handleFileChange} 
          />
        </label>

        {/* Display File Name or Placeholder */}
        <span className="text-sm text-gray-500 italic truncate max-w-xs">
          {fileName || "No file selected"}
        </span>
      </div>
    </div>
  );
};

export default SimpleDocUploader;