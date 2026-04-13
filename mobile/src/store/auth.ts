import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import api from '../api/client';

interface User {
  id: string;
  name: string;
  email: string;
  role: string;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;

  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string, reason?: string) => Promise<string>;
  logout: () => Promise<void>;
  restore: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isLoading: true,
  isAuthenticated: false,

  login: async (email, password) => {
    const { data } = await api.post('/auth/login', { email, password });
    await SecureStore.setItemAsync('access_token', data.access_token);
    await SecureStore.setItemAsync('refresh_token', data.refresh_token);
    set({
      user: { id: '', name: data.name, email: data.email, role: data.role },
      isAuthenticated: true,
    });
    // Fetch full profile
    try {
      const profile = await api.get('/auth/profile');
      set({ user: profile.data });
    } catch {}
  },

  register: async (name, email, password, reason = '') => {
    const { data } = await api.post('/auth/register', { name, email, password, reason });
    return data.message;
  },

  logout: async () => {
    try {
      const refreshToken = await SecureStore.getItemAsync('refresh_token');
      if (refreshToken) {
        await api.post('/auth/logout', { refresh_token: refreshToken });
      }
    } catch {}
    await SecureStore.deleteItemAsync('access_token');
    await SecureStore.deleteItemAsync('refresh_token');
    set({ user: null, isAuthenticated: false });
  },

  restore: async () => {
    set({ isLoading: true });
    try {
      const accessToken = await SecureStore.getItemAsync('access_token');
      if (!accessToken) {
        set({ isLoading: false });
        return;
      }
      // Verify token by fetching profile
      const { data } = await api.get('/auth/profile');
      set({ user: data, isAuthenticated: true, isLoading: false });
    } catch {
      // Token expired — interceptor will try refresh automatically
      // If refresh also fails, tokens are cleared
      await SecureStore.deleteItemAsync('access_token');
      await SecureStore.deleteItemAsync('refresh_token');
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },
}));
