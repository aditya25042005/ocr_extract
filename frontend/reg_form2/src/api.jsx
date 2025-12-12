// src/api.js
import axios from 'axios';

// Create an Axios instance
const api = axios.create({
  baseURL: 'http://localhost:8000',  // your Django backend
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;
