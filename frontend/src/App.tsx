import { Routes, Route, Navigate } from "react-router-dom"
import { useAuth } from "./contexts/AuthContext"
import { SessionsProvider } from "./contexts/SessionsContext"
import LoginPage from "./pages/LoginPage"
import RegisterPage from "./pages/RegisterPage"
import WorkspacePage from "./pages/WorkspacePage"

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <div>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/session/:sessionId" element={
          <ProtectedRoute><SessionsProvider><WorkspacePage /></SessionsProvider></ProtectedRoute>
        } />
        <Route path="*" element={
          <ProtectedRoute><SessionsProvider><WorkspacePage /></SessionsProvider></ProtectedRoute>
        } />
      </Routes>
    </div>
  )
}
