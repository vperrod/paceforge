import React from 'react';
import { View, Text, StyleSheet, ScrollView, ActivityIndicator } from 'react-native';
import { colors, spacing, fontSize } from '../theme';
import { useAuthStore } from '../store/auth';
import api from '../api/client';

export default function MetricsBanner() {
  const user = useAuthStore((s) => s.user);
  const [profile, setProfile] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const { data } = await api.get('/profile');
      setProfile(data);
    } catch {} finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="small" color={colors.primary} />
      </View>
    );
  }

  if (!profile && !user) return null;

  const metrics: { label: string; value: string; unit?: string; color?: string }[] = [];

  if (profile?.vo2_max) {
    metrics.push({ label: 'VO₂max', value: Math.round(profile.vo2_max).toString(), color: colors.primary });
  }
  if (profile?.resting_heart_rate) {
    metrics.push({ label: 'RHR', value: profile.resting_heart_rate.toString(), unit: 'bpm' });
  }
  if (profile?.weekly_running_km != null) {
    metrics.push({ label: 'Weekly', value: Math.round(profile.weekly_running_km).toString(), unit: 'km' });
  }
  if (profile?.training_status) {
    metrics.push({ label: 'Status', value: profile.training_status.replace(/_/g, ' '), color: colors.sky });
  }
  if (profile?.fitness_age) {
    metrics.push({ label: 'Fitness Age', value: profile.fitness_age.toString() });
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>
            {user?.name?.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2) || '?'}
          </Text>
        </View>
        <View>
          <Text style={styles.greeting}>Welcome back,</Text>
          <Text style={styles.name}>{user?.name || 'Runner'}</Text>
        </View>
      </View>
      {metrics.length > 0 && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.metricsRow}>
          {metrics.map((m, i) => (
            <View key={i} style={styles.metricPill}>
              <Text style={[styles.metricValue, m.color ? { color: m.color } : null]}>
                {m.value}
                {m.unit ? <Text style={styles.metricUnit}> {m.unit}</Text> : null}
              </Text>
              <Text style={styles.metricLabel}>{m.label}</Text>
            </View>
          ))}
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.card, borderRadius: 12, margin: spacing.md, marginBottom: 0,
    padding: spacing.md, borderWidth: 1, borderColor: colors.borderSubtle,
  },
  header: {
    flexDirection: 'row', alignItems: 'center', gap: spacing.md, marginBottom: spacing.sm,
  },
  avatar: {
    width: 40, height: 40, borderRadius: 20, backgroundColor: colors.primary + '25',
    justifyContent: 'center', alignItems: 'center',
  },
  avatarText: { color: colors.primary, fontSize: fontSize.sm, fontWeight: '700' },
  greeting: { fontSize: fontSize.xs, color: colors.textSecondary },
  name: { fontSize: fontSize.md, fontWeight: '700', color: colors.text },
  metricsRow: { marginTop: spacing.xs },
  metricPill: {
    backgroundColor: colors.elevated, borderRadius: 10, paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md, alignItems: 'center', marginRight: spacing.sm,
    minWidth: 70,
  },
  metricValue: { fontSize: fontSize.md, fontWeight: '700', color: colors.text },
  metricUnit: { fontSize: fontSize.xs, color: colors.textTertiary, fontWeight: '400' },
  metricLabel: { fontSize: fontSize.xs, color: colors.textSecondary, marginTop: 2 },
});
