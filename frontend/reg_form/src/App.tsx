import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom';


import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import Forms from './Forms'
function App() {

  return (
  <BrowserRouter>  
    <Routes>

       <Route path="/" element={<Forms/>} />
     </Routes>
     </BrowserRouter>

  
    
  )
}

export default App
