import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Sidebar from "./components/Sidebar";
import Login from "./components/Login";
import SkillList from "./components/skills/SkillList";
import SkillDetail from "./components/skills/SkillDetail";
import SkillUpload from "./components/skills/SkillUpload";
import TeamList from "./components/teams/TeamList";
import TeamDetail from "./components/teams/TeamDetail";
import TeamForm from "./components/teams/TeamForm";

function AuthenticatedApp() {
  const { apiKey } = useAuth();

  if (!apiKey) return <Login />;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-6 overflow-auto">
        <Routes>
          <Route path="/skills" element={<SkillList />} />
          <Route path="/skills/upload" element={<SkillUpload />} />
          <Route path="/skills/:id" element={<SkillDetail />} />
          <Route path="/teams" element={<TeamList />} />
          <Route path="/teams/new" element={<TeamForm />} />
          <Route path="/teams/:id" element={<TeamDetail />} />
          <Route path="*" element={<Navigate to="/skills" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter basename="/dashboard">
        <AuthenticatedApp />
      </BrowserRouter>
    </AuthProvider>
  );
}
