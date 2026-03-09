"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { GoogleLogin } from "@react-oauth/google";
import { useAuth } from "@/context/AuthContext";
import { API_URL } from "@/lib/constants";

interface TeamInfo {
  name: string;
  slug: string;
  skill_count: number;
  member_count: number;
}

interface JoinResult {
  team_id: string;
  team_name: string;
  setup_command: string | null;
  convention: string;
  already_member: boolean;
}

export default function InvitePage({ slug }: { slug: string }) {
  const router = useRouter();
  const { token, loginWithGoogle } = useAuth();
  const [teamInfo, setTeamInfo] = useState<TeamInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [joinResult, setJoinResult] = useState<JoinResult | null>(null);
  const [joining, setJoining] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Fetch team info (public, no auth)
  useEffect(() => {
    fetch(`${API_URL}/api/v1/invite/${slug}`)
      .then(async (res) => {
        if (!res.ok) {
          if (res.status === 404) throw new Error("Team not found");
          throw new Error("Failed to load team info");
        }
        return res.json();
      })
      .then(setTeamInfo)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [slug]);

  // Auto-join after authentication
  useEffect(() => {
    if (!token || !teamInfo || joinResult) return;
    setJoining(true);
    fetch(`${API_URL}/api/v1/invite/${slug}/join`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => {
        if (!res.ok) throw new Error("Failed to join team");
        return res.json();
      })
      .then(setJoinResult)
      .catch((e) => setError(e.message))
      .finally(() => setJoining(false));
  }, [token, teamInfo, slug, joinResult]);

  const handleGoogleSuccess = async (credentialResponse: { credential?: string }) => {
    setAuthError(null);
    if (!credentialResponse.credential) {
      setAuthError("No credential received from Google.");
      return;
    }
    const ok = await loginWithGoogle(credentialResponse.credential);
    if (!ok) {
      setAuthError("Sign-in failed. Please try again.");
    }
  };

  const copyCommand = async () => {
    if (!joinResult?.setup_command) return;
    await navigator.clipboard.writeText(joinResult.setup_command);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-sm text-gray-500">Loading...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="max-w-sm w-full bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-center">
          <h1 className="text-lg font-semibold text-gray-900 mb-2">Oops</h1>
          <p className="text-sm text-red-600">{error}</p>
        </div>
      </div>
    );
  }

  if (!teamInfo) return null;

  // Step 3: Joined — show setup
  if (joinResult) {
    return (
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="max-w-lg w-full">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h1 className="text-lg font-semibold text-gray-900 mb-1">
              {joinResult.already_member ? "Welcome back!" : "You're in!"}
            </h1>
            <p className="text-sm text-gray-500 mb-6">
              {joinResult.already_member
                ? `You're already a member of ${joinResult.team_name}.`
                : `You've joined ${joinResult.team_name} on Locker.`}
            </p>

            {/* Setup section */}
            <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 space-y-4">
              <h2 className="text-sm font-medium text-gray-800">Configure Claude Code</h2>

              <div>
                <p className="text-sm text-gray-600 mb-2">
                  1. Copy this command and paste it into your terminal:
                </p>
                {joinResult.setup_command ? (
                  <div className="relative bg-gray-900 rounded-md p-3 font-mono text-xs text-green-400 overflow-x-auto">
                    {joinResult.setup_command}
                    <button
                      onClick={copyCommand}
                      className="absolute top-2 right-2 text-xs bg-gray-700 hover:bg-gray-600 text-white px-2 py-1 rounded"
                    >
                      {copied ? "Copied!" : "Copy"}
                    </button>
                  </div>
                ) : (
                  <p className="text-sm text-amber-600">
                    Setup command unavailable. Ask your team admin to rotate the team token.
                  </p>
                )}
              </div>

              <div className="text-sm text-gray-600 space-y-2">
                <p>2. Restart Claude Code.</p>
                <p>3. Type <code className="bg-gray-200 px-1.5 py-0.5 rounded text-gray-800">{joinResult.convention} list_skills</code> to see your team&apos;s skills.</p>
              </div>

              <div className="text-xs text-gray-400 border-t border-gray-200 pt-3">
                <p className="font-medium text-gray-500 mb-1">What does this command do?</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>Configures Claude Code&apos;s MCP settings to connect to your team&apos;s Locker</li>
                  <li>Installs the <code>/locker</code> skill router command</li>
                  <li>No data leaves your machine — the token stays in your local config</li>
                </ul>
              </div>
            </div>

            <button
              onClick={() => router.push(`/dashboard?team=${joinResult.team_id}`)}
              className="mt-4 w-full px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
            >
              Go to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Step 1: Not authenticated — show invite + sign in
  if (!token) {
    return (
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="max-w-sm w-full">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h1 className="text-lg font-semibold text-gray-900 mb-1">
              Join {teamInfo.name}
            </h1>
            <p className="text-sm text-gray-500 mb-2">
              You&apos;ve been invited to join <span className="font-medium">{teamInfo.name}</span> on Locker.
            </p>
            <p className="text-xs text-gray-400 mb-5">
              {teamInfo.skill_count} skill{teamInfo.skill_count !== 1 ? "s" : ""} &middot;{" "}
              {teamInfo.member_count} member{teamInfo.member_count !== 1 ? "s" : ""}
            </p>

            <div className="bg-gray-50 rounded-md p-3 mb-5">
              <p className="text-xs text-gray-500">
                <span className="font-medium text-gray-700">What is Locker?</span> Locker lets teams
                share proprietary skills (instructions, templates, workflows) with Claude Code —
                encrypted and invisible to end users.
              </p>
            </div>

            <div className="flex justify-center">
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={() => setAuthError("Google sign-in was cancelled or failed.")}
                useOneTap
              />
            </div>

            {authError && (
              <p className="mt-3 text-sm text-red-600 text-center">{authError}</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Step 2: Authenticated, joining...
  if (joining) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-sm text-gray-500">Joining {teamInfo.name}...</p>
      </div>
    );
  }

  return null;
}
