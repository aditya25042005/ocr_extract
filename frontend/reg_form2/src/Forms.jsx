import React, { useState, useEffect } from 'react';
import { Upload, X, Eye, FileText, AlertCircle, Paperclip, CheckSquare, Square, ChevronDown } from 'lucide-react';
import { PDFDocument, rgb } from 'pdf-lib';
import './forms.css';
import { Viewer, SpecialZoomLevel } from '@react-pdf-viewer/core';
import { fullScreenPlugin } from '@react-pdf-viewer/full-screen';
import '@react-pdf-viewer/full-screen/lib/styles/index.css';
import '@react-pdf-viewer/core/lib/styles/index.css';
import api from './api';
const DOC_OPTIONS = {
  identity: ['Aadhaar Card', 'Driving License', 'Passport', 'Voter ID', 'PAN Card'],
  dob: ['Birth Certificate', 'SSLC Marks Card', 'Passport', 'Aadhaar Card'],
  address: ['Aadhaar Card', 'Driving License', 'Passport', 'Utility Bill', 'Rent Agreement'],
  autofill:['handwritten','printed']
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
const generateHighlightedFile = async (originalFile, coordsList) => {
  if (!coordsList || coordsList.length === 0) return URL.createObjectURL(originalFile);

  const fileType = originalFile.type;

  // --- PDF HANDLING ---
  if (fileType === 'application/pdf') {
    const arrayBuffer = await originalFile.arrayBuffer();
    const pdfDoc = await PDFDocument.load(arrayBuffer);
    const firstPage = pdfDoc.getPages()[0]; 
    const { height: pageHeight } = firstPage.getSize();

    coordsList.forEach((coords) => {
      // Data is [x1, y1, x2, y2]
      const [x1, x2, y1, y2] = coords;

      const width = Math.abs(x2 - x1);
      const height = Math.abs(y2 - y1);
      
      // Calculate Y for PDF (Flip axis: PageHeight - TopY)
      // Top visual Y is the smaller number in PDF coordinates usually, but we flip.
      // Standard Formula: PageHeight - (y_bottom_left + height)
      // Since inputs are likely Top-Left based images coords:
      // We convert Image Top-Left (y1) to PDF Bottom-Left.
      const pdfY = pageHeight - (y1 + height);

      firstPage.drawRectangle({
        x: x1,
        y: pdfY,
        width: width,
        height: height,
        borderColor: rgb(0, 0.8, 0.8), 
        borderWidth: 2,
      });
    });

    const pdfBytes = await pdfDoc.save();
    return URL.createObjectURL(new Blob([pdfBytes], { type: 'application/pdf' }));
  }

  // --- IMAGE HANDLING ---
  else if (fileType.startsWith('image/')) {
    return new Promise((resolve) => {
      const img = new Image();
      img.src = URL.createObjectURL(originalFile);
      img.onload = () => {
        const canvas = document.createElement('canvas');
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext('2d');
        
        ctx.drawImage(img, 0, 0);
        ctx.strokeStyle = '#0d9488'; 
        ctx.lineWidth = 4;

        coordsList.forEach((coords) => {
          const [x1, x2, y1, y2] = coords.coordinates;
          const width = x2 - x1;
          const height = y2 - y1;
          if(coords.score>0.8){
            ctx.strokeStyle = 'green';
                ctx.fillStyle = "green";

          }
          else if(coords.score>0.5){
            ctx.strokeStyle = 'pink';
            ctx.fillStyle = "pink";
          }
          else{
            ctx.strokeStyle = 'red';
            ctx.fillStyle = "red";
          }
          ctx.strokeRect(x1, y1, width, height);
          ctx.lineWidth = 4; // Changed from 2 to 4
          // 2. Increase Text Size
          ctx.font = "bold 32px calibri"; // Changed from 14px to 24px (and added 'bold')
          ctx.fillText(`${coords.score*100}%` ,(x2+10) , (y1+y2)/2);
          ctx.fillText(coords.label ,x2+10 ,(y1+y2)/2+30);


          
          
        });

        canvas.toBlob((blob) => {
          resolve(URL.createObjectURL(blob));
        }, fileType);
      };
    });
  }
  return URL.createObjectURL(originalFile);
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
      present_address_line: '',
      present_city: '',
      present_state: '',
      present_pincode: '',
      present_country: 'India'
    },
    
    // Permanent Address
    permanent_address_same_as_present: false,
    permanentAddress: {
      permanent_address_line: '',
      permanent_city: '',
      permanent_state: '',
       permanent_pincode: '',
       permanent_country: ''
    },

    // Documents
    documents: {
      name_gender_proof: { file: null, preview: null, name: '', docType: '' },
      dob_proof: { file: null, preview: null, name: '', docType: '' },
      address_proof: { file: null, preview: null, name: '', docType: '' },
      auto_fill: { file: null, preview: null, name: '', docType: '' }
    }
  });
  //auto fill submit
  const submit_auto_fill = async() => {
console.log("auto fill");
    /////

   if(!formData.documents.auto_fill.file){
      alert("Please upload Auto Fill document");
      return;
    }
    else{
      console.log(formData.documents.auto_fill.name);
      const data = new FormData();
      data.append('file', formData.documents.auto_fill.file);
       api.post('/api/handwritten/ocr/',data,{headers: {
          'Content-Type': 'multipart/form-data',
        }},)
      .then( async function (response) {
        console.log(response.data);
        // Update formData with received data
        const receivedData = response.data;
       let rawDob = receivedData?.['fields']?.['DOB']?.["value"];
         console.log(rawDob,"u");

let formattedDob = "";

// 2. Check if rawDob exists and is a string before splitting
if (rawDob && typeof rawDob === 'string') {
  const parts = rawDob.split('-'); // Splitting "05-04-2005"
  
  // 3. Reorder to YYYY-MM-DD for the input
  if (parts.length === 3) {
    const [day, month, year] = parts;
    formattedDob = `${year}-${month}-${day}`; // Becomes "2005-04-05"
  } else {
    formattedDob = rawDob; // Fallback if format is weird
  }
  console.log(formattedDob,"u");
}
//////// data with coordinates


 const fields = receivedData?.['fields'] || {};
 const coordinateList = Object.entries(fields) // Use entries to get the Key (e.g., "State")
  .map(([key, field]) => ({
      label: key,                     // "State", "Country", etc.
      value: field.value || field.raw_line, // "Kerala", "India" (fallback to raw_line if value is missing)
      coordinates: field.coordinates, // [127, 983, 793, 936]
      score: field.confidence_score   // 0.98
  }))
  .filter(item => item.coordinates && Array.isArray(item.coordinates) && item.coordinates.length === 4);
const highlightedPreviewUrl = await generateHighlightedFile(
        formData.documents.auto_fill.file, 
        coordinateList 
      );
const updatedAutoFillDoc = {
          ...formData.documents.auto_fill,
          preview: highlightedPreviewUrl, 
      };

        setFormData(prev => ({
          ...prev,
          firstName: receivedData?.['fields']?.['Name Raw']?.['first_name'] || prev.firstName,
  middleName: receivedData?.['fields']?.['Name Raw']?.['middle_name'] || prev.middleName,
  lastName: receivedData?.['fields']?.['Name Raw']?.['last_name'] || prev.lastName,
  gender: receivedData?.['fields']?.['Gender'] || prev.gender,
  dob: formattedDob || prev.dob,
  phone: receivedData?.['fields']?.['Phone']?.['value'] || prev.phone,
  email: receivedData?.['fields']?.['Email']?.['value'] || prev.email,
  permanentAddress: {
    permanent_address_line: receivedData?.['fields']?.['Address'] || prev.permanentAddress?.permanent_address_line,
    permanent_city: receivedData?.['fields']?.['City']?.['value'] || prev.permanentAddress?.permanent_city,
    permanent_state: receivedData?.['fields']?.['State']?. ['value']|| prev.permanentAddress?.permanent_state,
    permanent_pincode: receivedData?.['fields']?.['Pincode']?.['value'] || prev.permanentAddress?.permanent_pincode,
    permanent_country: receivedData?.['fields']?.['Country']?.['value'] || prev.permanentAddress?.permanent_country,
  },
    documents: {
        ...prev.documents,
        auto_fill:  updatedAutoFillDoc 
      }
           
 

        }));
        setviewfile(updatedAutoFillDoc);
        set_new_class("full-form");
     
  }).catch(function (error) {

  })
}

  }
  //verify passport data
  const verfiy_passport = () => {
const data = new FormData();

  // --- A. Append Simple Fields ---
  data.append('first_name', formData.firstName);
  data.append('middle_name', formData.middleName);
  data.append('last_name', formData.lastName);
  data.append('gender', formData.gender);
  data.append('dob', formData.dob);
  data.append('phone', formData.phone);
  data.append('email', formData.email);
  data.append('permanent_address_same_as_present', formData.permanent_address_same_as_present);

// Address Loop
  Object.keys(formData.presentAddress).forEach(key => {
    // Reading from State (formData)
    // Writing to Payload (payload)
    data.append(`${key}`, formData.presentAddress[key]);
  });
   Object.keys(formData.permanentAddress).forEach(key => {
    // Reading from State (formData)
    // Writing to Payload (payload)
    data.append(`${key}`, formData.permanentAddress[key]);
  });
Object.keys(formData.documents).forEach((docKey) => {
    
    // Get the specific document object (e.g., { file: ..., preview: ... })
    const docItem = formData.documents[docKey];

    // Check if the user actually selected a file for this document
    if (docItem.file) {
      // Append it to the payload
      // key: "identityProof", value: File Object
      data.append(docKey, docItem.file);
    }

  });
console.log(data);
api.post('/api/verify-documents/',
   data
  ,{headers: {
      // 1. We overwrite the global 'application/json' setting.
      // 2. Setting it to 'multipart/form-data' tells Axios/Django this contains files.
      // Note: Axios will automatically add the "boundary" string needed for files.
      'Content-Type': 'multipart/form-data',
    }},)
  .then(function (response) {
    console.log(response);

    data=response.data['verification_results'];


  })
  .catch(function (error) {
    console.log(error);
  });



  }
  // Submit Passport Data
  const submit_passport = () => {
const data = new FormData();

  // --- A. Append Simple Fields ---
  data.append('first_name', formData.firstName);
  data.append('middle_name', formData.middleName);
  data.append('last_name', formData.lastName);
  data.append('gender', formData.gender);
  data.append('dob', formData.dob);
  data.append('phone', formData.phone);
  data.append('email', formData.email);
  data.append('permanent_address_same_as_present', formData.permanent_address_same_as_present);

// Address Loop
  Object.keys(formData.presentAddress).forEach(key => {
    // Reading from State (formData)
    // Writing to Payload (payload)
    data.append(`${key}`, formData.presentAddress[key]);
  });
   Object.keys(formData.permanentAddress).forEach(key => {
    // Reading from State (formData)
    // Writing to Payload (payload)
    data.append(`${key}`, formData.permanentAddress[key]);
  });
Object.keys(formData.documents).forEach((docKey) => {
    
    // Get the specific document object (e.g., { file: ..., preview: ... })
    const docItem = formData.documents[docKey];

    // Check if the user actually selected a file for this document
    if (docItem.file) {
      // Append it to the payload
      // key: "identityProof", value: File Object
      data.append(docKey, docItem.file);
    }

  });
console.log(data);
api.post('/api/passport/create/',
   data
  ,{headers: {
      // 1. We overwrite the global 'application/json' setting.
      // 2. Setting it to 'multipart/form-data' tells Axios/Django this contains files.
      // Note: Axios will automatically add the "boundary" string needed for files.
      'Content-Type': 'multipart/form-data',
    }},)
  .then(function (response) {
    console.log(response);
    
  })
  .catch(function (error) {
    console.log(error);
  });

  }

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
      const newSameAsPresent = !prev.permanent_address_same_as_present;
      return {
        ...prev,
        permanent_address_same_as_present: newSameAsPresent,
        permanentAddress: newSameAsPresent ? { 
           
        permanent_address_line: prev.presentAddress.present_address_line,
        permanent_city: prev.presentAddress.present_city,
        permanent_state: prev.presentAddress.present_state,
        permanent_pincode: prev.presentAddress.present_pincode,
        permanent_country: prev.presentAddress.present_country,
      
         } : prev.permanentAddress
      };
    });
  };

  // Sync permanent address if checkbox is checked
  useEffect(() => {
    if (formData.permanent_address_same_as_present) {
      setFormData(prev => ({
        ...prev,
        permanentAddress: { ...prev.presentAddress }
      }));
    }
  }, [formData.presentAddress]);

  // Handle File Upload
  const handleFileUpload = (docKey, event) => {
    //imp 

        console.log("hi");
    //t check whether it is aadhar or not
    const file = event.target.files?.[0];
const formData = new FormData();
formData.append('file', file); // 'file' is the key name expected by your backend
     api.post('/api/aadhaar-detect/',formData,{headers: {

          'Content-Type': 'multipart/form-data',

        }},)

      .then(  function (response) {
       if(!response.data['is_aadhar']){
          alert("Please upload valid Aadhar Card");

       }

      }).catch(function (error) {




     })
     
    console.log(file,"hi");
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

    /// checking score '
      
    
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
                    docKey="name_gender_proof" 
                    doc={formData.documents.name_gender_proof}
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
                 
                    docKey="dob_proof" 
                    doc={formData.documents.dob_proof}
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
                <InputField label="Line" name="present_address_line" value={formData.presentAddress.present_address_line} onChange={(e) => handleInputChange(e, 'presentAddress')} required />
                
                <div className="grid md:grid-cols-2 gap-4">
                   <InputField label="City" name="present_city" value={formData.presentAddress.present_city} onChange={(e) => handleInputChange(e, 'presentAddress')} required />
                   <InputField label="State" name="present_state" value={formData.presentAddress.present_state} onChange={(e) => handleInputChange(e, 'presentAddress')} required />
                </div>
                
                <div className="grid md:grid-cols-2 gap-4">
                   <InputField label="Pincode" name="present_pincode" value={formData.presentAddress.present_pincode} onChange={(e) => handleInputChange(e, 'presentAddress')} required />
                   <InputField label="Country" name="present_country" value={formData.presentAddress.present_country} onChange={(e) => handleInputChange(e, 'presentAddress')} required />
                </div>

                {/* ADDRESS PROOF SELECTOR */}
                <div className="mt-2">
                    <DocumentSelector 
                        docKey="address_proof" 
                        doc={formData.documents.address_proof}
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
                  {formData.permanent_address_same_as_present ? <CheckSquare className="w-5 h-5 mr-1" /> : <Square className="w-5 h-5 mr-1" />}
                  Same as Present
                </button>
              </div>

              {!formData.permanent_address_same_as_present && (
                <div className="grid gap-4 animate-fadeIn">
                  <InputField label="Line" name="permanent_address_line" value={formData.permanentAddress.permanent_address_line} onChange={(e) => handleInputChange(e, 'permanentAddress')} required />
                  
                  <div className="grid md:grid-cols-2 gap-4">
                     <InputField label="City" name="permanent_city" value={formData.permanentAddress.permanent_city} onChange={(e) => handleInputChange(e, 'permanentAddress')} required />
                     <InputField label="State" name="permanent_state" value={formData.permanentAddress.permanent_state} onChange={(e) => handleInputChange(e, 'permanentAddress')} required />
                  </div>
                  
                  <div className="grid md:grid-cols-2 gap-4">
                     <InputField label="Pincode" name="permanent_pincode" value={formData.permanentAddress.permanent_pincode} onChange={(e) => handleInputChange(e, 'permanentAddress')} required />
                     <InputField label="Country" name="permanent_country" value={formData.permanentAddress.permanent_country} onChange={(e) => handleInputChange(e, 'permanentAddress')} required />
                  </div>
                </div>
              )}
               <div className="auto fill">
                 <DocumentSelector 
                        docKey="auto_fill"
                        doc={formData.documents.auto_fill}
                        label="Auto Fill"
                        options={DOC_OPTIONS.autofill}
                        required 
                        onTypeChange={handleDocTypeChange}
                        onUpload={handleFileUpload}
                        onOpen={handleOpenFile}
                        onRemove={removeFile}
                    />
               <button className="px-8 py-3 bg-gradient-to-r from-teal-600 to-teal-700 text-white font-bold rounded-lg shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all"
               onClick={verfiy_passport}>
                 verify Passport Record
               </button>
            </div>
            <button className="px-8 py-3 bg-gradient-to-r from-teal-600 to-teal-700 text-white font-bold rounded-lg shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all"
               onClick={submit_passport}>
                 Save Passport Record
               </button>
            
            </section>
             

            {/* Submit Button */}
            <div className="flex justify-end pt-4">
               <button className="px-8 py-3 bg-gradient-to-r from-teal-600 to-teal-700 text-white font-bold rounded-lg shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all"
               onClick={submit_auto_fill}>
                 Auto Fill Form
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
{viewfile.file.type==="application/pdf" ?
                <Viewer 
    fileUrl={viewfile.preview}
    defaultScale={SpecialZoomLevel.PageWidth} // Fits the whole page inside the container
    initialRotation={0}
/>:
                <img src={viewfile.preview} alt="Document Preview" className="object-contain w-full h-full bg-gray-900" />}

            </div>

        </div>
      )}
      
    </div>
  );
};

export default Forms;