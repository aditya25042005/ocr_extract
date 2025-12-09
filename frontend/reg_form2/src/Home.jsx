import React, { useState } from 'react';
import Box from '@mui/material/Box';
import { Landmark } from 'lucide-react';
import { SparklesCore } from "./components/ui/sparkles";
import './Home.css';
import { BackgroundGradient } from "./components/ui/background-gradient";
import { Button } from "./components/ui/moving-border";

import { CardContainer, CardBody, CardItem } from "./components/ui/3d-card.jsx";
function  Home(){



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

 <div className='nav-title2 t1'>Sign In</div>
</div>
<div className="page-title">

<div className='page-title1 p1'>

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
                <Button className='button-main1'  borderRadius="30rem">

                     Pre-register
                         </Button>
                         </div>
          <div className='button-group1'>

          <Button className='button-main1'>
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
            
        </CardItem>
        <CardItem
          as="div"
          className="feature_title feature_prop"
        >
            quick verification
        </CardItem>
         <CardItem
          as="p"
          className="feature_desc feature_prop"
        >
        Get your passport verified in just 24-48 hours with our
      streamlined process and dedicated team.

        </CardItem>

       
      
      </CardBody>
    </CardContainer>

            <CardContainer className="inter-var">
      <CardBody className="features">
        <CardItem
          className="feature_icon feature_prop"
        >
            ak
        </CardItem>
        <CardItem
          as="div"
          className="feature_title feature_prop"
        >
            quick verification
        </CardItem>
         <CardItem
          as="p"
          className="feature_desc feature_prop"
        >
        Get your passport verified in just 24-48 hours with our
      streamlined process and dedicated team.

        </CardItem>

       
      
      </CardBody>
    </CardContainer>
            <CardContainer className="inter-var">
      <CardBody className="features">
        <CardItem
          className="feature_icon feature_prop"
        >
            ak
        </CardItem>
        <CardItem
          as="div"
          className="feature_title feature_prop"
        >
            quick verification
        </CardItem>
         <CardItem
          as="p"
          className="feature_desc feature_prop"
        >
        Get your passport verified in just 24-48 hours with our
      streamlined process and dedicated team.

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