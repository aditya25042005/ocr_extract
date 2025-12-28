import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'; // Keep these imports

import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import Forms from './Forms'
import  Home  from './Home.jsx';
import Login from './login.jsx';
import StatusCheck from './status.jsx'
import  SelectionPage  from'./center.jsx'
import { Worker } from '@react-pdf-viewer/core';
import { Toaster } from "./components/ui/sooner.jsx"
import  VerificationReview from './approve.jsx';
function App() {

  return (
    // 1. Wrap the entire app with BrowserRouter
    <BrowserRouter> 
      <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.4.120/build/pdf.worker.min.js">
        <Toaster />

        {/* 2. Define the Routes */}
        <Routes>
          {/* Route for the Home component, accessible at the root path "/" */}
          <Route path="/" element={<Home />} />
          
          {/* Route for the Login component */}
          <Route path="/login" element={<Login />} />

          {/* Route for the Forms component */}
          <Route path="/forms" element={<Forms />} />
          <Route path="/status" element={<StatusCheck />} />
          <Route path="/center" element={<SelectionPage />} />
          <Route path="/detail/:centerId" element={<VerificationReview />} />



          {/* Add more routes here as needed */}
        </Routes>

      </Worker>
    </BrowserRouter>
  )
}

export default App