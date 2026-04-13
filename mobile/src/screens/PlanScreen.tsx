import React from 'react';
import { View, Text, StyleSheet, ScrollView, RefreshControl, TouchableOpacity } from 'react-native';
import { colors, spacing, fontSize } from '../theme';
import api from '../api/client';

export default function PlanScreen() {
  const [plans, setPlans] = React.useState<any[]>([]);
  const [refreshing, setRefreshing] = React.useState(false);

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

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={!activePlan ? styles.empty : undefined}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      {activePlan ? (
        <View style={styles.content}>
          <View style={styles.planHeader}>
            <Text style={styles.planGoal}>{activePlan.goal?.goal_type || 'Training Plan'}</Text>
            {activePlan.goal?.target_date && (
              <Text style={styles.planDate}>Target: {activePlan.goal.target_date}</Text>
            )}
          </View>
          {activePlan.weeks?.map((week: any, i: number) => (
            <View key={i} style={styles.weekCard}>
              <Text style={styles.weekTitle}>Week {week.week_number}</Text>
              {week.workouts?.map((wo: any, j: number) => (
                <View key={j} style={styles.workoutRow}>
                  <View style={[styles.dot, wo.completed ? styles.dotDone : styles.dotPending]} />
                  <View style={styles.workoutInfo}>
                    <Text style={styles.workoutName}>{wo.name}</Text>
                    <Text style={styles.workoutMeta}>
                      {wo.scheduled_date} · {wo.workout_type}
                    </Text>
                  </View>
                </View>
              ))}
            </View>
          ))}
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

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.md },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  emptyView: { alignItems: 'center', padding: spacing.xl },
  emptyIcon: { fontSize: 48, marginBottom: spacing.md },
  emptyText: { fontSize: fontSize.lg, fontWeight: '600', color: colors.text },
  emptyHint: { fontSize: fontSize.sm, color: colors.textSecondary, textAlign: 'center', marginTop: spacing.sm },
  planHeader: { padding: spacing.md, marginBottom: spacing.sm },
  planGoal: { fontSize: fontSize.xl, fontWeight: '700', color: colors.text, textTransform: 'capitalize' },
  planDate: { fontSize: fontSize.sm, color: colors.textSecondary, marginTop: spacing.xs },
  weekCard: {
    backgroundColor: colors.surface, borderRadius: 12, padding: spacing.md, marginBottom: spacing.md,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 4, elevation: 1,
  },
  weekTitle: { fontSize: fontSize.md, fontWeight: '600', color: colors.text, marginBottom: spacing.sm },
  workoutRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: spacing.sm },
  dot: { width: 10, height: 10, borderRadius: 5, marginRight: spacing.sm },
  dotDone: { backgroundColor: colors.secondary },
  dotPending: { backgroundColor: colors.border },
  workoutInfo: { flex: 1 },
  workoutName: { fontSize: fontSize.sm, fontWeight: '500', color: colors.text },
  workoutMeta: { fontSize: fontSize.xs, color: colors.textSecondary, marginTop: 2 },
});
