import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Calendar, DateData } from 'react-native-calendars';
import { useNavigation } from '@react-navigation/native';
import { colors, spacing, fontSize } from '../theme';
import api from '../api/client';

export default function CalendarScreen() {
  const [markedDates, setMarkedDates] = React.useState<Record<string, any>>({});
  const [selectedWorkout, setSelectedWorkout] = React.useState<any>(null);
  const navigation = useNavigation<any>();

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
              dotColor: wo.completed ? colors.primary : colors.sky,
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
          calendarBackground: colors.card,
          textSectionTitleColor: colors.textSecondary,
          todayTextColor: colors.primary,
          dayTextColor: colors.text,
          textDisabledColor: colors.textTertiary,
          monthTextColor: colors.text,
          arrowColor: colors.primary,
        }}
        style={styles.calendar}
      />
      {selectedWorkout ? (
        <TouchableOpacity
          style={styles.detail}
          onPress={() => navigation.navigate('WorkoutDetail', { workout: selectedWorkout })}
          activeOpacity={0.7}
        >
          <View style={styles.detailHeader}>
            <View>
              <Text style={styles.detailTitle}>{selectedWorkout.name}</Text>
              <Text style={styles.detailType}>
                {selectedWorkout.workout_type?.replace(/_/g, ' ')}
              </Text>
            </View>
            {selectedWorkout.completed && (
              <View style={styles.completedBadge}>
                <Text style={styles.completedText}>Done</Text>
              </View>
            )}
          </View>
          {selectedWorkout.purpose ? (
            <Text style={styles.detailPurpose}>{selectedWorkout.purpose}</Text>
          ) : null}
          <Text style={styles.tapHint}>Tap for full details ›</Text>
        </TouchableOpacity>
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
  calendar: {
    borderRadius: 12, margin: spacing.md, overflow: 'hidden',
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  detail: {
    backgroundColor: colors.card, borderRadius: 12, margin: spacing.md, padding: spacing.lg,
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  detailHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  detailTitle: { fontSize: fontSize.lg, fontWeight: '700', color: colors.text },
  detailType: {
    fontSize: fontSize.sm, color: colors.sky, marginTop: spacing.xs, textTransform: 'capitalize',
  },
  detailPurpose: { fontSize: fontSize.sm, color: colors.textSecondary, marginTop: spacing.sm },
  completedBadge: {
    backgroundColor: colors.primary + '20', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 4,
  },
  completedText: { color: colors.primary, fontWeight: '600', fontSize: fontSize.xs },
  tapHint: {
    fontSize: fontSize.xs, color: colors.textTertiary, marginTop: spacing.md, textAlign: 'right',
  },
  placeholder: { alignItems: 'center', padding: spacing.xl },
  placeholderText: { fontSize: fontSize.sm, color: colors.textSecondary },
});
