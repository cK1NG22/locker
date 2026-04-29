import { useState } from "react";
import { ONBOARDING_STEPS, STEP_LABELS } from "../content/onboarding";

interface OnboardingProps {
  onComplete: (token: string) => void;
  initialToken?: string | null;
}

export default function Onboarding({ onComplete, initialToken }: OnboardingProps) {
  const [step, setStep] = useState(0);
  const [token, setToken] = useState(initialToken ?? "");
  const [error, setError] = useState<string | null>(null);
  const [validating, setValidating] = useState(false);

  const current = ONBOARDING_STEPS[step];

  const handleConnect = async () => {
    const trimmed = token.trim();
    if (!trimmed) return;
    setValidating(true);
    setError(null);
    try {
      const res = await fetch("/api/v1/employee/skills", {
        headers: { "X-Team-Token": trimmed },
      });
      if (res.status === 401) {
        setError("Invalid team token. Check with your admin.");
        return;
      }
      if (!res.ok) {
        setError(`Server error (${res.status})`);
        return;
      }
      setStep(3); // success step
    } catch {
      setError("Cannot reach server");
    } finally {
      setValidating(false);
    }
  };

  const handleFinish = () => {
    onComplete(token.trim());
  };

  return (
    <div className="flex items-center justify-center min-h-screen px-4">
      <div className="w-full max-w-md">
        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {STEP_LABELS.map((label, i) => (
            <div key={label} className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full transition-colors ${
                  i <= step ? "bg-blue-600" : "bg-gray-300"
                }`}
              />
              {i < STEP_LABELS.length - 1 && (
                <div className={`w-6 h-px ${i < step ? "bg-blue-600" : "bg-gray-300"}`} />
              )}
            </div>
          ))}
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          {/* Step 0: Welcome */}
          {step === 0 && (
            <>
              <h1 className="text-xl font-semibold text-gray-900 mb-2">
                {current.title}
              </h1>
              <p className="text-sm text-gray-600 mb-6">
                {"description" in current && current.description}
              </p>
              <button
                onClick={() => setStep(1)}
                className="w-full py-2 px-4 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
              >
                Get started
              </button>
            </>
          )}

          {/* Step 1: How it works */}
          {step === 1 && (
            <>
              <h1 className="text-xl font-semibold text-gray-900 mb-4">
                {current.title}
              </h1>
              <div className="space-y-4 mb-6">
                {"panels" in current &&
                  current.panels.map((panel, i) => (
                    <div key={i} className="flex gap-3">
                      <div className="shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-xs font-bold flex items-center justify-center">
                        {i + 1}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {panel.heading}
                        </p>
                        <p className="text-sm text-gray-500">{panel.detail}</p>
                      </div>
                    </div>
                  ))}
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setStep(0)}
                  className="flex-1 py-2 px-4 border border-gray-300 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-50 transition-colors"
                >
                  Back
                </button>
                <button
                  onClick={() => setStep(2)}
                  className="flex-1 py-2 px-4 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
                >
                  Next
                </button>
              </div>
            </>
          )}

          {/* Step 2: Token input */}
          {step === 2 && (
            <>
              <h1 className="text-xl font-semibold text-gray-900 mb-2">
                {current.title}
              </h1>
              <p className="text-sm text-gray-600 mb-4">
                {"description" in current && current.description}
              </p>
              <input
                type="text"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Paste team token here"
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleConnect();
                }}
              />
              {error && (
                <p className="mt-2 text-sm text-red-600">{error}</p>
              )}
              <div className="flex gap-3 mt-4">
                <button
                  onClick={() => setStep(1)}
                  className="flex-1 py-2 px-4 border border-gray-300 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-50 transition-colors"
                >
                  Back
                </button>
                <button
                  onClick={handleConnect}
                  disabled={!token.trim() || validating}
                  className="flex-1 py-2 px-4 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {validating ? "Connecting..." : "Connect"}
                </button>
              </div>
            </>
          )}

          {/* Step 3: Success */}
          {step === 3 && (
            <>
              <h1 className="text-xl font-semibold text-gray-900 mb-2">
                {ONBOARDING_STEPS[3].title}
              </h1>
              <p className="text-sm text-gray-600 mb-6">
                {ONBOARDING_STEPS[3].description}
              </p>
              <button
                onClick={handleFinish}
                className="w-full py-2 px-4 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
              >
                View skills
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
