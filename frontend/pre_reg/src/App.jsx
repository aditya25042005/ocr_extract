import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import Pages from './components/pages.tsx'
function App() {
  const [count, setCount] = useState(0)

  return (
    <>
    <Pages/>
    </>
  )
}

export default App
