import { useState, useEffect } from "react";
import TokenSetup from "./components/TokenSetup";
import SkillList from "./components/SkillList";
import { useSkills } from "./hooks/useSkills";

const TOKEN_KEY = "locker_team_token";

export default function App() {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem(TOKEN_KEY),
  );

  const { team, skills, loading, error } = useSkills(token);

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

  if (showSetup) {
    return <TokenSetup onSubmit={setToken} error={token ? error : null} />;
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
    <SkillList
      team={team!}
      skills={skills}
      onChangeToken={handleChangeToken}
    />
  );
}
