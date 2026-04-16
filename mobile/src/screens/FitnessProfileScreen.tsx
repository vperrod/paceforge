import React from 'react';
import {
  View, Text, StyleSheet, ScrollView, RefreshControl, ActivityIndicator,
} from 'react-native';
import { colors, spacing, fontSize } from '../theme';
import api from '../api/client';

function fmtPace(secPerKm: number | null | undefined): string {
  if (!secPerKm || secPerKm <= 0) return '—';
  const m = Math.floor(secPerKm / 60);
  const s = Math.round(secPerKm % 60);
  return `${m}:${s.toString().padStart(2, '0')}/km`;
}

function fmtTime(seconds: number | null | undefined): string {
  if (!seconds) return '—';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.round(seconds % 60);
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

const ZONE_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#F97316', '#EF4444'];
const ZONE_LABELS = ['Z1 Easy', 'Z2 Aerobic', 'Z3 Tempo', 'Z4 Threshold', 'Z5 Max'];

const LEVEL_COLORS: Record<string, string> = {
  beginner: colors.sky,
  intermediate: colors.amber,
  advanced: colors.primary,
  elite: colors.violet,
};

export default function FitnessProfileScreen() {
  const [profile, setProfile] = React.useState<any>(null);
  const [analytics, setAnalytics] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(true);
  const [refreshing, setRefreshing] = React.useState(false);

  const loadData = async () => {
    try {
      const [profileRes, analyticsRes] = await Promise.all([
        api.get('/profile'),
        api.get('/profile/analytics').catch(() => ({ data: null })),
      ]);
      setProfile(profileRes.data);
      setAnalytics(analyticsRes.data);
    } catch {} finally {
      setLoading(false);
    }
  };

  React.useEffect(() => { loadData(); }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  if (!profile) {
    return (
      <View style={styles.center}>
        <Text style={styles.emptyIcon}>📊</Text>
        <Text style={styles.emptyText}>No Fitness Data</Text>
        <Text style={styles.emptyHint}>Connect your Garmin and sync activities to see your profile</Text>
      </View>
    );
  }

  const snap = analytics?.snapshot;
  const aero = analytics?.aerobic;
  const predictions = analytics?.race_predictions;
  const level = snap?.fitness_level || '';
  const levelColor = LEVEL_COLORS[level.toLowerCase()] || colors.textSecondary;

  const hrZones = profile.hr_zones || [];

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}
    >
      {/* Athlete Level + VDOT */}
      <View style={styles.levelCard}>
        <View style={styles.levelRow}>
          {level ? (
            <View style={[styles.levelBadge, { backgroundColor: levelColor + '20', borderColor: levelColor + '40' }]}>
              <Text style={[styles.levelText, { color: levelColor }]}>{level}</Text>
            </View>
          ) : null}
          {snap?.vdot ? (
            <View style={styles.vdotBox}>
              <Text style={styles.vdotValue}>{snap.vdot.toFixed(1)}</Text>
              <Text style={styles.vdotLabel}>VDOT</Text>
            </View>
          ) : null}
        </View>
        {snap?.training_status && (
          <Text style={styles.trainingStatus}>
            Training Status: {snap.training_status.replace(/_/g, ' ')}
          </Text>
        )}
      </View>

      {/* Key Metrics Grid */}
      <View style={styles.kpiGrid}>
        {profile.vo2_max && <KPI label="VO₂max" value={Math.round(profile.vo2_max).toString()} color={colors.primary} />}
        {profile.resting_heart_rate && <KPI label="RHR" value={profile.resting_heart_rate.toString()} unit="bpm" />}
        {profile.max_hr && <KPI label="Max HR" value={profile.max_hr.toString()} unit="bpm" color={colors.danger} />}
        {profile.weekly_running_km != null && <KPI label="Weekly" value={Math.round(profile.weekly_running_km).toString()} unit="km" />}
        {profile.endurance_score && <KPI label="Endurance" value={profile.endurance_score.toString()} color={colors.sky} />}
        {profile.fitness_age && <KPI label="Fitness Age" value={profile.fitness_age.toString()} />}
        {profile.lactate_threshold_hr && <KPI label="LT HR" value={profile.lactate_threshold_hr.toString()} unit="bpm" color={colors.amber} />}
        {profile.lactate_threshold_speed && <KPI label="LT Pace" value={fmtPace(1000 / profile.lactate_threshold_speed)} color={colors.amber} />}
      </View>

      {/* Aerobic Engine */}
      {aero && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Aerobic Engine</Text>
          {aero.vo2max_category && (
            <Text style={styles.infoText}>
              VO₂max Category: <Text style={{ color: colors.primary, fontWeight: '600' }}>{aero.vo2max_category}</Text>
            </Text>
          )}
          {aero.aerobic_ratio != null && (
            <View style={styles.ratioRow}>
              <View style={[styles.ratioBar, { flex: aero.aerobic_ratio, backgroundColor: colors.primary }]} />
              <View style={[styles.ratioBar, { flex: 100 - aero.aerobic_ratio, backgroundColor: colors.danger }]} />
            </View>
          )}
          {aero.aerobic_ratio != null && (
            <View style={styles.ratioLabels}>
              <Text style={styles.ratioLabel}>Aerobic {aero.aerobic_ratio}%</Text>
              <Text style={styles.ratioLabel}>Anaerobic {100 - aero.aerobic_ratio}%</Text>
            </View>
          )}
          {aero.threshold_pct_of_vo2max && (
            <Text style={styles.infoText}>
              Threshold at {aero.threshold_pct_of_vo2max.toFixed(0)}% of VO₂max
            </Text>
          )}
        </View>
      )}

      {/* HR Zones */}
      {hrZones.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Heart Rate Zones</Text>
          {hrZones.slice(0, 5).map((zone: any, i: number) => (
            <View key={i} style={styles.zoneRow}>
              <Text style={[styles.zoneLabel, { color: ZONE_COLORS[i] }]}>{ZONE_LABELS[i]}</Text>
              <View style={styles.zoneBarBg}>
                <View style={[styles.zoneBarFill, {
                  width: '100%', backgroundColor: ZONE_COLORS[i] + '30',
                }]} />
              </View>
              <Text style={styles.zoneBpm}>
                {zone.low_bpm || zone.zoneLowBoundary}–{zone.high_bpm || zone.zoneHighBoundary}
              </Text>
            </View>
          ))}
        </View>
      )}

      {/* Race Predictions */}
      {predictions && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Race Predictions</Text>
          <View style={styles.predictGrid}>
            {predictions['5K'] && <PredictionCard race="5K" time={predictions['5K']} />}
            {predictions['10K'] && <PredictionCard race="10K" time={predictions['10K']} />}
            {predictions['Half Marathon'] && <PredictionCard race="Half" time={predictions['Half Marathon']} />}
            {predictions['Marathon'] && <PredictionCard race="Marathon" time={predictions['Marathon']} />}
          </View>
        </View>
      )}

      {/* Strengths & Weaknesses */}
      {snap?.strengths?.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Strengths</Text>
          {snap.strengths.map((s: string, i: number) => (
            <Text key={i} style={styles.bulletItem}>✓ {s}</Text>
          ))}
        </View>
      )}
      {snap?.weaknesses?.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Areas to Improve</Text>
          {snap.weaknesses.map((w: string, i: number) => (
            <Text key={i} style={styles.bulletItem}>△ {w}</Text>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

function KPI({ label, value, unit, color }: { label: string; value: string; unit?: string; color?: string }) {
  return (
    <View style={styles.kpiBox}>
      <Text style={[styles.kpiValue, color ? { color } : null]}>
        {value}
        {unit ? <Text style={styles.kpiUnit}> {unit}</Text> : null}
      </Text>
      <Text style={styles.kpiLabel}>{label}</Text>
    </View>
  );
}

function PredictionCard({ race, time }: { race: string; time: number }) {
  return (
    <View style={styles.predCard}>
      <Text style={styles.predRace}>{race}</Text>
      <Text style={styles.predTime}>{fmtTime(time)}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.md, paddingBottom: spacing.xl * 2 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: colors.background },
  emptyIcon: { fontSize: 48, marginBottom: spacing.md },
  emptyText: { fontSize: fontSize.lg, fontWeight: '600', color: colors.text },
  emptyHint: { fontSize: fontSize.sm, color: colors.textSecondary, textAlign: 'center', marginTop: spacing.sm, paddingHorizontal: spacing.xl },

  levelCard: {
    backgroundColor: colors.card, borderRadius: 12, padding: spacing.md, marginBottom: spacing.md,
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  levelRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  levelBadge: {
    borderRadius: 8, paddingHorizontal: 14, paddingVertical: 6,
    borderWidth: 1,
  },
  levelText: { fontSize: fontSize.md, fontWeight: '700', textTransform: 'capitalize' },
  vdotBox: { alignItems: 'center' },
  vdotValue: { fontSize: fontSize.xl, fontWeight: '700', color: colors.primary },
  vdotLabel: { fontSize: fontSize.xs, color: colors.textSecondary, marginTop: 2 },
  trainingStatus: {
    fontSize: fontSize.sm, color: colors.textSecondary, marginTop: spacing.sm, textTransform: 'capitalize',
  },

  kpiGrid: {
    flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, marginBottom: spacing.md,
  },
  kpiBox: {
    backgroundColor: colors.card, borderRadius: 12, padding: spacing.md,
    alignItems: 'center', minWidth: 80, flex: 1,
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  kpiValue: { fontSize: fontSize.lg, fontWeight: '700', color: colors.text },
  kpiUnit: { fontSize: fontSize.xs, color: colors.textTertiary, fontWeight: '400' },
  kpiLabel: { fontSize: fontSize.xs, color: colors.textSecondary, marginTop: 2 },

  section: {
    backgroundColor: colors.card, borderRadius: 12, padding: spacing.md, marginBottom: spacing.md,
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  sectionTitle: {
    fontSize: fontSize.sm, fontWeight: '700', color: colors.text,
    textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: spacing.sm,
  },
  infoText: { fontSize: fontSize.sm, color: colors.textSecondary, marginBottom: spacing.sm },

  ratioRow: { flexDirection: 'row', height: 10, borderRadius: 5, overflow: 'hidden', marginBottom: spacing.xs },
  ratioBar: { height: 10 },
  ratioLabels: { flexDirection: 'row', justifyContent: 'space-between' },
  ratioLabel: { fontSize: fontSize.xs, color: colors.textSecondary },

  zoneRow: { flexDirection: 'row', alignItems: 'center', marginBottom: spacing.sm },
  zoneLabel: { width: 85, fontSize: fontSize.xs, fontWeight: '600' },
  zoneBarBg: { flex: 1, height: 8, borderRadius: 4, backgroundColor: colors.elevated, marginHorizontal: spacing.sm, overflow: 'hidden' },
  zoneBarFill: { height: 8, borderRadius: 4 },
  zoneBpm: { width: 70, fontSize: fontSize.xs, color: colors.textSecondary, textAlign: 'right' },

  predictGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  predCard: {
    flex: 1, minWidth: 70, backgroundColor: colors.elevated, borderRadius: 10,
    padding: spacing.sm, alignItems: 'center',
  },
  predRace: { fontSize: fontSize.xs, color: colors.textSecondary, fontWeight: '600' },
  predTime: { fontSize: fontSize.md, fontWeight: '700', color: colors.text, marginTop: 2 },

  bulletItem: { fontSize: fontSize.sm, color: colors.text, marginBottom: spacing.xs, lineHeight: 20 },
});
