import React from 'react';
import AppRouter from './AppRouter';
import { AuthProvider } from './components/Auth';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <div className="App">
        <AppRouter />
      </div>
    </AuthProvider>
  );
}

export default App;
