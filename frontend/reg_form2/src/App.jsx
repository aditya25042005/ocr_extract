import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom';


import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import Forms from './Forms'
import  Home  from './Home.jsx';
import Login from './login.jsx';
import { Worker } from '@react-pdf-viewer/core';

function App() {

  return (
    <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.4.120/build/pdf.worker.min.js">

  <Forms/>
  </Worker>

  
    
  )
}

export default App
