import React, { useState } from 'react';
// Assuming you put the CSS in a file named status.css
import './status.css'; 
import Box from '@mui/material/Box';
import { Landmark } from 'lucide-react';
import { SparklesCore } from "./components/ui/sparkles";
import './Home.css';
import { BackgroundGradient } from "./components/ui/background-gradient";
import { Button } from "./components/ui/moving-border";
import { Zap, ShieldCheck, Camera } from 'lucide-react';
import { CardContainer, CardBody, CardItem } from "./components/ui/3d-card.jsx";
import { useNavigate } from 'react-router-dom';
import api from './api';
const StatusCheck = () => {
  const navigate = useNavigate();
  const [applicationId, setApplicationId] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [statusData, setStatusData] = useState(undefined); // To hold all fetched data
    const [applicationStatus, setApplicationStatus] = useState(null); // To hold just the status string

    // --- API Fetch Function ---
    const fetchApplicationStatus = async (id) => {
        try {
            const response = await api.get(`/api/passport/${id}`);
            const apiData = response.data;

            if (apiData && apiData.id) {
                // Return the status string (e.g., 'VERIFIED')
                return { 
                    data: apiData, 
                    status: apiData.status 
                };
            }
            return null; // ID not found

        } catch (error) {
            console.error('Error fetching application status:', error);
            return null; // Handle API errors
        }
    };
  
const handleSubmit = async (e) => {
    e.preventDefault();
    const id = applicationId.trim();

    if (!id) {
        alert("Please enter a valid Application ID.");
        return;
    }

    setIsLoading(true);
    setStatusData(undefined);
    setApplicationStatus(null); 

    const result = await fetchApplicationStatus(id);

    setIsLoading(false);

    if (result && result.data) {
        setStatusData(result.data);
        setApplicationStatus(result.status); 
        // Optional: alert(`Status: ${result.status}`); 
    } else {
        alert(`Application ID ${id} not found or a server error occurred.`);
        setStatusData(null); 
    }
};

  return (
    <>
     <div className="ui">
         
            {/* Core component */}
            <SparklesCore
              background="transparent"
              minSize={0.4}
              maxSize={2}
              particleDensity={700}
              className="w-full h-full"
              particleColor="#327182ff"
            />
     
            {/* Radial Gradient to prevent sharp edges */}
          {  <div className="absolute inset-0 w-full h-full bg-white [mask-image:radial-gradient(100vw_120vh_at_top,transparent_20%,white)]"></div>}
        </div>
     
      
      {/* Navigation Header - Sits on top of the 'ui' background */}
      <div className='nav-header'>
        <div className='nav-title1 t1'>
          <Landmark />
          Passport Verification Portal
        </div>
        <a href="/STATUS" className="nav-title2 t1 check-status-link">
          CHECK STATUS
        </a>
      </div>

     <div className="status_main">
      <div className="status-content-card">
        <h2 className="status-title">Check Application Status</h2>
        <p className="status-subtitle">
          Please enter your Application ID to view the current status of your passport verification.
        </p>

        <form onSubmit={handleSubmit} className="status-form">
          <div className="input-group">
            <label htmlFor="applicationId" className="input-label">Application ID</label>
            <input
              type="text"
              id="applicationId"
              className="status-input"
              value={applicationId}
              onChange={(e) => setApplicationId(e.target.value)}
              placeholder="e.g. 123"
              required
            />
          </div>
          
          <button type="submit" className="check-status-button">
            CHECK STATUS
          </button>
          <div className="status-result">
            {isLoading && <p>Loading status...</p>}

            {!isLoading && applicationStatus && (
              <p>{statusData.first_name}'s application status is: <strong>{applicationStatus}</strong></p>
            )}
            </div>
        </form>
        </div>
        </div>
        
    <div className='footer'>
    
        © 2024 Government of India. All rights reserved.
         </div>
     
        



      
      </>
    
       
  );
};

export default StatusCheck;
