import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert } from 'react-native';
import { colors, spacing, fontSize } from '../theme';
import { useAuthStore } from '../store/auth';
import api from '../api/client';

export default function ProfileScreen() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const [profile, setProfile] = React.useState<any>(null);

  React.useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const { data } = await api.get('/profile');
      setProfile(data);
    } catch {}
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
        <TouchableOpacity style={styles.menuItem}>
          <Text style={styles.menuText}>⌚ Garmin Connection</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.menuItem}>
          <Text style={styles.menuText}>👥 Friends</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.menuItem}>
          <Text style={styles.menuText}>🤖 AI Coach</Text>
        </TouchableOpacity>
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
    width: 72, height: 72, borderRadius: 36, backgroundColor: colors.primary,
    justifyContent: 'center', alignItems: 'center', marginBottom: spacing.md,
  },
  avatarText: { color: '#fff', fontSize: fontSize.xl, fontWeight: '700' },
  name: { fontSize: fontSize.xl, fontWeight: '700', color: colors.text },
  email: { fontSize: fontSize.sm, color: colors.textSecondary, marginTop: spacing.xs },
  statsRow: {
    flexDirection: 'row', justifyContent: 'center', gap: spacing.md,
    paddingHorizontal: spacing.lg, marginBottom: spacing.lg,
  },
  statPill: {
    backgroundColor: colors.surface, borderRadius: 12, paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg, alignItems: 'center', minWidth: 80,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 4, elevation: 1,
  },
  statValue: { fontSize: fontSize.lg, fontWeight: '700', color: colors.text },
  statLabel: { fontSize: fontSize.xs, color: colors.textSecondary, marginTop: 2 },
  section: {
    backgroundColor: colors.surface, borderRadius: 12, marginHorizontal: spacing.md, marginBottom: spacing.lg,
    overflow: 'hidden',
  },
  menuItem: {
    padding: spacing.md, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border,
  },
  menuText: { fontSize: fontSize.md, color: colors.text },
  logoutButton: {
    marginHorizontal: spacing.md, marginBottom: spacing.xl, padding: spacing.md,
    backgroundColor: colors.surface, borderRadius: 12, alignItems: 'center',
  },
  logoutText: { fontSize: fontSize.md, color: colors.danger, fontWeight: '600' },
});
