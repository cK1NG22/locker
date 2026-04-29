import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { GoogleOAuthProvider } from "@react-oauth/google";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Sidebar from "./components/Sidebar";
import Login from "./components/Login";
import SkillList from "./components/skills/SkillList";
import SkillDetail from "./components/skills/SkillDetail";
import SkillUpload from "./components/skills/SkillUpload";
import TeamList from "./components/teams/TeamList";
import TeamDetail from "./components/teams/TeamDetail";
import TeamForm from "./components/teams/TeamForm";
import OrgList from "./components/orgs/OrgList";
import OrgDetailPage from "./components/orgs/OrgDetail";
import OrgAnalytics from "./components/orgs/OrgAnalytics";
import ShareRequests from "./components/orgs/ShareRequests";
import FeedbackList from "./components/feedback/FeedbackList";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID ?? "";

function AuthenticatedApp() {
  const { token } = useAuth();

  if (!token) return <Login />;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-6 pt-16 md:pt-6 overflow-auto bg-gray-50">
        <Routes>
          <Route path="/skills" element={<SkillList />} />
          <Route path="/skills/upload" element={<SkillUpload />} />
          <Route path="/skills/:id" element={<SkillDetail />} />
          <Route path="/teams" element={<TeamList />} />
          <Route path="/teams/new" element={<TeamForm />} />
          <Route path="/teams/:id" element={<TeamDetail />} />
          <Route path="/feedback" element={<FeedbackList />} />
          <Route path="/orgs" element={<OrgList />} />
          <Route path="/orgs/:id" element={<OrgDetailPage />} />
          <Route path="/orgs/:id/analytics" element={<OrgAnalytics />} />
          <Route path="/teams/:id/share-requests" element={<ShareRequests />} />
          <Route path="*" element={<Navigate to="/skills" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <AuthProvider>
        <BrowserRouter basename="/dashboard">
          <AuthenticatedApp />
        </BrowserRouter>
      </AuthProvider>
    </GoogleOAuthProvider>
  );
}
