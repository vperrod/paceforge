import React from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  Alert, Platform, Switch, ActivityIndicator,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { colors, spacing, fontSize } from '../theme';
import { useAuthStore } from '../store/auth';
import api from '../api/client';
import { syncHealthData } from '../services/healthSync';

export default function ProfileScreen() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigation = useNavigation<any>();
  const [profile, setProfile] = React.useState<any>(null);
  const [healthEnabled, setHealthEnabled] = React.useState(false);
  const [healthSyncing, setHealthSyncing] = React.useState(false);
  const [lastSync, setLastSync] = React.useState<string | null>(null);
  const [garminStatus, setGarminStatus] = React.useState<{ connected: boolean } | null>(null);

  React.useEffect(() => {
    loadProfile();
    loadHealthPrefs();
    loadGarminStatus();
  }, []);

  const loadProfile = async () => {
    try {
      const { data } = await api.get('/profile');
      setProfile(data);
    } catch {}
  };

  const loadGarminStatus = async () => {
    try {
      const { data } = await api.get('/garmin/status');
      setGarminStatus(data);
    } catch {}
  };

  const loadHealthPrefs = async () => {
    try {
      const { data } = await api.get('/preferences');
      const hc = data?.health_connections ?? {};
      const enabled = Platform.OS === 'ios' ? !!hc.apple_health : !!hc.google_health_connect;
      setHealthEnabled(enabled);

      const hd = await api.get('/health/data');
      if (hd.data?.last_sync) {
        setLastSync(hd.data.last_sync.slice(0, 16).replace('T', ' '));
      }
    } catch {}
  };

  const toggleHealth = async (value: boolean) => {
    setHealthEnabled(value);
    try {
      const key = Platform.OS === 'ios' ? 'apple_health' : 'google_health_connect';
      await api.put('/preferences', { health_connections: { [key]: value } });
      if (value) handleHealthSync();
    } catch {
      setHealthEnabled(!value);
      Alert.alert('Error', 'Failed to update health connection');
    }
  };

  const handleHealthSync = async () => {
    setHealthSyncing(true);
    try {
      const result = await syncHealthData(90);
      if (result?.last_sync) setLastSync(result.last_sync.slice(0, 16).replace('T', ' '));
      Alert.alert('Success', 'Health data synced successfully');
    } catch {
      Alert.alert('Error', 'Failed to sync health data');
    } finally {
      setHealthSyncing(false);
    }
  };

  const handleLogout = () => {
    Alert.alert('Logout', 'Are you sure you want to log out?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Logout', style: 'destructive', onPress: logout },
    ]);
  };

  const initials = user?.name
    ?.split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2) || '?';

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{initials}</Text>
        </View>
        <Text style={styles.name}>{user?.name || 'Runner'}</Text>
        <Text style={styles.email}>{user?.email}</Text>
      </View>

      {profile && (
        <View style={styles.statsRow}>
          {profile.vo2_max && (
            <View style={styles.statPill}>
              <Text style={styles.statValue}>{Math.round(profile.vo2_max)}</Text>
              <Text style={styles.statLabel}>VO₂max</Text>
            </View>
          )}
          {profile.resting_heart_rate && (
            <View style={styles.statPill}>
              <Text style={styles.statValue}>{profile.resting_heart_rate}</Text>
              <Text style={styles.statLabel}>RHR</Text>
            </View>
          )}
          {profile.weekly_running_km != null && (
            <View style={styles.statPill}>
              <Text style={styles.statValue}>{Math.round(profile.weekly_running_km)}</Text>
              <Text style={styles.statLabel}>km/wk</Text>
            </View>
          )}
        </View>
      )}

      <View style={styles.section}>
        <TouchableOpacity
          style={styles.menuItem}
          onPress={() => navigation.navigate('GarminConnect')}
        >
          <Text style={styles.menuText}>⌚ Garmin Connection</Text>
          <View style={styles.menuRight}>
            {garminStatus?.connected && <View style={styles.connectedDot} />}
            <Text style={styles.chevron}>›</Text>
          </View>
        </TouchableOpacity>
        <TouchableOpacity style={styles.menuItem}>
          <Text style={styles.menuText}>👥 Friends</Text>
          <Text style={styles.chevron}>›</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.menuItem}>
          <Text style={styles.menuText}>🤖 AI Coach</Text>
          <Text style={styles.chevron}>›</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.section}>
        <View style={styles.healthHeader}>
          <Text style={styles.sectionTitle}>
            {Platform.OS === 'ios' ? '🍎 Apple Health' : '💚 Health Connect'}
          </Text>
        </View>
        <View style={styles.healthRow}>
          <Text style={styles.menuText}>Sync body composition</Text>
          <Switch
            value={healthEnabled}
            onValueChange={toggleHealth}
            trackColor={{ false: colors.textTertiary, true: colors.primary + '60' }}
            thumbColor={healthEnabled ? colors.primary : colors.textSecondary}
          />
        </View>
        {healthEnabled && (
          <>
            <TouchableOpacity
              style={styles.syncButton}
              onPress={handleHealthSync}
              disabled={healthSyncing}
            >
              {healthSyncing ? (
                <ActivityIndicator size="small" color={colors.primary} />
              ) : (
                <Text style={styles.syncText}>Sync Now</Text>
              )}
            </TouchableOpacity>
            {lastSync && <Text style={styles.lastSyncText}>Last sync: {lastSync}</Text>}
          </>
        )}
        <Text style={styles.healthDesc}>Weight, BMI, body fat %, lean body mass</Text>
      </View>

      <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
        <Text style={styles.logoutText}>Log Out</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  header: { alignItems: 'center', padding: spacing.xl, paddingTop: spacing.xl + 20 },
  avatar: {
    width: 72, height: 72, borderRadius: 36, backgroundColor: colors.primary + '25',
    justifyContent: 'center', alignItems: 'center', marginBottom: spacing.md,
  },
  avatarText: { color: colors.primary, fontSize: fontSize.xl, fontWeight: '700' },
  name: { fontSize: fontSize.xl, fontWeight: '700', color: colors.text },
  email: { fontSize: fontSize.sm, color: colors.textSecondary, marginTop: spacing.xs },
  statsRow: {
    flexDirection: 'row', justifyContent: 'center', gap: spacing.md,
    paddingHorizontal: spacing.lg, marginBottom: spacing.lg,
  },
  statPill: {
    backgroundColor: colors.card, borderRadius: 12, paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg, alignItems: 'center', minWidth: 80,
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  statValue: { fontSize: fontSize.lg, fontWeight: '700', color: colors.text },
  statLabel: { fontSize: fontSize.xs, color: colors.textSecondary, marginTop: 2 },
  section: {
    backgroundColor: colors.card, borderRadius: 12, marginHorizontal: spacing.md,
    marginBottom: spacing.lg, overflow: 'hidden', borderWidth: 1, borderColor: colors.borderSubtle,
  },
  menuItem: {
    padding: spacing.md, borderBottomWidth: 1, borderBottomColor: colors.borderSubtle,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
  },
  menuRight: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  connectedDot: {
    width: 8, height: 8, borderRadius: 4, backgroundColor: colors.primary,
  },
  menuText: { fontSize: fontSize.md, color: colors.text },
  chevron: { fontSize: 20, color: colors.textTertiary },
  logoutButton: {
    marginHorizontal: spacing.md, marginBottom: spacing.xl, padding: spacing.md,
    backgroundColor: colors.card, borderRadius: 12, alignItems: 'center',
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  logoutText: { fontSize: fontSize.md, color: colors.danger, fontWeight: '600' },
  healthHeader: {
    padding: spacing.md, borderBottomWidth: 1, borderBottomColor: colors.borderSubtle,
  },
  sectionTitle: { fontSize: fontSize.md, fontWeight: '600', color: colors.text },
  healthRow: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    padding: spacing.md, borderBottomWidth: 1, borderBottomColor: colors.borderSubtle,
  },
  syncButton: {
    margin: spacing.md, marginTop: spacing.sm, padding: spacing.sm,
    backgroundColor: colors.primary + '15', borderRadius: 8, alignItems: 'center',
  },
  syncText: { color: colors.primary, fontWeight: '600', fontSize: fontSize.sm },
  lastSyncText: {
    color: colors.textSecondary, fontSize: fontSize.xs, textAlign: 'center', marginBottom: spacing.sm,
  },
  healthDesc: {
    color: colors.textSecondary, fontSize: fontSize.xs, padding: spacing.md, paddingTop: spacing.xs,
  },
});
