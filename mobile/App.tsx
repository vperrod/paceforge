import React, { useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { StatusBar } from 'expo-status-bar';
import RootNavigator from './src/navigation/RootNavigator';
import { useAuthStore } from './src/store/auth';
import { isHealthSyncEnabled, syncHealthData } from './src/services/healthSync';

export default function App() {
  const restore = useAuthStore((s) => s.restore);
  const isLoggedIn = useAuthStore((s) => !!s.user);

  useEffect(() => {
    restore();
  }, []);

  // Auto-sync health data on app open when logged in
  useEffect(() => {
    if (!isLoggedIn) return;
    (async () => {
      try {
        const enabled = await isHealthSyncEnabled();
        if (enabled) {
          await syncHealthData(90);
        }
      } catch {
        // Silent failure — health sync is best-effort
      }
    })();
  }, [isLoggedIn]);

  return (
    <NavigationContainer>
      <StatusBar style="light" />
      <RootNavigator />
    </NavigationContainer>
  );
}
