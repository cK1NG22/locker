import { useState, useEffect } from "react";
import { GoogleLogin } from "@react-oauth/google";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { loginWithGoogle } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);

  useEffect(() => {
    if (localStorage.getItem("locker_session_expired") === "1") {
      setSessionExpired(true);
      localStorage.removeItem("locker_session_expired");
    }
  }, []);

  const handleSuccess = async (credentialResponse: { credential?: string }) => {
    if (!credentialResponse.credential) {
      setError("No credential received from Google.");
      return;
    }
    const ok = await loginWithGoogle(credentialResponse.credential);
    if (!ok) {
      setError("Sign-in failed. Please try again.");
    }
  };

  const handleError = () => {
    setError("Google sign-in was cancelled or failed.");
  };

  return (
    <div className="flex items-center justify-center min-h-screen px-4">
      <div className="w-full max-w-sm">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h1 className="text-lg font-semibold text-gray-900 mb-1">
            Locker Dashboard
          </h1>
          <p className="text-sm text-gray-500 mb-5">
            Sign in with your Google account to continue.
          </p>

          {sessionExpired && (
            <p className="text-sm text-amber-600 mb-4 text-center">
              Session expired, please sign in again.
            </p>
          )}

          <div className="flex justify-center">
            <GoogleLogin
              onSuccess={handleSuccess}
              onError={handleError}
              useOneTap
            />
          </div>

          {error && (
            <p className="mt-3 text-sm text-red-600 text-center">{error}</p>
          )}
        </div>
      </div>
    </div>
  );
}
