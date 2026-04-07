import { create } from "zustand";
import { api } from "../api/client";
import type { User } from "../types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (code: string) => Promise<void>;
  devLogin: () => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: true,

  login: async (code: string) => {
    const { token, user } = await api.googleAuth(code);
    localStorage.setItem("token", token);
    set({ user, loading: false });
  },

  devLogin: async () => {
    const resp = await fetch("/api/auth/dev-login", { method: "POST" });
    if (!resp.ok) throw new Error("Dev login failed");
    const { token, user } = await resp.json();
    localStorage.setItem("token", token);
    set({ user, loading: false });
  },

  logout: () => {
    localStorage.removeItem("token");
    set({ user: null, loading: false });
  },

  checkAuth: async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      set({ loading: false });
      return;
    }
    try {
      const user = await api.getMe();
      set({ user, loading: false });
    } catch {
      localStorage.removeItem("token");
      set({ user: null, loading: false });
    }
  },
}));
