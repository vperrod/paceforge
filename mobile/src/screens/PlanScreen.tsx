import React from 'react';
import { View, Text, StyleSheet, ScrollView, RefreshControl, TouchableOpacity } from 'react-native';
import { useNavigation } from '@react-navigation/native';
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

export default function PlanScreen() {
  const [plans, setPlans] = React.useState<any[]>([]);
  const [refreshing, setRefreshing] = React.useState(false);
  const navigation = useNavigation<any>();

  const loadPlans = async () => {
    try {
      const { data } = await api.get('/plans');
      setPlans(data);
    } catch {}
  };

  React.useEffect(() => {
    loadPlans();
  }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadPlans();
    setRefreshing(false);
  };

  const activePlan = plans.find((p) => p.accepted);

  // Determine current week (by date)
  const todayStr = new Date().toISOString().slice(0, 10);
  let currentWeekNum: number | null = null;
  if (activePlan?.weeks) {
    for (const week of activePlan.weeks) {
      for (const wo of week.workouts || []) {
        if (wo.scheduled_date && wo.scheduled_date >= todayStr) {
          currentWeekNum = week.week_number;
          break;
        }
      }
      if (currentWeekNum != null) break;
    }
  }

  const totalWeeks = activePlan?.weeks?.length || 0;
  const completedWorkouts = activePlan?.weeks
    ?.flatMap((w: any) => w.workouts || [])
    .filter((wo: any) => wo.completed).length || 0;
  const totalWorkouts = activePlan?.weeks
    ?.flatMap((w: any) => w.workouts || []).length || 0;

  const paces = activePlan?.paces;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={!activePlan ? styles.empty : undefined}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />
      }
    >
      {activePlan ? (
        <View style={styles.content}>
          {/* Plan Header */}
          <View style={styles.planHeader}>
            <Text style={styles.planName}>{activePlan.name || 'Training Plan'}</Text>
            <Text style={styles.planGoal}>
              {(activePlan.goal?.goal_type || '').replace(/_/g, ' ')}
            </Text>
            <View style={styles.planMeta}>
              {activePlan.goal?.target_date && (
                <Text style={styles.planDate}>🎯 {activePlan.goal.target_date}</Text>
              )}
              {activePlan.goal?.target_time_seconds && (
                <Text style={styles.planDate}>
                  ⏱ Target: {fmtTime(activePlan.goal.target_time_seconds)}
                </Text>
              )}
            </View>
            {/* Progress */}
            <View style={styles.progressRow}>
              <View style={styles.progressBarBg}>
                <View style={[
                  styles.progressBarFill,
                  { width: `${totalWorkouts > 0 ? (completedWorkouts / totalWorkouts) * 100 : 0}%` },
                ]} />
              </View>
              <Text style={styles.progressText}>
                {completedWorkouts}/{totalWorkouts} workouts
              </Text>
            </View>
            {currentWeekNum != null && (
              <Text style={styles.weekIndicator}>
                📅 Week {currentWeekNum} of {totalWeeks}
              </Text>
            )}
          </View>

          {/* Training Paces */}
          {paces && (
            <View style={styles.pacesCard}>
              <Text style={styles.pacesTitle}>Training Paces</Text>
              <View style={styles.pacesGrid}>
                {paces.easy_pace && (
                  <PacePill label="Easy" value={fmtPace(paces.easy_pace)} color={colors.primary} />
                )}
                {paces.marathon_pace && (
                  <PacePill label="Marathon" value={fmtPace(paces.marathon_pace)} color={colors.sky} />
                )}
                {paces.threshold_pace && (
                  <PacePill label="Threshold" value={fmtPace(paces.threshold_pace)} color={colors.amber} />
                )}
                {paces.interval_pace && (
                  <PacePill label="Interval" value={fmtPace(paces.interval_pace)} color={colors.danger} />
                )}
                {paces.repetition_pace && (
                  <PacePill label="Repetition" value={fmtPace(paces.repetition_pace)} color={colors.violet} />
                )}
              </View>
            </View>
          )}

          {/* Weeks */}
          {activePlan.weeks?.map((week: any, i: number) => {
            const isCurrent = week.week_number === currentWeekNum;
            return (
              <View key={i} style={[styles.weekCard, isCurrent && styles.weekCardCurrent]}>
                <View style={styles.weekHeader}>
                  <View style={styles.weekTitleRow}>
                    <Text style={styles.weekTitle}>Week {week.week_number}</Text>
                    {isCurrent && <Text style={styles.currentBadge}>Current</Text>}
                  </View>
                  {week.phase && <Text style={styles.weekPhase}>{week.phase}</Text>}
                </View>
                {week.workouts?.map((wo: any, j: number) => (
                  <TouchableOpacity
                    key={j}
                    style={styles.workoutRow}
                    onPress={() => navigation.navigate('WorkoutDetail', { workout: wo })}
                  >
                    <View style={[styles.dot, wo.completed ? styles.dotDone : styles.dotPending]} />
                    <View style={styles.workoutInfo}>
                      <Text style={styles.workoutName}>{wo.name}</Text>
                      <Text style={styles.workoutMeta}>
                        {wo.scheduled_date} · {wo.workout_type?.replace(/_/g, ' ')}
                        {wo.estimated_distance_meters
                          ? ` · ${(wo.estimated_distance_meters / 1000).toFixed(1)} km`
                          : ''}
                      </Text>
                    </View>
                    <Text style={styles.chevron}>›</Text>
                  </TouchableOpacity>
                ))}
              </View>
            );
          })}
        </View>
      ) : (
        <View style={styles.emptyView}>
          <Text style={styles.emptyIcon}>📋</Text>
          <Text style={styles.emptyText}>No Training Plan</Text>
          <Text style={styles.emptyHint}>Generate a plan from the web app to get started</Text>
        </View>
      )}
    </ScrollView>
  );
}

