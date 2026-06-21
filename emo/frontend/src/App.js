import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ROUTER_BASENAME } from "@/lib/paths";
import ThemedToaster from "@/components/ThemedToaster";
import ErrorBoundary from "@/components/ErrorBoundary";
import Login from "@/pages/Login";
import GoogleAuthCallback from "@/pages/GoogleAuthCallback";
import Chat from "@/pages/Chat";

function App() {
  return (
    <div className="App">
      <ThemedToaster />
      <ErrorBoundary label="Application">
        <BrowserRouter basename={ROUTER_BASENAME}>
          <Routes>
            <Route path="/" element={<Navigate to="/chat" replace />} />
            <Route path="/login" element={<Login />} />
            <Route path="/auth/google/callback" element={<GoogleAuthCallback />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="*" element={<Navigate to="/chat" replace />} />
          </Routes>
        </BrowserRouter>
      </ErrorBoundary>
    </div>
  );
}

export default App;
