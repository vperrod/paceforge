import React from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { colors, spacing, fontSize } from '../theme';

type Props = NativeStackScreenProps<any, 'WorkoutDetail'>;

function formatPace(secPerKm: number | null | undefined): string {
  if (!secPerKm || secPerKm <= 0) return '—';
  const m = Math.floor(secPerKm / 60);
  const s = Math.round(secPerKm % 60);
  return `${m}:${s.toString().padStart(2, '0')}/km`;
}

function formatDuration(seconds: number | null | undefined): string {
  if (!seconds) return '—';
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m > 0 ? `${m}:${s.toString().padStart(2, '0')}` : `${s}s`;
}

function formatDistance(meters: number | null | undefined): string {
  if (!meters) return '';
  return meters >= 1000 ? `${(meters / 1000).toFixed(1)} km` : `${Math.round(meters)} m`;
}

const typeColors: Record<string, string> = {
  EASY_RUN: colors.primary,
  LONG_RUN: colors.sky,
  TEMPO: colors.amber,
  INTERVALS: colors.danger,
  RECOVERY: '#8B95AD',
  REST: '#5C6478',
};

export default function WorkoutDetailScreen({ route }: Props) {
  const workout = route.params?.workout;
  if (!workout) return null;

  const typeColor = typeColors[workout.workout_type] || colors.sky;

  const renderStep = (step: any, index: number, depth = 0) => {
    const isRepeat = step.step_type === 'repeat' && step.steps?.length;
    const indent = depth * 16;

    if (isRepeat) {
      return (
        <View key={index} style={[styles.repeatBlock, { marginLeft: indent }]}>
          <Text style={styles.repeatLabel}>× {step.repeat_count || 1}</Text>
          {step.steps.map((sub: any, i: number) => renderStep(sub, i, depth + 1))}
        </View>
      );
    }

    const target =
      step.target_type === 'pace' && step.target_low
        ? `${formatPace(step.target_low)}${step.target_high ? ` – ${formatPace(step.target_high)}` : ''}`
        : step.target_type === 'heart_rate' && step.target_low
          ? `${step.target_low}${step.target_high ? `–${step.target_high}` : ''} bpm`
          : null;

    const duration = step.duration_seconds
      ? formatDuration(step.duration_seconds)
      : step.distance_meters
        ? formatDistance(step.distance_meters)
        : null;

    const stepColor =
      step.step_type === 'warmup' || step.step_type === 'cooldown'
        ? colors.textSecondary
        : step.step_type === 'recovery' || step.step_type === 'rest'
          ? colors.textTertiary
          : colors.text;

    return (
      <View key={index} style={[styles.stepRow, { marginLeft: indent }]}>
        <View style={[styles.stepDot, { backgroundColor: stepColor }]} />
        <View style={styles.stepContent}>
          <Text style={[styles.stepDesc, { color: stepColor }]}>{step.description}</Text>
          <View style={styles.stepMeta}>
            {duration && <Text style={styles.stepChip}>{duration}</Text>}
            {target && <Text style={[styles.stepChip, styles.stepPace]}>{target}</Text>}
          </View>
        </View>
      </View>
    );
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <View style={[styles.typeBadge, { backgroundColor: typeColor + '20' }]}>
          <Text style={[styles.typeText, { color: typeColor }]}>
            {workout.workout_type?.replace(/_/g, ' ')}
          </Text>
        </View>
        <Text style={styles.name}>{workout.name}</Text>
        {workout.scheduled_date && (
          <Text style={styles.date}>{workout.scheduled_date}</Text>
        )}
      </View>

      {workout.completed && (
        <View style={styles.completedBanner}>
          <Text style={styles.completedText}>✓ Completed</Text>
          {workout.user_rpe && (
            <Text style={styles.rpeText}>RPE: {workout.user_rpe}/10</Text>
          )}
        </View>
      )}

      {workout.purpose && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Purpose</Text>
          <Text style={styles.sectionText}>{workout.purpose.replace(/_/g, ' ')}</Text>
        </View>
      )}

      {workout.description && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Description</Text>
          <Text style={styles.sectionText}>{workout.description}</Text>
        </View>
      )}

      {/* Duration & Distance summary */}
      <View style={styles.metricsRow}>
        {workout.estimated_duration_seconds && (
          <View style={styles.metricBox}>
            <Text style={styles.metricValue}>
              {formatDuration(workout.estimated_duration_seconds)}
            </Text>
            <Text style={styles.metricLabel}>Duration</Text>
          </View>
        )}
        {workout.estimated_distance_meters && (
          <View style={styles.metricBox}>
            <Text style={styles.metricValue}>
              {formatDistance(workout.estimated_distance_meters)}
            </Text>
            <Text style={styles.metricLabel}>Distance</Text>
          </View>
        )}
        {workout.cadence_target && (
          <View style={styles.metricBox}>
            <Text style={styles.metricValue}>{workout.cadence_target}</Text>
            <Text style={styles.metricLabel}>Cadence</Text>
          </View>
        )}
      </View>

      {/* Workout Steps */}
      {workout.steps?.length > 0 && (
        <View style={styles.stepsSection}>
          <Text style={styles.sectionLabel}>Workout Structure</Text>
          {workout.steps.map((step: any, i: number) => renderStep(step, i))}
        </View>
      )}

      {/* Completion analysis */}
      {workout.completion_analysis && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>AI Analysis</Text>
          <Text style={styles.sectionText}>{workout.completion_analysis}</Text>
        </View>
      )}

      {/* User notes */}
      {workout.user_notes && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Your Notes</Text>
          <Text style={styles.sectionText}>{workout.user_notes}</Text>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.md, paddingBottom: spacing.xl },
  header: { marginBottom: spacing.lg },
  typeBadge: {
    alignSelf: 'flex-start', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 4,
    marginBottom: spacing.sm,
  },
  typeText: { fontSize: fontSize.xs, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 },
  name: { fontSize: fontSize.xl, fontWeight: '700', color: colors.text },
  date: { fontSize: fontSize.sm, color: colors.textSecondary, marginTop: spacing.xs },
  completedBanner: {
    backgroundColor: colors.primary + '15', borderRadius: 12, padding: spacing.md,
    marginBottom: spacing.lg, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    borderWidth: 1, borderColor: colors.primary + '30',
  },
  completedText: { color: colors.primary, fontWeight: '700', fontSize: fontSize.md },
  rpeText: { color: colors.textSecondary, fontSize: fontSize.sm },
  section: {
    backgroundColor: colors.card, borderRadius: 12, padding: spacing.md, marginBottom: spacing.md,
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  sectionLabel: {
    fontSize: fontSize.xs, fontWeight: '600', color: colors.textSecondary,
    textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: spacing.sm,
  },
  sectionText: { fontSize: fontSize.sm, color: colors.text, lineHeight: 22 },
  metricsRow: {
    flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.lg,
  },
  metricBox: {
    flex: 1, backgroundColor: colors.card, borderRadius: 12, padding: spacing.md,
    alignItems: 'center', borderWidth: 1, borderColor: colors.borderSubtle,
  },
  metricValue: { fontSize: fontSize.lg, fontWeight: '700', color: colors.text },
  metricLabel: { fontSize: fontSize.xs, color: colors.textSecondary, marginTop: 2 },
  stepsSection: {
    backgroundColor: colors.card, borderRadius: 12, padding: spacing.md, marginBottom: spacing.md,
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  stepRow: {
    flexDirection: 'row', alignItems: 'flex-start', paddingVertical: spacing.sm,
  },
  stepDot: {
    width: 8, height: 8, borderRadius: 4, marginTop: 6, marginRight: spacing.sm,
  },
  stepContent: { flex: 1 },
  stepDesc: { fontSize: fontSize.sm, lineHeight: 20 },
  stepMeta: { flexDirection: 'row', gap: spacing.sm, marginTop: 4 },
  stepChip: {
    fontSize: fontSize.xs, color: colors.textSecondary,
    backgroundColor: colors.elevated, borderRadius: 4, paddingHorizontal: 6, paddingVertical: 2,
  },
  stepPace: { color: colors.sky },
  repeatBlock: {
    borderLeftWidth: 2, borderLeftColor: colors.amber + '40',
    paddingLeft: spacing.sm, marginVertical: spacing.xs,
  },
  repeatLabel: {
    fontSize: fontSize.xs, fontWeight: '700', color: colors.amber, marginBottom: spacing.xs,
  },
});
