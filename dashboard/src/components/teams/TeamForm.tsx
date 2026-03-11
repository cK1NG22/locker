import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useTeams } from "../../hooks/useTeams";
import { useSkills } from "../../hooks/useSkills";
import { copyToClipboard } from "../../lib/clipboard";

interface CreatedTeam {
  id: string;
  token: string;
  invite_code: string | null;
  name: string;
}

function StepIndicator({ step }: { step: 1 | 2 | 3 }) {
  const labels = ["Create Team", "Add Skill", "Invite Member"];
  return (
    <div className="flex items-center justify-center mb-8">
      {labels.map((label, i) => {
        const num = i + 1;
        const isComplete = num < step;
        const isCurrent = num === step;
        return (
          <div key={num} className="flex items-center">
            {i > 0 && (
              <div
                className={`w-12 h-0.5 ${num <= step ? "bg-blue-600" : "bg-gray-200"}`}
              />
            )}
            <div className="flex flex-col items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  isCurrent
                    ? "bg-blue-600 text-white"
                    : isComplete
                      ? "bg-blue-600 text-white"
                      : "bg-gray-200 text-gray-500"
                }`}
              >
                {isComplete ? "\u2713" : num}
              </div>
              <span
                className={`text-xs mt-1 ${isCurrent ? "text-blue-600 font-medium" : "text-gray-400"}`}
              >
                {label}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function TokenDisplay({
  token,
  copied,
  onCopy,
}: {
  token: string;
  copied: boolean;
  onCopy: () => void;
}) {
  return (
    <div className="mb-4">
      <label className="text-xs text-gray-400 uppercase tracking-wide">
        Team Token
      </label>
      <div className="mt-1 flex items-center gap-2">
        <code className="flex-1 bg-gray-100 px-3 py-2 rounded text-sm font-mono text-gray-700 select-all">
          {token}
        </code>
        <button
          onClick={onCopy}
          className="px-3 py-2 text-sm border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
        >
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <p className="text-xs text-gray-400 mt-1">
        Share this token with team members for the Companion page.
      </p>
    </div>
  );
}

export default function TeamForm() {
  const navigate = useNavigate();
  const { createTeam, setTeamSkills, addMember } = useTeams();
  const { createSkill } = useSkills();

  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [createdTeam, setCreatedTeam] = useState<CreatedTeam | null>(null);

  // Step 1
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Token / invite code copy
  const [copied, setCopied] = useState(false);
  const [inviteCodeCopied, setInviteCodeCopied] = useState(false);

  // Step 2
  const [skillName, setSkillName] = useState("");
  const [skillContent, setSkillContent] = useState("");
  const [uploadingSkill, setUploadingSkill] = useState(false);
  const [skillError, setSkillError] = useState<string | null>(null);
  const [skillSuccess, setSkillSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Step 3
  const [memberEmail, setMemberEmail] = useState("");
  const [inviting, setInviting] = useState(false);
  const [memberError, setMemberError] = useState<string | null>(null);
  const [memberSuccess, setMemberSuccess] = useState(false);
  const [memberNotFound, setMemberNotFound] = useState(false);
  const [signupCopied, setSignupCopied] = useState(false);

  const copyToken = async () => {
    if (!createdTeam) return;
    await copyToClipboard(createdTeam.token, setCopied);
  };

  const handleCreateTeam = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const result = await createTeam(name.trim());
      setCreatedTeam({ id: result.id, token: result.token, invite_code: result.invite_code, name: name.trim() });
      setStep(2);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Create failed");
    } finally {
      setSaving(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      setSkillContent(reader.result as string);
      if (!skillName) {
        setSkillName(file.name.replace(/\.[^.]+$/, ""));
      }
    };
    reader.readAsText(file);
  };

  const handleUploadSkill = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createdTeam || !skillName.trim() || !skillContent.trim()) return;
    setUploadingSkill(true);
    setSkillError(null);
    try {
      const result = await createSkill({
        name: skillName.trim(),
        content: skillContent.trim(),
        scope: "team",
      });
      await setTeamSkills(createdTeam.id, [result.id]);
      setSkillSuccess(true);
    } catch (e) {
      setSkillError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploadingSkill(false);
    }
  };

  const handleInviteMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createdTeam || !memberEmail.trim()) return;
    setInviting(true);
    setMemberError(null);
    setMemberNotFound(false);
    try {
      await addMember(createdTeam.id, memberEmail.trim());
      setMemberSuccess(true);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Invite failed";
      if (msg.includes("404") || msg.toLowerCase().includes("not found")) {
        setMemberNotFound(true);
      } else {
        setMemberError(msg);
      }
    } finally {
      setInviting(false);
    }
  };

  const finish = () => {
    if (createdTeam) navigate(`/teams/${createdTeam.id}`);
  };

  return (
    <div className="max-w-md">
      <button
        onClick={() => navigate("/teams")}
        className="text-sm text-gray-500 hover:text-gray-700 mb-4 transition-colors"
      >
        &larr; Back to teams
      </button>

      {createdTeam && (
        <p className="text-sm text-gray-500 mb-2">
          Team: <span className="font-medium text-gray-900">{createdTeam.name}</span>
        </p>
      )}

      <StepIndicator step={step} />

      {/* Step 1: Create Team */}
      {step === 1 && (
        <>
          <h2 className="text-lg font-semibold text-gray-900 mb-6">
            Create Team
          </h2>
          <form onSubmit={handleCreateTeam} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Team name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Legal, Sales, Engineering"
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                autoFocus
              />
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <button
              type="submit"
              disabled={!name.trim() || saving}
              className="w-full py-2 px-4 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {saving ? "Creating..." : "Create team"}
            </button>
          </form>
        </>
      )}

      {/* Step 2: Upload First Skill */}
      {step === 2 && createdTeam && (
        <>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Add Your First Skill
          </h2>

          <TokenDisplay token={createdTeam.token} copied={copied} onCopy={copyToken} />

          {createdTeam.invite_code && (
            <div className="mb-4">
              <label className="text-xs text-gray-400 uppercase tracking-wide">
                Invite Code
              </label>
              <div className="mt-1 flex items-center gap-2">
                <code className="flex-1 bg-gray-100 px-3 py-2 rounded text-sm font-mono text-gray-700 tracking-wider select-all">
                  {createdTeam.invite_code}
                </code>
                <button
                  onClick={() => copyToClipboard(createdTeam.invite_code!, setInviteCodeCopied)}
                  className="px-3 py-2 text-sm border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
                >
                  {inviteCodeCopied ? "Copied!" : "Copy"}
                </button>
              </div>
              <p className="text-xs text-gray-400 mt-1">
                Share this code with team members so they can join from their dashboard.
              </p>
            </div>
          )}

          {skillSuccess ? (
            <div className="space-y-4">
              <p className="text-sm text-green-600 font-medium">
                Skill added and assigned to your team!
              </p>
              <button
                onClick={() => setStep(3)}
                className="w-full py-2 px-4 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
              >
                Next: Invite a member
              </button>
            </div>
          ) : (
            <form onSubmit={handleUploadSkill} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Skill name
                </label>
                <input
                  type="text"
                  value={skillName}
                  onChange={(e) => setSkillName(e.target.value)}
                  placeholder="e.g. Legal Brief Template"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Skill content
                </label>
                <textarea
                  value={skillContent}
                  onChange={(e) => setSkillContent(e.target.value)}
                  placeholder="Paste or type your skill content here..."
                  rows={6}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y"
                />
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".md,.txt"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="text-xs text-blue-600 hover:underline mt-1"
                >
                  or upload a file
                </button>
              </div>
              {skillError && <p className="text-sm text-red-600">{skillError}</p>}
              <button
                type="submit"
                disabled={!skillName.trim() || !skillContent.trim() || uploadingSkill}
                className="w-full py-2 px-4 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {uploadingSkill ? "Uploading..." : "Add skill"}
              </button>
              <button
                type="button"
                onClick={() => setStep(3)}
                className="w-full text-sm text-gray-500 hover:text-gray-700 transition-colors"
              >
                Skip this step
              </button>
            </form>
          )}
        </>
      )}

      {/* Step 3: Invite First Member */}
      {step === 3 && createdTeam && (
        <>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Invite a Team Member
          </h2>

          {memberSuccess ? (
            <div className="space-y-4">
              <p className="text-sm text-green-600 font-medium">
                Member invited!
              </p>
              <button
                onClick={finish}
                className="w-full py-2 px-4 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
              >
                Go to team
              </button>
            </div>
          ) : memberNotFound ? (
            <div className="space-y-4">
              <p className="text-sm text-gray-700">
                <span className="font-medium">{memberEmail}</span> hasn't joined
                Locker yet. Share this link so they can sign up:
              </p>
              <div className="flex items-center gap-2">
                <code className="flex-1 bg-gray-100 px-3 py-2 rounded text-sm font-mono text-gray-700 select-all truncate">
                  {window.location.origin}/dashboard
                </code>
                <button
                  onClick={() => copyToClipboard(`${window.location.origin}/dashboard`, setSignupCopied)}
                  className="px-3 py-2 text-sm border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
                >
                  {signupCopied ? "Copied!" : "Copy"}
                </button>
              </div>
              <button
                onClick={finish}
                className="w-full py-2 px-4 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
              >
                Finish setup
              </button>
            </div>
          ) : (
            <form onSubmit={handleInviteMember} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email address
                </label>
                <input
                  type="email"
                  value={memberEmail}
                  onChange={(e) => setMemberEmail(e.target.value)}
                  placeholder="colleague@company.com"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  autoFocus
                />
              </div>
              {memberError && <p className="text-sm text-red-600">{memberError}</p>}
              <button
                type="submit"
                disabled={!memberEmail.trim() || inviting}
                className="w-full py-2 px-4 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {inviting ? "Inviting..." : "Invite"}
              </button>
              <button
                type="button"
                onClick={finish}
                className="w-full text-sm text-gray-500 hover:text-gray-700 transition-colors"
              >
                Skip — finish setup
              </button>
            </form>
          )}
        </>
      )}
    </div>
  );
}
