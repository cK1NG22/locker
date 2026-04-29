export const STORAGE_KEYS = {
  AUTH_TOKEN: "locker_auth_token",
  USER: "locker_user",
  SESSION_EXPIRED: "locker_session_expired",
  ACTIVE_TEAM: "locker_active_team",
} as const;

export const COPY_FEEDBACK_MS = 1500;

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "";