function PacePill({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <View style={[paceStyles.pill, { borderColor: color + '30' }]}>
      <Text style={[paceStyles.value, { color }]}>{value}</Text>
      <Text style={paceStyles.label}>{label}</Text>
    </View>
  );
}

const paceStyles = StyleSheet.create({
  pill: {
    backgroundColor: colors.elevated, borderRadius: 10, paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md, alignItems: 'center', minWidth: 80,
    borderWidth: 1,
  },
  value: { fontSize: fontSize.sm, fontWeight: '700' },
  label: { fontSize: fontSize.xs, color: colors.textSecondary, marginTop: 2 },
});

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.md, paddingBottom: spacing.xl },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  emptyView: { alignItems: 'center', padding: spacing.xl },
  emptyIcon: { fontSize: 48, marginBottom: spacing.md },
  emptyText: { fontSize: fontSize.lg, fontWeight: '600', color: colors.text },
  emptyHint: {
    fontSize: fontSize.sm, color: colors.textSecondary, textAlign: 'center', marginTop: spacing.sm,
  },
  planHeader: {
    backgroundColor: colors.card, borderRadius: 12, padding: spacing.md, marginBottom: spacing.md,
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  planName: { fontSize: fontSize.xl, fontWeight: '700', color: colors.text },
  planGoal: {
    fontSize: fontSize.sm, color: colors.primary, fontWeight: '600',
    textTransform: 'capitalize', marginTop: spacing.xs,
  },
  planMeta: { marginTop: spacing.sm, gap: spacing.xs },
  planDate: { fontSize: fontSize.sm, color: colors.textSecondary },
  progressRow: {
    flexDirection: 'row', alignItems: 'center', marginTop: spacing.md, gap: spacing.sm,
  },
  progressBarBg: {
    flex: 1, height: 6, borderRadius: 3, backgroundColor: colors.elevated,
  },
  progressBarFill: {
    height: 6, borderRadius: 3, backgroundColor: colors.primary,
  },
  progressText: { fontSize: fontSize.xs, color: colors.textSecondary, minWidth: 90 },
  weekIndicator: {
    fontSize: fontSize.sm, color: colors.sky, marginTop: spacing.sm, fontWeight: '500',
  },

  pacesCard: {
    backgroundColor: colors.card, borderRadius: 12, padding: spacing.md, marginBottom: spacing.md,
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  pacesTitle: {
    fontSize: fontSize.sm, fontWeight: '700', color: colors.text,
    textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: spacing.sm,
  },
  pacesGrid: {
    flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm,
  },

  weekCard: {
    backgroundColor: colors.card, borderRadius: 12, padding: spacing.md, marginBottom: spacing.md,
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  weekCardCurrent: {
    borderColor: colors.primary + '40',
  },
  weekHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    marginBottom: spacing.sm,
  },
  weekTitleRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  weekTitle: { fontSize: fontSize.md, fontWeight: '600', color: colors.text },
  currentBadge: {
    fontSize: fontSize.xs, color: colors.primary, fontWeight: '600',
    backgroundColor: colors.primary + '15', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 6,
  },
  weekPhase: {
    fontSize: fontSize.xs, color: colors.sky, fontWeight: '500',
    backgroundColor: colors.sky + '15', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 6,
  },
  workoutRow: {
    flexDirection: 'row', alignItems: 'center', paddingVertical: spacing.sm,
    borderTopWidth: 1, borderTopColor: colors.borderSubtle,
  },
  dot: { width: 10, height: 10, borderRadius: 5, marginRight: spacing.sm },
  dotDone: { backgroundColor: colors.primary },
  dotPending: { backgroundColor: colors.textTertiary },
  workoutInfo: { flex: 1 },
  workoutName: { fontSize: fontSize.sm, fontWeight: '500', color: colors.text },
  workoutMeta: { fontSize: fontSize.xs, color: colors.textSecondary, marginTop: 2 },
  chevron: { fontSize: 20, color: colors.textTertiary, marginLeft: spacing.sm },
});
