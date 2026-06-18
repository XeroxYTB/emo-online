import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ROUTER_BASENAME } from "@/lib/paths";
import { Toaster } from "sonner";
import Login from "@/pages/Login";
import GoogleAuthCallback from "@/pages/GoogleAuthCallback";
import Chat from "@/pages/Chat";

function App() {
  return (
    <div className="App">
      <Toaster
        theme="dark"
        position="top-right"
        toastOptions={{
          style: {
            background: "rgba(18, 11, 26, 0.95)",
            border: "1px solid rgba(168, 85, 247, 0.2)",
            color: "#F3E8FF",
          },
        }}
      />
      <BrowserRouter basename={ROUTER_BASENAME}>
        <Routes>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="/login" element={<Login />} />
          <Route path="/auth/google/callback" element={<GoogleAuthCallback />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
