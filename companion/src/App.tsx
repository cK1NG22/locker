import { useState, useEffect } from "react";
import TokenSetup from "./components/TokenSetup";
import SkillList from "./components/SkillList";
import { SetupWizard } from "./components/SetupWizard";
import Onboarding from "./components/Onboarding";
import { useSkills } from "./hooks/useSkills";

const TOKEN_KEY = "locker_team_token";
const ONBOARDING_KEY = "locker_onboarding_complete";

function getJoinToken(): string | null {
  const params = new URLSearchParams(window.location.search);
  return params.get("join") || null;
}

export default function App() {
  const [joinToken] = useState<string | null>(getJoinToken);
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem(TOKEN_KEY),
  );
  const [onboardingComplete, setOnboardingComplete] = useState(
    () => localStorage.getItem(ONBOARDING_KEY) === "1",
  );

  const { team, convention, skills, loading, error } = useSkills(token);

  // If we have a token saved but it's invalid, stay on the form with the error
  const showSetup = !token || (error !== null && error === "Invalid team token");

  useEffect(() => {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  }, [token]);

  const handleChangeToken = () => {
    setToken(null);
  };

  const handleOnboardingComplete = (newToken: string) => {
    setToken(newToken);
    setOnboardingComplete(true);
    localStorage.setItem(ONBOARDING_KEY, "1");
  };

  const handleResetOnboarding = () => {
    setToken(null);
    setOnboardingComplete(false);
    localStorage.removeItem(ONBOARDING_KEY);
  };

  // Show onboarding if no token and not previously completed
  if (!token && !onboardingComplete) {
    return <Onboarding onComplete={handleOnboardingComplete} initialToken={joinToken} />;
  }

  if (showSetup) {
    return <TokenSetup onSubmit={setToken} error={token ? error : null} initialToken={joinToken} />;
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-sm text-gray-500">Loading skills...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="text-center">
          <p className="text-sm text-red-600 mb-4">{error}</p>
          <button
            onClick={handleChangeToken}
            className="text-sm text-blue-600 hover:underline"
          >
            Change token
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto">
      <SkillList
        team={team!}
        skills={skills}
        convention={convention}
        token={token!}
        onChangeToken={handleChangeToken}
      />
      <div className="px-4 pb-8">
        <SetupWizard token={token!} convention={convention} />
      </div>
    </div>
  );
}
