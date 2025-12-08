import React, { useState } from 'react';
import { Upload, X, Eye, FileText, AlertCircle } from 'lucide-react';

interface DocumentUpload {
  file: File | null;
  preview: string | null;
  referenceId: string;
}

interface FormData {
  identityProof: DocumentUpload;
  addressProof: DocumentUpload;
  dobProof: DocumentUpload;
  relationshipProof: DocumentUpload;
}

const Forms = () => {
  const [formData, setFormData] = useState<FormData>({
    identityProof: { file: null, preview: null, referenceId: '' },
    addressProof: { file: null, preview: null, referenceId: '' },
    dobProof: { file: null, preview: null, referenceId: '' },
    relationshipProof: { file: null, preview: null, referenceId: '' },
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleFileUpload = (field: keyof FormData, event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type and size
    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg'];
    const maxSize = 2 * 1024 * 1024; // 2MB

    if (!allowedTypes.includes(file.type)) {
      setErrors({ ...errors, [field]: 'Only PDF, JPEG, PNG, JPG files are allowed' });
      return;
    }

    if (file.size > maxSize) {
      setErrors({ ...errors, [field]: 'File size must be less than 2MB' });
      return;
    }

    // Clear error
    const newErrors = { ...errors };
    delete newErrors[field];
    setErrors(newErrors);

    // Create preview for images
    let preview: string | null = null;
    if (file.type.startsWith('image/')) {
      preview = URL.createObjectURL(file);
    }

    setFormData({
      ...formData,
      [field]: { ...formData[field], file, preview },
    });
  };

  const handleReferenceIdChange = (field: keyof FormData, value: string) => {
    setFormData({
      ...formData,
      [field]: { ...formData[field], referenceId: value },
    });
  };

  const removeFile = (field: keyof FormData) => {
    if (formData[field].preview) {
      URL.revokeObjectURL(formData[field].preview!);
    }
    setFormData({
      ...formData,
      [field]: { file: null, preview: null, referenceId: formData[field].referenceId },
    });
  };

  const handleSubmit = () => {
    // Validation
    const newErrors: Record<string, string> = {};
    if (!formData.identityProof.file) newErrors.identityProof = 'Identity proof is required';
    if (!formData.dobProof.file) newErrors.dobProof = 'DOB proof is required';
    if (!formData.relationshipProof.file) newErrors.relationshipProof = 'Relationship proof is required';

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    console.log('Form submitted:', formData);
    alert('Registration submitted successfully!');
  };

  const DocumentUploadSection: React.FC<{
    title: string;
    field: keyof FormData;
    required?: boolean;
    documentType: string;
  }> = ({ title, field, required = false, documentType }) => {
    const data = formData[field];
    const error = errors[field];

    return (
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="bg-gradient-to-r from-teal-600 to-teal-700 px-6 py-4">
          <h3 className="text-white font-semibold text-lg">
            {title} {required && <span className="text-red-300">*</span>}
          </h3>
        </div>
        
        <div className="p-6">
          <div className="grid md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {documentType}
              </label>
              <select className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent transition">
                <option>{documentType}</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Document Reference Id
              </label>
              <input
                type="text"
                value={data.referenceId}
                onChange={(e) => handleReferenceIdChange(field, e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent transition"
                placeholder="Enter reference ID"
              />
            </div>
          </div>

          {!data.file ? (
            <div className="relative">
              <input
                type="file"
                id={`file-${field}`}
                className="hidden"
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={(e) => handleFileUpload(field, e)}
              />
              <label
                htmlFor={`file-${field}`}
                className="flex items-center justify-center px-6 py-3 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-teal-500 hover:bg-teal-50 transition group"
              >
                <Upload className="w-5 h-5 text-gray-400 group-hover:text-teal-600 mr-2" />
                <span className="text-sm font-medium text-gray-600 group-hover:text-teal-600">
                  BROWSE
                </span>
              </label>
              <p className="text-xs text-gray-500 mt-2">
                Allowed file types: pdf, jpeg, png, jpg | Max size: 2MB
              </p>
            </div>
          ) : (
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200">
              <div className="flex items-center space-x-3">
                {data.preview ? (
                  <img src={data.preview} alt="Preview" className="w-12 h-12 rounded object-cover" />
                ) : (
                  <FileText className="w-12 h-12 text-red-500" />
                )}
                <div>
                  <p className="text-sm font-medium text-gray-900">{data.file.name}</p>
                  <p className="text-xs text-gray-500">
                    {(data.file.size / 1024).toFixed(2)} KB
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                {data.preview && (
                  <button
                    type="button"
                    onClick={() => window.open(data.preview!, '_blank')}
                    className="p-2 text-teal-600 hover:bg-teal-50 rounded-lg transition"
                  >
                    <Eye className="w-5 h-5" />
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => removeFile(field)}
                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center mt-2 text-red-600 text-sm">
              <AlertCircle className="w-4 h-4 mr-1" />
              {error}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
          <div className="bg-gradient-to-r from-teal-600 via-teal-700 to-cyan-600 px-8 py-6">
            <h1 className="text-3xl font-bold text-white">Document Registration</h1>
            <p className="text-teal-100 mt-2">Please upload the required documents to complete your registration</p>
          </div>

          <div className="p-8">
            <div className="grid gap-6">
              <DocumentUploadSection
                title="Identity Proof"
                field="identityProof"
                required
                documentType="Reference Identity"
              />

              <DocumentUploadSection
                title="Address Proof"
                field="addressProof"
                documentType="Address Proof"
              />

              <DocumentUploadSection
                title="DOB Proof"
                field="dobProof"
                required
                documentType="Certificate of Birth"
              />

              <DocumentUploadSection
                title="Relationship Proof"
                field="relationshipProof"
                required
                documentType="Relationship Proof"
              />
            </div>

            <div className="flex justify-between mt-8 pt-6 border-t border-gray-200">
              <button
                onClick={() => window.history.back()}
                className="px-8 py-3 border-2 border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition"
              >
                BACK
              </button>
              <button
                onClick={handleSubmit}
                className="px-8 py-3 bg-gradient-to-r from-teal-600 to-teal-700 text-white rounded-lg font-medium hover:from-teal-700 hover:to-teal-800 transition shadow-lg hover:shadow-xl"
              >
                SUBMIT REGISTRATION
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Forms;