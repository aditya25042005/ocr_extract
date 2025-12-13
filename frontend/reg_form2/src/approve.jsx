import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom'; // <--- REQUIRED IMPORT
import { Check, X, FileText, Landmark } from 'lucide-react';
// Assuming the provided CSS is in a file like 'approve.css'
import './approve.css'; 
import api from './api';
// NOTE: Ensure 'api' (e.g., an Axios instance) is imported here!
// import api from './path-to-your-api-instance'; 


// --- API Fetch Function ---
// Fetches the application data based on the ID from the URL.
const fetchApplicationData = async (id) => {
    // Replace this logic with your actual API call and mapping
    try {
        // API URL from your image: http://127.0.0.1:8000/api/passport/1
        const response = await api.get(`/api/passport/${id}`);
        const apiData = response.data;
        // Map the raw API response (apiData) to the component's internal structure
        // This is a necessary step to ensure the component fields (e.g., data.firstName) are populated correctly
        const processedData = {
            id: String(apiData.id),
            firstName: apiData.first_name,
            middleName: apiData.middle_name,
            lastName: apiData.last_name,
            gender: apiData.gender,
            dob: apiData.dob,
            phone: apiData.phone,
            email: apiData.email,
            presentAddress: {
                line: apiData.present_address,
                city: apiData.present_city,
                state: apiData.present_state,
                pincode: apiData.present_pincode,
                country: apiData.present_country,
            },
            permanentAddress: {
                line: apiData.permanent_address || 'Same as Present',
                city: apiData.permanent_city || '',
                state: apiData.permanent_state || '',
                pincode: apiData.permanent_pincode || '',
                country: apiData.permanent_country || '',
            },
            documents: {
                identity_proof: { type: 'Name/Gender Proof', url: apiData.name_gender_proof, fileName: 'uploaded' }, // Placeholder fileName
                dob_proof: { type: 'DOB Proof', url: apiData.dob_proof, fileName: 'uploaded' },
                address_proof: { type: 'Address Proof', url: apiData.address_proof, fileName: 'uploaded' },
            },
            status: apiData.status,
            verification_score: 'N/A', 
        };
        return processedData;

    } catch (error) {
        console.error(`Failed to fetch application data for ID ${id}:`, error);
        return null;
    }
};


// --- Read-Only Display Field Component (Kept the same) ---
const DisplayField = ({ label, value, className = "" }) => (
  <div className={`flex flex-col ${className}`}>
    <label className="text-sm font-medium text-gray-500 mb-1">{label}</label>
    <p className="px-4 py-2 border border-gray-200 rounded-lg bg-gray-50 text-gray-800 font-semibold">
      {value || 'N/A'}
    </p>
  </div>
);


