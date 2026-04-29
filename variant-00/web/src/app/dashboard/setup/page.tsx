"use client";

import { useState, useEffect } from "react";
import { useTeamContext } from "@/context/TeamContext";
import { api } from "@/lib/api";

export default function SetupPage() {
  const { activeTeam, loading: teamLoading } = useTeamContext();
  const [setupCommand, setSetupCommand] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (teamLoading || !activeTeam?.slug) return;
    setLoading(true);
    api
      .get<{ setup_command: string }>(`/api/v1/invite/${activeTeam.slug}/setup`)
      .then((data) => {
        setSetupCommand(data.setup_command);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load setup"))
      .finally(() => setLoading(false));
  }, [activeTeam?.slug, teamLoading]);

  const copyCommand = async () => {
    if (!setupCommand) return;
    await navigator.clipboard.writeText(setupCommand);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (teamLoading || loading) {
    return <p className="text-sm text-gray-500">Loading setup...</p>;
  }

  if (error) {
    return <p className="text-sm text-red-600">{error}</p>;
  }

  return (
    <div className="max-w-lg">
      <h2 className="text-lg font-semibold text-gray-900 mb-1">Setup</h2>
      <p className="text-sm text-gray-500 mb-6">
        Configure Claude Code to connect to {activeTeam?.team_name}.
      </p>

      <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 space-y-4">
        <div>
          <p className="text-sm text-gray-600 mb-2">
            Copy this command and paste it into your terminal:
          </p>
          {setupCommand ? (
            <div className="relative bg-gray-900 rounded-md p-3 font-mono text-xs text-green-400 overflow-x-auto">
              {setupCommand}
              <button
                onClick={copyCommand}
                className="absolute top-2 right-2 text-xs bg-gray-700 hover:bg-gray-600 text-white px-2 py-1 rounded"
              >
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
          ) : (
            <p className="text-sm text-amber-600">
              Setup command unavailable. Ask your team admin to rotate the team
              token.
            </p>
          )}
        </div>

        <div className="text-sm text-gray-600 space-y-2">
          <p>Then restart Claude Code.</p>
          <p>
            Type{" "}
            <code className="bg-gray-200 px-1.5 py-0.5 rounded text-gray-800">
              /locker list_skills
            </code>{" "}
            to see your team&apos;s skills.
          </p>
        </div>

        <div className="text-xs text-gray-400 border-t border-gray-200 pt-3">
          <p className="font-medium text-gray-500 mb-1">
            What does this command do?
          </p>
          <ul className="list-disc list-inside space-y-1">
            <li>
              Configures Claude Code&apos;s MCP settings to connect to your
              team&apos;s Locker
            </li>
            <li>
              Installs the <code>/locker</code> skill router command
            </li>
            <li>
              No data leaves your machine — the token stays in your local config
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
