import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import { getStoredToken, setStoredToken, clearStoredToken } from "../lib/api";

interface User {
  id: string;
  email: string;
  name: string;
}

interface AuthContextValue {
  token: string | null;
  user: User | null;
  loginWithGoogle: (googleToken: string) => Promise<boolean>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(getStoredToken);
  const [user, setUser] = useState<User | null>(() => {
    const stored = localStorage.getItem("locker_user");
    return stored ? JSON.parse(stored) : null;
  });

  const loginWithGoogle = useCallback(async (googleToken: string): Promise<boolean> => {
    try {
      const res = await fetch("/api/v1/auth/google", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: googleToken }),
      });
      if (!res.ok) return false;
      const data = await res.json();
      setStoredToken(data.access_token);
      setToken(data.access_token);
      setUser(data.user);
      localStorage.setItem("locker_user", JSON.stringify(data.user));
      return true;
    } catch {
      return false;
    }
  }, []);

  const logout = useCallback(() => {
    clearStoredToken();
    localStorage.removeItem("locker_user");
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, user, loginWithGoogle, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
