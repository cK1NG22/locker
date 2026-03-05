import { useState } from "react";

interface Props { token: string; }

export function SetupWizard({ token }: Props) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const serverUrl = window.location.origin;
  const cmd = `curl -fsSL ${serverUrl}/setup/${token} | bash`;

  function copy() {
    navigator.clipboard.writeText(cmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="mt-6 border border-gray-200 rounded-lg">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex justify-between items-center px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50"
      >
        <span>Connect to Claude Code</span>
        <span className="text-gray-400">{open ? "−" : "+"}</span>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-4 text-sm text-gray-600">
          <div className="space-y-3">
            <div><span className="font-medium text-gray-800">Step 1 —</span> Run this command in your terminal:</div>
            <div className="relative bg-gray-900 rounded-md p-3 font-mono text-xs text-green-400 overflow-x-auto">
              {cmd}
              <button
                onClick={copy}
                className="absolute top-2 right-2 text-xs bg-gray-700 hover:bg-gray-600 text-white px-2 py-1 rounded"
              >
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
            <div><span className="font-medium text-gray-800">Step 2 —</span> Restart Claude Code.</div>
            <div><span className="font-medium text-gray-800">Step 3 —</span> Type <code className="bg-gray-100 px-1 rounded">/locker code-review</code> to try a skill.</div>
          </div>
        </div>
      )}
    </div>
  );
}
