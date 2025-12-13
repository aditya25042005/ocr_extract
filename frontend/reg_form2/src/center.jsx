import React, { useState, useEffect } from 'react';
// Use the same CSS file for shared styling
import './center.css'; 
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
// --- Mock API Fetch (Replace with your actual API call) ---

const FetchDropdownOptions = async () => {
    try {
        // 1. Fetch data from the actual API endpoint
        const response = await api.get('/api/passport/ids');
        
        // The API response data structure, based on your image, is { count: N, ids: [1, 2, ...] }
        const rawIds = response.data.ids;
        
        console.log('Successfully fetched Passport IDs:', rawIds);

        // 2. Process the raw IDs into the required options format
        const options = rawIds.map(id => ({
            // Ensure IDs are treated as strings if necessary, though they look like numbers in the image
            value: String(id), 
            label: `ID: ${id}`, // Adding 'ID: ' for better display context
        }));

        // 3. Simulate a short delay (optional, but good for testing UI loading states)
        await new Promise(resolve => setTimeout(resolve, 500)); 

        // 4. Return the options array, fulfilling the outer Promise
        return options;

    } catch (error) {
        // Handle network errors, 4xx/5xx responses from the API
        console.error('Error fetching Passport IDs for dropdown:', error);
        
        // Return an empty array or throw an error based on desired behavior
        // Returning an empty array allows the component to load without options.
        return []; 
    }
};


const SelectionPage = () => {
    const navigate = useNavigate();
  const [options, setOptions] = useState([]);
  const [selectedValue, setSelectedValue] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  // 1. Fetch data on component mount
  useEffect(() => {
    const fetchData = async () => {
      const data = await FetchDropdownOptions();
      setOptions(data);
      setIsLoading(false);
      // Set a default value if options exist
      if (data.length > 0) {
        setSelectedValue(data[0].value);
      }
    };
    fetchData();
  }, []);

  const handleSelectionChange = (event) => {
    setSelectedValue(event.target.value);
  };
  
  const handleSubmit = (e) => {
    e.preventDefault();
    alert(`Selected value: ${selectedValue}`);
    if (selectedValue) {
        // Navigate to the next route, appending the selected value (ID)
        // Example: If selectedValue is '3', it navigates to /detail/3
        navigate(`/detail/${selectedValue}`);
    } else {
        alert("Please select an option before proceeding.");
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
    <div className="status-page-container selection-page-bg"> 
      
      {/* Header and UI Background here (omitted for brevity, assume they are present) */}
      
      <div className="selection-card">
        <h2 className="selection-title">Select Verification Center</h2>
        <p className="selection-subtitle">
          Please choose the appropriate department or location from the list below.
        </p>

        <form onSubmit={handleSubmit} className="selection-form">
          <div className="input-group">
            <label htmlFor="selection" className="input-label">Available Options</label>
            
            {isLoading ? (
                <div className="dropdown-loading">Loading options...</div>
            ) : (
                <div className="custom-select-wrapper">
                    <select
                        id="selection"
                        className="themed-dropdown"
                        value={selectedValue}
                        onChange={handleSelectionChange}
                        required
                    >
                        {options.map(option => (
                            <option key={option.value} value={option.value}>
                                {option.label}
                            </option>
                        ))}
                    </select>
                </div>
            )}
          </div>
          
          <button type="submit" className="check-status-button selection-submit-btn">
            PROCEED
          </button>
        </form>
      </div>
    </div>
    </>
  );
};

export default SelectionPage;