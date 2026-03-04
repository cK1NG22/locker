import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import { getStoredApiKey, setStoredApiKey, clearStoredApiKey } from "../lib/api";

interface AuthContextValue {
  apiKey: string | null;
  login: (key: string) => Promise<boolean>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [apiKey, setApiKey] = useState<string | null>(getStoredApiKey);

  const login = useCallback(async (key: string): Promise<boolean> => {
    try {
      const res = await fetch("/api/v1/skills", {
        headers: { "X-API-Key": key },
      });
      if (res.ok) {
        setStoredApiKey(key);
        setApiKey(key);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }, []);

  const logout = useCallback(() => {
    clearStoredApiKey();
    setApiKey(null);
  }, []);

  return (
    <AuthContext.Provider value={{ apiKey, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
