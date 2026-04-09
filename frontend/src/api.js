// src/api.js
// Handles all backend REST API requests using Axios.
// Automatically injects the JWT auth bearer token to requests.

import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
});

// Interceptor intelligently appends exactly what we need for authentication.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Logs a user in and grabs a fresh JSON Web Token.
export const loginUser = (username, password) => {
  return api.post('/login', { username, password });
};

// Registers a new brand user and auto-generates their initial JWT.
export const registerUser = (username, password) => {
  return api.post('/register', { username, password });
};

// Scaffolds a new multiplayer document room.
export const createRoom = (name) => {
  return api.post('/rooms', { name });
};

// Returns initialization data for a specific room.
export const getRoom = (roomId) => {
  return api.get(`/rooms/${roomId}`);
};
