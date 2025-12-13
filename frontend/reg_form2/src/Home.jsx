import React, { useState } from 'react';
import Box from '@mui/material/Box';
import { Landmark } from 'lucide-react';
import { SparklesCore } from "./components/ui/sparkles";
import './Home.css';
import { BackgroundGradient } from "./components/ui/background-gradient";
import { Button } from "./components/ui/moving-border";
import { Zap, ShieldCheck, Camera } from 'lucide-react';
import { CardContainer, CardBody, CardItem } from "./components/ui/3d-card.jsx";
import  ashoka from './components/ui/img/fov.png';
import { useNavigate } from 'react-router-dom'; // 1. Import useNavigate
function  Home(){
  const navigate = useNavigate(); // 2. Initialize useNavigate
const handlePreRegisterClick = () => {

    navigate('/login'); // Navigate to the Login route
  };

  const handleCenterClick = () => {
    navigate('/center'); // Navigate to the Forms route
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
<div className=' nav-header'>

 <div className='nav-title1 t1'>
    <Landmark />
 Passport Verification Portal
 </div>

 <a href="/STATUS" class="nav-title2 t1 check-status-link">CHECK STATUS</a>
</div>
<div className="page-title">

<div className='page-title1 p1' >
<img 
        src={ashoka} 
        alt="Ashoka Chakra/National Emblem" 
       style={{ display: 'block', margin: '0 auto' }} 
    />
GOVERNMENT OF INDIA
</div>



<div className='page-title2 p1'>
Fast and Secure Passport Verification System

</div>
<div className='page-title3 p1'>
    Get your passport verified quickly and securely. 
    Join thousands of users who trust our 
    platform for seamless verification services.

    </div>
    <div className='page-title-button p1'>
            <div className='button-group1'>
                <Button className='button-main1'  borderRadius="30rem" onClick={handlePreRegisterClick}  >

                     Pre-register
                         </Button>
                         </div>
          <div className='button-group1'>

          <Button className='button-main1'  borderRadius="30rem" onClick={handleCenterClick}>
                     center
                         </Button>
                         </div>



          <div className='page-title-button2 p2'>
        

        </div>

       
    </div>
        </div>

 
  

    <CardContainer className="inter-var">
  <CardBody className="features">
    <CardItem
      className="feature_icon feature_prop"
    >
      {/* Icon: Zap (For Speed/Automation) - Styled directly for visual appeal */}
      <Zap size={40} strokeWidth={2.5} color="#007bff" />
    </CardItem>
    <CardItem
      as="div"
      className="feature_title feature_prop"
    >
      Instant Auto-Fill & Data Capture
    </CardItem>
    <CardItem
      as="p"
      className="feature_desc feature_prop"
    >
      Imagine: Throwing a messy, handwritten form at the system and watching it instantly fill out a digital application! 
    </CardItem>
  </CardBody>
</CardContainer>

<CardContainer className="inter-var">
  <CardBody className="features">
    <CardItem
      className="feature_icon feature_prop"
    >
      {/* Icon: ShieldCheck (For Verification/Trust) - Styled directly for visual appeal */}
      <ShieldCheck size={40} strokeWidth={2.5} color="#28a745" />
    </CardItem>
    <CardItem
      as="div"
      className="feature_title feature_prop"
    >
      Trust is Built-In: Verification & Scoring
    </CardItem>
    <CardItem
      as="p"
      className="feature_desc feature_prop"
    >
      The Feature: Our system acts as the Guardian of Integrity, cross-checking user form data against the document.
    </CardItem>
  </CardBody> 
</CardContainer>

<CardContainer className="inter-var">
  <CardBody className="features">
    <CardItem
      className="feature_icon feature_prop"
    >
      {/* Icon: Camera (For Image/Quality Check) - Styled directly for visual appeal */}
      <Camera size={40} strokeWidth={2.5} color="#ffc107" />
    </CardItem>
    <CardItem
      as="div"
      className="feature_title feature_prop"
    >
      Smart Quality Control & Authentication
    </CardItem>
    <CardItem
      as="p"
      className="feature_desc feature_prop"
    >
       Our system instantly reads and pre-fills forms from any handwritten or scanned document, saving hours.
    </CardItem>
  </CardBody>
</CardContainer>
    
    
    
    
        

    
  
         <div className='footer'>
    
        © 2024 Government of India. All rights reserved.
         </div>
     
        

</>







)


}
export default Home;