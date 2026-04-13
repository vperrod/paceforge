import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Calendar, DateData } from 'react-native-calendars';
import { colors, spacing, fontSize } from '../theme';
import api from '../api/client';

export default function CalendarScreen() {
  const [markedDates, setMarkedDates] = React.useState<Record<string, any>>({});
  const [selectedWorkout, setSelectedWorkout] = React.useState<any>(null);

  React.useEffect(() => {
    loadPlanDates();
  }, []);

  const loadPlanDates = async () => {
    try {
      const { data } = await api.get('/plans');
      const active = data.find((p: any) => p.accepted);
      if (!active) return;
      const marks: Record<string, any> = {};
      for (const week of active.weeks || []) {
        for (const wo of week.workouts || []) {
          if (wo.scheduled_date) {
            marks[wo.scheduled_date] = {
              marked: true,
              dotColor: wo.completed ? colors.secondary : colors.primary,
              workout: wo,
            };
          }
        }
      }
      setMarkedDates(marks);
    } catch {}
  };

  const onDayPress = (day: DateData) => {
    const entry = markedDates[day.dateString];
    setSelectedWorkout(entry?.workout || null);
  };

  return (
    <View style={styles.container}>
      <Calendar
        onDayPress={onDayPress}
        markedDates={markedDates}
        theme={{
          backgroundColor: colors.background,
          calendarBackground: colors.surface,
          textSectionTitleColor: colors.textSecondary,
          todayTextColor: colors.primary,
          dayTextColor: colors.text,
          monthTextColor: colors.text,
          arrowColor: colors.primary,
        }}
        style={styles.calendar}
      />
      {selectedWorkout ? (
        <View style={styles.detail}>
          <Text style={styles.detailTitle}>{selectedWorkout.name}</Text>
          <Text style={styles.detailType}>{selectedWorkout.workout_type}</Text>
          {selectedWorkout.purpose ? (
            <Text style={styles.detailPurpose}>{selectedWorkout.purpose}</Text>
          ) : null}
          {selectedWorkout.completed && (
            <View style={styles.completedBadge}>
              <Text style={styles.completedText}>✅ Completed</Text>
            </View>
          )}
        </View>
      ) : (
        <View style={styles.placeholder}>
          <Text style={styles.placeholderText}>Tap a date to view workout details</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  calendar: { borderRadius: 12, margin: spacing.md, overflow: 'hidden' },
  detail: {
    backgroundColor: colors.surface, borderRadius: 12, margin: spacing.md, padding: spacing.lg,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 4, elevation: 1,
  },
  detailTitle: { fontSize: fontSize.lg, fontWeight: '700', color: colors.text },
  detailType: { fontSize: fontSize.sm, color: colors.primary, marginTop: spacing.xs, textTransform: 'capitalize' },
  detailPurpose: { fontSize: fontSize.sm, color: colors.textSecondary, marginTop: spacing.sm },
  completedBadge: {
    backgroundColor: '#E8F5E9', borderRadius: 8, padding: spacing.sm, marginTop: spacing.md, alignSelf: 'flex-start',
  },
  completedText: { color: '#2E7D32', fontWeight: '600', fontSize: fontSize.sm },
  placeholder: { alignItems: 'center', padding: spacing.xl },
  placeholderText: { fontSize: fontSize.sm, color: colors.textSecondary },
});
