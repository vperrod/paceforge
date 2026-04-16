import React from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, ScrollView,
  ActivityIndicator, RefreshControl,
} from 'react-native';
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

const today = () => new Date().toISOString().slice(0, 10);

export default function CalendarScreen() {
  const [markedDates, setMarkedDates] = React.useState<Record<string, any>>({});
  const [entries, setEntries] = React.useState<Record<string, CalendarEntry[]>>({});
  const [selectedDate, setSelectedDate] = React.useState<string>(today());
  const [loading, setLoading] = React.useState(true);
  const [syncing, setSyncing] = React.useState(false);
  const navigation = useNavigation<any>();

  React.useEffect(() => {
    loadCalendarData();
  }, []);

  const loadCalendarData = async (forceSync = false) => {
    const allEntries: Record<string, CalendarEntry[]> = {};

    const addEntry = (date: string, entry: CalendarEntry) => {
      if (!allEntries[date]) allEntries[date] = [];
      allEntries[date].push(entry);
    };

    // 1) Load past Garmin activities (all types)
    try {
      const url = forceSync ? '/activities?days=240&sync=true' : '/activities?days=240';
      const { data: activities } = await api.get(url);

      for (const act of activities || []) {
        const dateStr = (act.startTimeLocal || act.start_time || '').slice(0, 10);
        if (!dateStr) continue;

        const dist = act.distance || act.distance_meters;
        const dur = act.duration || act.duration_seconds;
        const distKm = dist ? (dist / 1000).toFixed(1) : null;
        const durationMin = dur ? Math.round(dur / 60) : null;
        const typeKey = act.activityType?.typeKey || act.activity_type || '';
        const isRun = typeKey.toLowerCase().includes('running');
        const name = act.activityName || act.name || typeKey || 'Activity';

        let subtitle = '';
        if (isRun && distKm && dur && dist) {
          const paceSeconds = dur / (dist / 1000);
          const paceMin = Math.floor(paceSeconds / 60);
          const paceSec = Math.round(paceSeconds % 60);
          subtitle = `${distKm} km · ${paceMin}:${String(paceSec).padStart(2, '0')}/km`;
        } else if (distKm) {
          subtitle = `${distKm} km${durationMin ? ` · ${durationMin} min` : ''}`;
        } else if (durationMin) {
          subtitle = `${durationMin} min`;
        }

        if (act.avg_hr || act.averageHR) {
          subtitle += ` · ${Math.round(act.avg_hr || act.averageHR)} bpm`;
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
        const dateStr = (sw.date || sw.scheduled_date || '').slice(0, 10);
        if (!dateStr) continue;
        addEntry(dateStr, {
          type: 'scheduled',
          title: `📅 ${sw.workoutName || sw.name || 'Scheduled'}`,
          subtitle: sw.description?.slice(0, 80) || undefined,
          color: colors.amber,
          data: sw,
        });
      }
    } catch {}

    setEntries(allEntries);

    // Build marked dates — auto-select today
    const todayStr = today();
    const marks: Record<string, any> = {};
    for (const [date, dateEntries] of Object.entries(allEntries)) {
      const hasActivity = dateEntries.some(e => e.type === 'activity');
      const hasPlanned = dateEntries.some(e => e.type === 'planned');
      marks[date] = {
        marked: true,
        dotColor: hasActivity ? colors.primary : hasPlanned ? colors.sky : colors.amber,
        selected: date === todayStr,
      };
    }
    // Ensure today is always in marks
    if (!marks[todayStr]) {
      marks[todayStr] = { selected: true };
    }
    setMarkedDates(marks);
    setLoading(false);
  };

  const handleSync = async () => {
    setSyncing(true);
    await loadCalendarData(true);
    setSyncing(false);
  };

  const onDayPress = (day: DateData) => {
    setSelectedDate(day.dateString);
    const updated = { ...markedDates };
    for (const d of Object.keys(updated)) {
      updated[d] = { ...updated[d], selected: d === day.dateString };
    }
    if (!updated[day.dateString]) {
      updated[day.dateString] = { selected: true };
    }
    setMarkedDates(updated);
  };

  const selectedEntries = entries[selectedDate] || [];

  return (
    <View style={styles.container}>
      {/* Sync header */}
      <View style={styles.syncHeader}>
        <Text style={styles.syncLabel}>
          {selectedDate === today() ? 'Today' : selectedDate}
        </Text>
        <TouchableOpacity
          style={styles.syncButton}
          onPress={handleSync}
          disabled={syncing}
        >
          {syncing ? (
            <ActivityIndicator size="small" color={colors.primary} />
          ) : (
            <Text style={styles.syncText}>↻ Sync Garmin</Text>
          )}
        </TouchableOpacity>
      </View>

      <ScrollView
        refreshControl={
          <RefreshControl
            refreshing={syncing}
            onRefresh={handleSync}
            tintColor={colors.primary}
          />
        }
      >
        <Calendar
          key="plan_calendar"
          initialDate={today()}
          current={today()}
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

        {loading ? (
          <View style={styles.placeholder}>
            <ActivityIndicator size="large" color={colors.primary} />
          </View>
        ) : selectedEntries.length > 0 ? (
          <View style={styles.entryList}>
            {selectedEntries.map((entry, i) => (
              <TouchableOpacity
                key={`${selectedDate}-${i}`}
                style={styles.detail}
                onPress={() => {
                  if (entry.type === 'activity') {
                    const actId = entry.data.activityId || entry.data.activity_id;
                    if (actId) {
                      navigation.navigate('ActivityDetail', { activityId: actId, activity: entry.data });
                    }
                  } else if (entry.type === 'planned') {
                    navigation.navigate('WorkoutDetail', { workout: entry.data });
                  }
                }}
                activeOpacity={0.7}
              >
                <View style={styles.detailHeader}>
                  <View style={[styles.colorBar, { backgroundColor: entry.color }]} />
                  <View style={styles.detailContent}>
                    <Text style={styles.detailTitle}>{entry.title}</Text>
                    {entry.subtitle ? (
                      <Text style={styles.detailSubtitle}>{entry.subtitle}</Text>
                    ) : null}
                  </View>
                  <Text style={styles.tapHint}>›</Text>
                </View>
              </TouchableOpacity>
            ))}
          </View>
        ) : (
          <View style={styles.placeholder}>
            <Text style={styles.placeholderText}>No activities on this date</Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  syncHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: spacing.md, paddingVertical: spacing.sm,
    borderBottomWidth: 1, borderBottomColor: colors.borderSubtle,
  },
  syncLabel: { fontSize: fontSize.sm, fontWeight: '600', color: colors.text },
  syncButton: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: colors.primary + '15', borderRadius: 8,
    paddingHorizontal: spacing.md, paddingVertical: spacing.xs + 2,
  },
  syncText: { color: colors.primary, fontWeight: '600', fontSize: fontSize.sm },
  calendar: {
    borderRadius: 12, margin: spacing.md, overflow: 'hidden',
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  entryList: { paddingHorizontal: spacing.md, paddingBottom: spacing.xl },
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