// --- Main Verification Component ---
const VerificationReview = () => {
    // 1. Get ID from URL params instead of props
    const { centerId } = useParams(); 
    const applicationId = centerId; // Use a more descriptive name if needed

    const [data, setData] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [verificationStatus, setVerificationStatus] = useState(null); // 'VERIFIED' or 'Rejected'

    // 2. useEffect to call API when the component mounts or ID changes
    useEffect(() => {
        const loadData = async () => {
            if (!applicationId) {
                setIsLoading(false);
                setData(null);
                return;
            }
            setIsLoading(true);
            // Call the integrated API fetch function
            const applicationData = await fetchApplicationData(applicationId); 
 setVerificationStatus(applicationData?.status || null);
            setData(applicationData);
            setIsLoading(false);
        };
        loadData();
    }, [applicationId]); // Dependency on the ID from the URL

    const handleVerification =async (newStatus) => {


        // Ensure newStatus is uppercase (VERIFIED or REJECTED)
        const statusToSend = newStatus.toUpperCase();
        
        // 1. Optimistically update UI (optional, but good for UX)
        // setVerificationStatus(statusToSend); 
        
        try {
            console.log(`[API] Attempting to PATCH status for ID ${applicationId} to: ${statusToSend}`);
            
            const response = await api.patch(
                `/api/passport/${applicationId}/toggle-status/`,
                { status: statusToSend } // Sending the required JSON body
            );

            // 2. Confirm status update from API response (optional, but robust)
            if (response.data && response.data.status === statusToSend) {
                setVerificationStatus(statusToSend); // Final state update on success
                alert(`Application ${applicationId} successfully set to ${statusToSend}!`);
            } else {
                // If API returns an unexpected response
                alert(`Error: API response for ${statusToSend} was unexpected.`);
                // Revert status or show error message
            }

        } catch (error) {
            console.error(`Error patching application status for ID ${applicationId}:`, error);
            alert(`Failed to update status due to network or server error. Check console.`);
            // Revert state if necessary, setVerificationStatus(data.initialStatus);
        }
         };
    
    // --- Render Logic ---
    if (isLoading) {
        return <div className="p-8 text-center text-lg text-[#0D47A1]">Loading Application ID {applicationId}...</div>;
    }

    if (!data) {
        return <div className="p-8 text-center text-lg text-red-600">Application ID {applicationId} not found.</div>;
    }
    
    const requiresAction = () => {
        const status = verificationStatus?.toUpperCase();
        // Assume VERIFIED or REJECTED are final states where buttons are hidden
        return status !== 'VERIFIED' && status !== 'REJECTED';
    };
    // Determine the header style based on verification status
    const statusClass = verificationStatus === 'VERIFIED' ? 'bg-green-600' : 
                        verificationStatus === 'REJECTED' ? 'bg-red-600' : 
                        'bg-gradient-to-r from-[#0D47A1] to-[#1976D2]';


    return (
        <div className="min-h-screen py-8 px-4 bg-gray-50">
            <div className="max-w-6xl mx-auto bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-200">
                
                {/* Header (Thematic blue/white) */}
                <div className={`${statusClass} px-8 py-6 text-white flex justify-between items-center`}>
                    <div>
                        <h1 className="text-2xl font-bold">Verification Review - Application ID: {data.id}</h1>
                        <p className="text-sm mt-1">Review applicant data and attached documents for verification.</p>
                    </div>
                    {verificationStatus && (
                         <span className="text-lg font-extrabold p-2 rounded-full border-2 bg-white text-center"
                             style={{ color: verificationStatus === 'REJECTED' ? '#1a9a4b' : '#dc3545' }}>
                             {verificationStatus.toUpperCase()}
                         </span>
                    )}
                </div>

                <div className="p-8 space-y-10">
                    
                    {/* 1. PERSONAL DETAILS */}
                    <section>
                        <h2 className="text-xl font-semibold text-[#1a3b5d] mb-4 border-b-2 border-gray-200 pb-2">1. Personal Details</h2>
                        <div className="grid md:grid-cols-4 gap-4">
                            <DisplayField label="First Name" value={data.firstName} />
                            <DisplayField label="Middle Name" value={data.middleName} />
                            <DisplayField label="Last Name" value={data.lastName} />
                            <DisplayField label="Gender" value={data.gender === 'M' ? 'Male' : data.gender === 'F' ? 'Female' : 'Other'} />
                            <DisplayField label="Date of Birth" value={data.dob} />
                            <DisplayField label="Phone" value={data.phone} />
                            <DisplayField label="Email" value={data.email} className="md:col-span-2" />
                        </div>
                    </section>

                    {/* 2. ADDRESSES */}
                    <section>
                        <h2 className="text-xl font-semibold text-[#1a3b5d] mb-4 border-b-2 border-gray-200 pb-2">2. Address Details</h2>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            {/* Present Address */}
                            <div className="p-4 border border-blue-100 rounded-lg bg-blue-50">
                                <h3 className="font-bold text-[#0D47A1] mb-3">Present Address</h3>
                                <div className="space-y-3">
                                    <DisplayField label="Line" value={data.presentAddress.line} />
                                    <div className="grid grid-cols-2 gap-4">
                                        <DisplayField label="City" value={data.presentAddress.city} />
                                        <DisplayField label="State" value={data.presentAddress.state} />
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <DisplayField label="Pincode" value={data.presentAddress.pincode} />
                                        <DisplayField label="Country" value={data.presentAddress.country} />
                                    </div>
                                </div>
                            </div>

                            {/* Permanent Address */}
                            <div className="p-4 border border-blue-100 rounded-lg bg-blue-50">
                                <h3 className="font-bold text-[#0D47A1] mb-3">Permanent Address</h3>
                                <div className="space-y-3">
                                    <DisplayField label="Line" value={data.permanentAddress.line} />
                                    <div className="grid grid-cols-2 gap-4">
                                        <DisplayField label="City" value={data.permanentAddress.city} />
                                        <DisplayField label="State" value={data.permanentAddress.state} />
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <DisplayField label="Pincode" value={data.permanentAddress.pincode} />
                                        <DisplayField label="Country" value={data.permanentAddress.country} />
                                    </div>
                                </div>
                            </div>
                        </div>
                    </section>

                {/* 3. DOCUMENTS & SCORES */}
                    <section>
                        <h2 className="text-xl font-semibold text-[#1a3b5d] mb-4 border-b-2 border-gray-200 pb-2">3. Supporting Documents</h2>
                        <div className="grid md:grid-cols-3 gap-6">
                            {Object.entries(data.documents).map(([key, doc]) => (
                                <div key={key} className="border p-4 rounded-lg bg-white shadow-sm">
                                    <p className="font-semibold text-[#0D47A1] capitalize mb-1">{doc.type}</p>
                                    <p className="text-sm text-gray-600 flex items-center">
                                        <FileText className="w-4 h-4 mr-2 text-gray-500" />
                                        File: {doc.fileName}
                                    </p>
                                    {/* Score display (simulated) */}
                                    <p className="mt-2 text-sm font-bold text-green-600">
                                    </p>
                                    
                                    {/* --- DIRECT URL LINK IMPLEMENTED HERE --- */}
                                    <a 
                                        href={doc.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className={`mt-3 text-xs font-medium block ${doc.url ? 'text-teal-700 hover:text-teal-900' : 'text-gray-400 cursor-not-allowed'}`}
                                        // This disables the link if doc.url is falsy
                                        onClick={(e) => { if (!doc.url) e.preventDefault(); }} 
                                    >
                                        View Document (Link)
                                    </a>
                                    {/* -------------------------------------- */}
                                </div>
                            ))}
                        </div>
                    </section>
                    {/* VERIFICATION ACTION BUTTONS */}
                    {/* VERIFICATION ACTION BUTTONS - Conditional Rendering */}
                    {requiresAction() && (
                        <div className="pt-6 border-t border-gray-100 flex justify-end gap-4">
                            <button 
                                className="flex items-center px-6 py-2.5 bg-red-600 text-white font-bold rounded-lg shadow-md hover:bg-red-700 transition-all"
                                onClick={() => handleVerification('REJECTED')}
                            >
                                <X className="w-5 h-5 mr-2" /> Reject Application
                            </button>
                            <button 
                                className="flex items-center px-6 py-2.5 bg-green-600 text-white font-bold rounded-lg shadow-md hover:bg-green-700 transition-all"
                                onClick={() => handleVerification('VERIFIED')}
                            >
                                <Check className="w-5 h-5 mr-2" /> Approve Application
                            </button>
                        </div>
                    )}
                    
                    {!requiresAction() && verificationStatus && (
                        <div className="pt-6 border-t border-gray-100 flex justify-center p-4">
                             <p className="text-lg font-bold" style={{ color: verificationStatus?.toUpperCase() === 'VERIFIED' ? '#1a9a4b' : '#dc3545' }}>
                                This application has been {verificationStatus.toUpperCase()}. No further action required.
                            </p>
                        </div>
                    )}
                   

                </div>
            </div>
        </div>
    );
};

export default VerificationReview;