import React, { useState, useEffect } from 'react';
import { Upload, X, Eye, FileText, AlertCircle, Paperclip, CheckSquare, Square, ChevronDown } from 'lucide-react';
import { PDFDocument, rgb } from 'pdf-lib';
import './forms.css';
import { Viewer, SpecialZoomLevel } from '@react-pdf-viewer/core';
import { fullScreenPlugin } from '@react-pdf-viewer/full-screen';
import '@react-pdf-viewer/full-screen/lib/styles/index.css';
import '@react-pdf-viewer/core/lib/styles/index.css';

const DOC_OPTIONS = {
  identity: ['Aadhaar Card', 'Driving License', 'Passport', 'Voter ID', 'PAN Card'],
  dob: ['Birth Certificate', 'SSLC Marks Card', 'Passport', 'Aadhaar Card'],
  address: ['Aadhaar Card', 'Driving License', 'Passport', 'Utility Bill', 'Rent Agreement']
};


// Reusable Component for Input Fields (Moved Outside)
const InputField = ({ label, name, value, onChange, type = "text", required = false, width = "full" }) => (
  <div className={`flex flex-col ${width === "half" ? "md:w-1/2" : "w-full"}`}>
    <label className="text-sm font-medium text-gray-700 mb-1">
      {label} {required && <span className="text-red-500">*</span>}
    </label>
    <input
      type={type}
      name={name}
      value={value}
      onChange={onChange}
      className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none transition"
    />
  </div>
);

