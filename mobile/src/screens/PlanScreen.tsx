import React from 'react';
import { View, Text, StyleSheet, ScrollView, RefreshControl, TouchableOpacity } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { colors, spacing, fontSize } from '../theme';
import api from '../api/client';

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
          <View style={styles.planHeader}>
            <Text style={styles.planGoal}>{activePlan.goal?.goal_type || 'Training Plan'}</Text>
            {activePlan.goal?.target_date && (
              <Text style={styles.planDate}>Target: {activePlan.goal.target_date}</Text>
            )}
          </View>
          {activePlan.weeks?.map((week: any, i: number) => (
            <View key={i} style={styles.weekCard}>
              <View style={styles.weekHeader}>
                <Text style={styles.weekTitle}>Week {week.week_number}</Text>
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
                    </Text>
                  </View>
                  <Text style={styles.chevron}>›</Text>
                </TouchableOpacity>
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
  emptyHint: {
    fontSize: fontSize.sm, color: colors.textSecondary, textAlign: 'center', marginTop: spacing.sm,
  },
  planHeader: { padding: spacing.md, marginBottom: spacing.sm },
  planGoal: {
    fontSize: fontSize.xl, fontWeight: '700', color: colors.text, textTransform: 'capitalize',
  },
  planDate: { fontSize: fontSize.sm, color: colors.textSecondary, marginTop: spacing.xs },
  weekCard: {
    backgroundColor: colors.card, borderRadius: 12, padding: spacing.md, marginBottom: spacing.md,
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  weekHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    marginBottom: spacing.sm,
  },
  weekTitle: { fontSize: fontSize.md, fontWeight: '600', color: colors.text },
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
