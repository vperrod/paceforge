import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView } from 'react-native';
import { Calendar, DateData } from 'react-native-calendars';
import { useNavigation } from '@react-navigation/native';
import { colors, spacing, fontSize } from '../theme';
import api from '../api/client';

interface CalendarEntry {
  type: 'activity' | 'planned' | 'scheduled';
  title: string;
  subtitle?: string;
  color: string;
  data: any;
}

export default function CalendarScreen() {
  const [markedDates, setMarkedDates] = React.useState<Record<string, any>>({});
  const [entries, setEntries] = React.useState<Record<string, CalendarEntry[]>>({});
  const [selectedDate, setSelectedDate] = React.useState<string | null>(null);
  const navigation = useNavigation<any>();

  React.useEffect(() => {
    loadCalendarData();
  }, []);

  const loadCalendarData = async () => {
    const allEntries: Record<string, CalendarEntry[]> = {};

    const addEntry = (date: string, entry: CalendarEntry) => {
      if (!allEntries[date]) allEntries[date] = [];
      allEntries[date].push(entry);
    };

    // 1) Load past Garmin activities
    try {
      const { data: activities } = await api.get('/activities?days=240');
      const matchedIds = new Set<string>();

      // Collect matched activity IDs from plans to avoid duplicates
      try {
        const { data: plans } = await api.get('/plans');
        for (const plan of plans) {
          if (!plan.accepted) continue;
          for (const week of plan.weeks || []) {
            for (const wo of week.workouts || []) {
              if (wo.matched_activity_id) matchedIds.add(String(wo.matched_activity_id));
            }
          }
        }
      } catch {}

      for (const act of activities || []) {
        const dateStr = (act.startTimeLocal || '').slice(0, 10);
        if (!dateStr) continue;
        // Skip if already matched to a planned workout
        if (matchedIds.has(String(act.activityId))) continue;

        const distKm = act.distance ? (act.distance / 1000).toFixed(1) : null;
        const durationMin = act.duration ? Math.round(act.duration / 60) : null;
        const isRun = (act.activityType?.typeKey || '').toLowerCase().includes('running');
        const name = act.activityName || act.activityType?.typeKey || 'Activity';

        let subtitle = '';
        if (isRun && distKm) {
          const paceSeconds = act.duration && act.distance ? (act.duration / (act.distance / 1000)) : 0;
          const paceMin = Math.floor(paceSeconds / 60);
          const paceSec = Math.round(paceSeconds % 60);
          subtitle = `${distKm} km · ${paceMin}:${String(paceSec).padStart(2, '0')}/km`;
        } else if (distKm) {
          subtitle = `${distKm} km · ${durationMin} min`;
        } else if (durationMin) {
          subtitle = `${durationMin} min`;
        }

        addEntry(dateStr, {
          type: 'activity',
          title: `✓ ${name}`,
          subtitle,
          color: isRun ? colors.primary : colors.violet,
          data: act,
        });
      }
    } catch {}

    // 2) Load plan workouts
    try {
      const { data: plans } = await api.get('/plans');
      const active = plans.find((p: any) => p.accepted);
      if (active) {
        for (const week of active.weeks || []) {
          for (const wo of week.workouts || []) {
            if (!wo.scheduled_date) continue;
            const distKm = wo.estimated_distance_meters
              ? (wo.estimated_distance_meters / 1000).toFixed(1)
              : null;
            addEntry(wo.scheduled_date, {
              type: 'planned',
              title: `${wo.completed ? '✓' : '○'} ${wo.name}`,
              subtitle: [
                wo.workout_type?.replace(/_/g, ' '),
                distKm ? `${distKm} km` : null,
              ].filter(Boolean).join(' · '),
              color: wo.completed ? colors.primary : colors.sky,
              data: wo,
            });
          }
        }
      }
    } catch {}

    // 3) Load Garmin scheduled workouts
    try {
      const { data: scheduled } = await api.get('/garmin/scheduled-workouts');
      for (const sw of scheduled || []) {
        const dateStr = (sw.date || '').slice(0, 10);
        if (!dateStr) continue;
        addEntry(dateStr, {
          type: 'scheduled',
          title: `📅 ${sw.workoutName || 'Scheduled'}`,
          subtitle: sw.description?.slice(0, 80) || undefined,
          color: colors.sky,
          data: sw,
        });
      }
    } catch {}

    setEntries(allEntries);

    // Build marked dates from entries
    const marks: Record<string, any> = {};
    for (const [date, dateEntries] of Object.entries(allEntries)) {
      const hasActivity = dateEntries.some(e => e.type === 'activity');
      const hasPlanned = dateEntries.some(e => e.type === 'planned');
      const completed = dateEntries.some(e => e.type === 'activity' || e.data?.completed);
      marks[date] = {
        marked: true,
        dotColor: hasActivity ? colors.primary : hasPlanned ? colors.sky : colors.amber,
        selected: false,
      };
      if (completed && hasPlanned) {
        marks[date].dotColor = colors.primary;
      }
    }
    setMarkedDates(marks);
  };

  const onDayPress = (day: DateData) => {
    setSelectedDate(day.dateString);
    // Update selection styling
    const updated = { ...markedDates };
    for (const d of Object.keys(updated)) {
      updated[d] = { ...updated[d], selected: d === day.dateString };
    }
    setMarkedDates(updated);
  };

  const selectedEntries = selectedDate ? entries[selectedDate] || [] : [];

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
          selectedDayBackgroundColor: colors.primary,
          selectedDayTextColor: '#fff',
        }}
        style={styles.calendar}
      />
      {selectedEntries.length > 0 ? (
        <ScrollView style={styles.entryList}>
          {selectedEntries.map((entry, i) => (
            <TouchableOpacity
              key={`${selectedDate}-${i}`}
              style={styles.detail}
              onPress={() => {
                if (entry.type === 'planned') {
                  navigation.navigate('WorkoutDetail', { workout: entry.data });
                }
              }}
              activeOpacity={entry.type === 'planned' ? 0.7 : 1}
            >
              <View style={styles.detailHeader}>
                <View style={[styles.colorBar, { backgroundColor: entry.color }]} />
                <View style={styles.detailContent}>
                  <Text style={styles.detailTitle}>{entry.title}</Text>
                  {entry.subtitle ? (
                    <Text style={styles.detailSubtitle}>{entry.subtitle}</Text>
                  ) : null}
                </View>
                {entry.type === 'planned' && (
                  <Text style={styles.tapHint}>›</Text>
                )}
              </View>
            </TouchableOpacity>
          ))}
        </ScrollView>
      ) : selectedDate ? (
        <View style={styles.placeholder}>
          <Text style={styles.placeholderText}>No activities on this date</Text>
        </View>
      ) : (
        <View style={styles.placeholder}>
          <Text style={styles.placeholderText}>Tap a date to view details</Text>
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
  entryList: { flex: 1, paddingHorizontal: spacing.md },
  detail: {
    backgroundColor: colors.card, borderRadius: 12, marginBottom: spacing.sm, padding: spacing.md,
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  detailHeader: { flexDirection: 'row', alignItems: 'center' },
  colorBar: { width: 4, borderRadius: 2, alignSelf: 'stretch', marginRight: spacing.md },
  detailContent: { flex: 1 },
  detailTitle: { fontSize: fontSize.md, fontWeight: '600', color: colors.text },
  detailSubtitle: { fontSize: fontSize.sm, color: colors.textSecondary, marginTop: 2 },
  tapHint: { fontSize: fontSize.lg, color: colors.textTertiary, fontWeight: '600' },
  placeholder: { alignItems: 'center', padding: spacing.xl },
  placeholderText: { fontSize: fontSize.sm, color: colors.textSecondary },
});