// Reusable Document Selector Component (Moved Outside)
const DocumentSelector = ({ docKey, label, options, required = false, doc, onTypeChange, onUpload, onOpen, onRemove }) => {
  return (
    
    <div className="mt-3 p-4 bg-gray-50 rounded-lg border border-gray-200 transition-all hover:border-teal-300">
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          <div className="w-full sm:w-1/2">
              <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">
                  {label} Type {required && <span className="text-red-500">*</span>}
              </label>
              <div className="relative">
                  <select
                      value={doc?.docType || ''}
                      onChange={(e) => onTypeChange(docKey, e.target.value)}
                      className="w-full pl-3 pr-8 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-teal-500 outline-none bg-white appearance-none cursor-pointer"
                  >
                      <option value="">Select Document...</option>
                      {options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                  </select>
                  <ChevronDown className="absolute right-2 top-2.5 w-4 h-4 text-gray-400 pointer-events-none" />
              </div>
          </div>

          <div className="w-full sm:w-auto">
              <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5 sm:invisible">
                  Action
              </label>
              
              <div className="flex items-center space-x-2">
                  <input
                      type="file"
                      id={docKey}
                      className="hidden"
                      accept=".pdf,.jpg,.jpeg,.png"
                      onChange={(e) => onUpload(docKey, e)}
                      disabled={!doc?.docType}
                  />
                  
                  {!doc?.file ? (
                  <label
                      htmlFor={docKey}
                      className={`flex items-center justify-center px-4 py-2 rounded-md border text-sm font-medium transition-all w-full sm:w-auto ${
                      !doc?.docType 
                          ? 'bg-gray-100 text-gray-400 cursor-not-allowed border-gray-200' 
                          : 'bg-white text-teal-700 border-teal-200 hover:bg-teal-50 hover:border-teal-300 cursor-pointer shadow-sm'
                      }`}
                      title={!doc?.docType ? "Please select a document type first" : "Upload document"}
                  >
                      <Paperclip className="w-4 h-4 mr-2" />
                      {doc?.docType ? 'Upload File' : 'Select Type First'}
                  </label>
                  ) : (
                      <div className="flex items-center bg-white px-3 py-1.5 rounded-md border border-green-200 shadow-sm">
                          <CheckSquare className="w-4 h-4 text-green-600 mr-2" />
                          <div className="flex flex-col mr-3">
                              <span className="text-[10px] text-gray-500 uppercase font-bold">{doc.docType}</span>
                              <span className="text-xs text-green-700 font-medium truncate max-w-[100px]">{doc.name}</span>
                          </div>
                          <div className="flex border-l border-gray-200 pl-2 space-x-1">
                              <button onClick={() => onOpen(docKey)} className="p-1 text-teal-600 hover:bg-teal-50 rounded">
                                  <Eye className="w-4 h-4" />
                              </button>
                              <button onClick={() => onRemove(docKey)} className="p-1 text-red-500 hover:bg-red-50 rounded">
                                  <X className="w-4 h-4" />
                              </button>
                          </div>
                      </div>
                  )}
              </div>
          </div>
      </div>
    </div>
  );
};

const Forms = () => {
  const fullScreenPluginInstance = fullScreenPlugin();
const { EnterFullScreenButton } = fullScreenPluginInstance;

  const [new_class, set_new_class] = useState('');
  const [viewfile, setviewfile] = useState(null);
  const [errors, setErrors] = useState({});

  // State matching the Django Model Structure
  const [formData, setFormData] = useState({
    // Personal Details
    firstName: '',
    middleName: '',
    lastName: '',
    gender: 'M', // Default per choices
    dob: '',
    
    // Contact
    phone: '',
    email: '',
    
    // Present Address
    presentAddress: {
      line1: '',
      line2: '',
      city: '',
      state: '',
      pincode: '',
      country: 'India'
    },
    
    // Permanent Address
    sameAsPresent: false,
    permanentAddress: {
      line1: '',
      line2: '',
      city: '',
      state: '',
      pincode: '',
      country: ''
    },

    // Documents
    documents: {
      identityProof: { file: null, preview: null, name: '', docType: '' },
      dobProof: { file: null, preview: null, name: '', docType: '' },
      addressProof: { file: null, preview: null, name: '', docType: '' }
    }
  });

  // Handle Text Inputs
  const handleInputChange = (e, section = null) => {
    const { name, value } = e.target;
    if (section) {
      setFormData(prev => ({
        ...prev,
        [section]: { ...prev[section], [name]: value }
      }));
    } else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }
  };

  // Handle Document Type Selection
  const handleDocTypeChange = (docKey, value) => {
    setFormData(prev => ({
      ...prev,
      documents: {
        ...prev.documents,
        [docKey]: { ...prev.documents[docKey], docType: value }
      }
    }));
  };

  // Handle Checkbox for Permanent Address
  const handleCheckboxChange = () => {
    setFormData(prev => {
      const newSameAsPresent = !prev.sameAsPresent;
      return {
        ...prev,
        sameAsPresent: newSameAsPresent,
        permanentAddress: newSameAsPresent ? { ...prev.presentAddress } : prev.permanentAddress
      };
    });
  };

  // Sync permanent address if checkbox is checked
  useEffect(() => {
    if (formData.sameAsPresent) {
      setFormData(prev => ({
        ...prev,
        permanentAddress: { ...prev.presentAddress }
      }));
    }
  }, [formData.presentAddress]);

  // Handle File Upload
  const handleFileUpload = (docKey, event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Basic Validation
    if (file.size > 2 * 1024 * 1024) {
      alert("File size must be less than 2MB");
      return;
    }

    const preview = URL.createObjectURL(file);
    
    setFormData(prev => ({
      ...prev,
      documents: {
        ...prev.documents,
        [docKey]: { ...prev.documents[docKey], file, preview, name: file.name }
      }
    }));
  };

  const handleOpenFile = (docKey) => {
    const doc = formData.documents[docKey];
    if (doc && doc.file) {
      set_new_class("full-form");
      setviewfile(doc);
    }
  };

  const removeFile = (docKey) => {
    setFormData(prev => ({
      ...prev,
      documents: {
        ...prev.documents,
        [docKey]: { ...prev.documents[docKey], file: null, preview: null, name: '' }
      }
    }));
    if (viewfile?.file === formData.documents[docKey].file) {
      setviewfile(null);
      set_new_class('');
    }
  };

  return (
    <div className={`transition-all duration-300 ${new_class}`}>
      
      {/* LEFT SIDE: FORM */}
      <div className="min-h-screen bg-gray-50 py-8 px-4 reg w-full">
        <div className="max-w-5xl mx-auto bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-200">
          
          {/* Header */}
          <div className="bg-gradient-to-r from-teal-700 to-cyan-700 px-8 py-6 text-white">
            <h1 className="text-2xl font-bold">Passport Record Form</h1>
            <p className="text-teal-100 text-sm mt-1">Fill in the details exactly as per your documents</p>
          </div>

          <div className="p-8 space-y-8">
            
            {/* 1. PERSONAL DETAILS */}
            <section>
              <h2 className="text-xl font-semibold text-gray-800 mb-4 border-b pb-2">Personal Details</h2>
              <div className="grid md:grid-cols-3 gap-4 mb-4">
                <InputField label="First Name" name="firstName" value={formData.firstName} onChange={handleInputChange} required />
                <InputField label="Middle Name" name="middleName" value={formData.middleName} onChange={handleInputChange} />
                <InputField label="Last Name" name="lastName" value={formData.lastName} onChange={handleInputChange} required />
              </div>
              
              <div className="grid md:grid-cols-3 gap-4">
                <div className="flex flex-col">
                  <label className="text-sm font-medium text-gray-700 mb-1">Gender *</label>
                  <select 
                    name="gender" 
                    value={formData.gender} 
                    onChange={handleInputChange}
                    className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 outline-none"
                  >
                    <option value="M">Male</option>
                    <option value="F">Female</option>
                    <option value="O">Other</option>
                  </select>
                </div>

                <div className="flex flex-col">
                   <div className="flex justify-between items-center mb-1">
                      <label className="text-sm font-medium text-gray-700">Date of Birth *</label>
                   </div>
                   <input
                    type="date"
                    name="dob"
                    value={formData.dob}
                    onChange={handleInputChange}
                    className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 outline-none w-full"
                  />
                </div>

                <InputField label="Phone" name="phone" value={formData.phone} onChange={handleInputChange} required />
              </div>
              
              <div className="mt-4 md:w-1/3">
                 <InputField label="Email" name="email" value={formData.email} onChange={handleInputChange} type="email" required />
              </div>

              {/* IDENTITY PROOF SELECTOR */}
              <div className="mt-6">
                <DocumentSelector 
                    docKey="identityProof" 
                    doc={formData.documents.identityProof}
                    label="Identity Proof" 
                    options={DOC_OPTIONS.identity} 
                    required 
                    onTypeChange={handleDocTypeChange}
                    onUpload={handleFileUpload}
                    onOpen={handleOpenFile}
                    onRemove={removeFile}
                />
              </div>

              {/* DOB PROOF SELECTOR */}
              <div className="mt-2">
                 <DocumentSelector 
                    docKey="dobProof" 
                    doc={formData.documents.dobProof}
                    label="Date of Birth Proof" 
                    options={DOC_OPTIONS.dob} 
                    required 
                    onTypeChange={handleDocTypeChange}
                    onUpload={handleFileUpload}
                    onOpen={handleOpenFile}
                    onRemove={removeFile}
                 />
              </div>
            </section>

            {/* 2. PRESENT ADDRESS */}
            <section>
              <div className="flex justify-between items-center mb-4 border-b pb-2">
                <h2 className="text-xl font-semibold text-gray-800">Present Address</h2>
              </div>
              
              <div className="grid gap-4">
                <InputField label="Line 1" name="line1" value={formData.presentAddress.line1} onChange={(e) => handleInputChange(e, 'presentAddress')} required />
                <InputField label="Line 2" name="line2" value={formData.presentAddress.line2} onChange={(e) => handleInputChange(e, 'presentAddress')} />
                
                <div className="grid md:grid-cols-2 gap-4">
                   <InputField label="City" name="city" value={formData.presentAddress.city} onChange={(e) => handleInputChange(e, 'presentAddress')} required />
                   <InputField label="State" name="state" value={formData.presentAddress.state} onChange={(e) => handleInputChange(e, 'presentAddress')} required />
                </div>
                
                <div className="grid md:grid-cols-2 gap-4">
                   <InputField label="Pincode" name="pincode" value={formData.presentAddress.pincode} onChange={(e) => handleInputChange(e, 'presentAddress')} required />
                   <InputField label="Country" name="country" value={formData.presentAddress.country} onChange={(e) => handleInputChange(e, 'presentAddress')} required />
                </div>

                {/* ADDRESS PROOF SELECTOR */}
                <div className="mt-2">
                    <DocumentSelector 
                        docKey="addressProof" 
                        doc={formData.documents.addressProof}
                        label="Address Proof" 
                        options={DOC_OPTIONS.address} 
                        required 
                        onTypeChange={handleDocTypeChange}
                        onUpload={handleFileUpload}
                        onOpen={handleOpenFile}
                        onRemove={removeFile}
                    />
                </div>
              </div>
            </section>

            {/* 3. PERMANENT ADDRESS */}
            <section>
              <div className="flex items-center mb-4 border-b pb-2">
                <h2 className="text-xl font-semibold text-gray-800 mr-4">Permanent Address</h2>
                <button 
                  onClick={handleCheckboxChange} 
                  className="flex items-center text-sm text-teal-700 hover:text-teal-900 focus:outline-none"
                >
                  {formData.sameAsPresent ? <CheckSquare className="w-5 h-5 mr-1" /> : <Square className="w-5 h-5 mr-1" />}
                  Same as Present
                </button>
              </div>

              {!formData.sameAsPresent && (
                <div className="grid gap-4 animate-fadeIn">
                  <InputField label="Line 1" name="line1" value={formData.permanentAddress.line1} onChange={(e) => handleInputChange(e, 'permanentAddress')} required />
                  <InputField label="Line 2" name="line2" value={formData.permanentAddress.line2} onChange={(e) => handleInputChange(e, 'permanentAddress')} />
                  
                  <div className="grid md:grid-cols-2 gap-4">
                     <InputField label="City" name="city" value={formData.permanentAddress.city} onChange={(e) => handleInputChange(e, 'permanentAddress')} required />
                     <InputField label="State" name="state" value={formData.permanentAddress.state} onChange={(e) => handleInputChange(e, 'permanentAddress')} required />
                  </div>
                  
                  <div className="grid md:grid-cols-2 gap-4">
                     <InputField label="Pincode" name="pincode" value={formData.permanentAddress.pincode} onChange={(e) => handleInputChange(e, 'permanentAddress')} required />
                     <InputField label="Country" name="country" value={formData.permanentAddress.country} onChange={(e) => handleInputChange(e, 'permanentAddress')} required />
                  </div>
                </div>
              )}
            </section>

            {/* Submit Button */}
            <div className="flex justify-end pt-4">
               <button className="px-8 py-3 bg-gradient-to-r from-teal-600 to-teal-700 text-white font-bold rounded-lg shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all">
                 Save Passport Record
               </button>
            </div>

          </div>
        </div>
      </div>

      {/* RIGHT SIDE: PDF PREVIEW */}
      {viewfile && (


        <div className='reg2 h-screen sticky top-0 border-l-4 border-teal-600 shadow-2xl bg-gray-900'>

            <div className="bg-gray-800 text-white p-3 flex justify-between items-center shadow-md">
                <span className="font-medium flex items-center">
                   <FileText className="w-4 h-4 mr-2 text-teal-400" />
                   {viewfile.name}
                </span>
                <button 
                   onClick={() => {setviewfile(null); set_new_class('')}} 
                   className="text-gray-400 hover:text-white transition-colors p-1 rounded-md hover:bg-gray-700"
                >
                    <X size={20} />
                </button>
            </div>

            <div className="h-screen w-full bg-gray-500 overflow-hidden">

                <Viewer 
    fileUrl={viewfile.preview}
    defaultScale={SpecialZoomLevel.PageWidth} // Fits the whole page inside the container
    initialRotation={0}
/>

            </div>

        </div>
      )}
      
    </div>
  );
};

export default Forms;