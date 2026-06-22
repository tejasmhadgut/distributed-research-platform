import { Routes, Route, Navigate } from "react-router-dom"
import { useAuth } from "./contexts/AuthContext"
import LoginPage from "./pages/LoginPage"
import RegisterPage from "./pages/RegisterPage"

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
        <Route path="*" element={
          <ProtectedRoute>
            <div className="flex items-center justify-center h-screen bg-background text-foreground">
              <p>Workspace coming soon</p>
            </div>
          </ProtectedRoute>
        } />
      </Routes>
    </div>
  )
}
