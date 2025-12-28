import React, { useState } from 'react';
import './login.css'
import { Landmark, ShieldCheck, Mail, Lock, HelpCircle } from 'lucide-react'; // Added icons
import { SparklesCore } from "./components/ui/sparkles";
import { Input } from "./components/ui/input"
import {
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
} from "./components/ui/input-otp"
import { useRef } from 'react';
import api from './api';
import { useNavigate } from 'react-router-dom'; // 1. Import useNavigate
import { Toaster } from 'sonner';
function Login() {
  const navigate = useNavigate(); // 2. Initialize useNavigate
  let  [email, setEmail ] = useState('');
  let  [otp, setotp ] = useState('');

  const otp_check = useRef(null);

  function otp_button(){
    if(otp_check.current.innerText==="Verify & Proceed"){
          api.post('api/verify-otp/', {
        'email':email,
        'otp':otp
  })
  .then(function (response) {
console.log(response);
console.log('Value to be stored:', email);
localStorage.setItem('email', email);
setTimeout(() => {
                    navigate('/forms'); // Navigate only after a brief delay
                }, 50); // 50 milliseconds is usually enough to prevent the race condition

  })
  .catch(function (error) {
          Toaster.error("Error in login. Please try again.");

    console.log(error);
  });


    }
    else{
    otp_check.current.innerText = "Proceesing";
      //try catch vs then
      api.post('api/send-otp/', {
        'email':email
   
  })
  .then(function (response) {
    console.log(response);
    if(response.status===200){
      otp_check.current.innerText = "Verify & Proceed";
    }
    else{
      Toaster.error("Error sending OTP. Please try again.");
      otp_check.current.innerText = "Send OTP";
    }
  })
  .catch(function (error) {
    console.log(error);
  });
    }
  }
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
        {/* Radial Gradient */}
        <div className="absolute inset-0 w-full h-full bg-white [mask-image:radial-gradient(100vw_120vh_at_top,transparent_20%,white)]"></div>
      </div>

      <div className='nav-header'>
        <div className='nav-title1 t1'>
          <Landmark />
          Passport Verification Portal
        </div>
        <div className='nav-title2 t1'>Help Center</div>
      </div>

      <div className="login-box">
        
        {/* NEW: Card Header */}
        <div className="box-header">
            <div className="icon-bg">
                <ShieldCheck size={40} color="#1a3b5d" />
            </div>
            <h2 className="header-title">Applicant Verification</h2>
            <p className="header-desc">
                Securely log in to verify your passport details.
            </p>
        </div>

        {/* Existing Inputs */}
        <div className='login-box-section'>
          <div className='login-box-email box-part1'>
             <Mail size={18} style={{marginRight: '8px', verticalAlign: 'middle'}}/>
             Email Address
          </div>
          <Input type='email' placeholder="e.g. karn@gmail.com" className="login-email box-part2"  onChange={(e)=>{setEmail(e.target.value)}} />
          <p className="input-hint">We'll send a 6-digit code to this email.</p>
        </div>

        <div className="login-box-section">
          <div className='login-box-otp box-part1'>
             <Lock size={18} style={{marginRight: '80px', verticalAlign: 'middle'}}/>
             Enter OTP
          </div>
          <InputOTP maxLength={6} className="box-part2"  onChange={(value)=>{setotp(value)}}>
            <InputOTPGroup>
              <InputOTPSlot index={0} />
              <InputOTPSlot index={1} />
              <InputOTPSlot index={2} />
              <InputOTPSlot index={3} />
              <InputOTPSlot index={4} />
              <InputOTPSlot index={5} />
            </InputOTPGroup>
          </InputOTP>
        </div>

   <button className='login-button' ref={otp_check} onClick={()=>{otp_button()}}>Send OTP</button>
     
        {/* NEW: Footer Links */}
        <div className="box-footer">
            <div className="footer-link">
            </div>
            <p className="footer-note">By continuing, you agree to the <span className="blue-text">Terms of Service</span>.</p>
        </div>

      </div>
      
         <div className='footer'>
    
        © 2024 Government of India. All rights reserved.
         </div>
     
        

    </>
  )
}

export default Login;