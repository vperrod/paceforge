import React from 'react';
import {
  View, Text, StyleSheet, ScrollView, ActivityIndicator,
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { colors, spacing, fontSize } from '../theme';
import api from '../api/client';

type Props = NativeStackScreenProps<any, 'ActivityDetail'>;

function fmtPace(secPerKm: number | null | undefined): string {
  if (!secPerKm || secPerKm <= 0) return '—';
  const m = Math.floor(secPerKm / 60);
  const s = Math.round(secPerKm % 60);
  return `${m}:${s.toString().padStart(2, '0')}/km`;
}

function fmtDuration(seconds: number | null | undefined): string {
  if (!seconds) return '—';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.round(seconds % 60);
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function fmtDist(meters: number | null | undefined): string {
  if (!meters) return '—';
  return meters >= 1000 ? `${(meters / 1000).toFixed(2)} km` : `${Math.round(meters)} m`;
}

const ZONE_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#F97316', '#EF4444'];
const ZONE_LABELS = ['Z1 Easy', 'Z2 Aerobic', 'Z3 Tempo', 'Z4 Threshold', 'Z5 Max'];

export default function ActivityDetailScreen({ route }: Props) {
  const { activityId, activity } = route.params || {};
  const [detail, setDetail] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    loadDetail();
  }, []);

  const loadDetail = async () => {
    try {
      const { data } = await api.get(`/activities/${activityId}`);
      setDetail(data);
    } catch {
      setError('Could not load activity details');
    } finally {
      setLoading(false);
    }
  };

  // Use activity summary from either the detail response or the passed-in activity
  const summary = detail?.summary || activity || {};
  const dist = summary.distance || summary.distance_meters || summary.summaryDTO?.distance;
  const dur = summary.duration || summary.duration_seconds || summary.summaryDTO?.duration;
  const avgPace = summary.avg_pace_sec_per_km || summary.averagePace
    || (dur && dist ? dur / (dist / 1000) : null);
  const avgHR = summary.avg_hr || summary.averageHR || summary.summaryDTO?.averageHR;
  const maxHR = summary.max_hr || summary.maxHR || summary.summaryDTO?.maxHR;
  const calories = summary.calories || summary.summaryDTO?.calories;
  const cadence = summary.avg_running_cadence || summary.averageRunningCadence
    || summary.summaryDTO?.averageRunningCadence;
  const elevation = summary.elevation_gain || summary.elevationGain
    || summary.summaryDTO?.elevationGain;
  const aerobicTE = summary.training_effect_aerobic || summary.aerobicTrainingEffect
    || summary.summaryDTO?.aerobicTrainingEffect;
  const anaerobicTE = summary.training_effect_anaerobic || summary.anaerobicTrainingEffect
    || summary.summaryDTO?.anaerobicTrainingEffect;
  const actName = summary.activityName || summary.name || 'Activity';

  // Splits from lapDTOs or split_summaries
  const laps = detail?.splits?.lapDTOs || detail?.split_summaries?.splitSummaries || [];

  // HR zones
  const hrZones = detail?.hr_zones || [];
  const hrEntries = Array.isArray(hrZones) ? hrZones : hrZones?.hrTimeInZones || [];
  const totalZoneTime = hrEntries.reduce((s: number, z: any) => s + (z.secsInZone || 0), 0);

  // Weather
  const weather = detail?.weather;

  // Compute avg pace across splits for color coding
  const splitPaces = laps.map((lap: any) => {
    const d = lap.distance || lap.splitDistance;
    const t = lap.duration || lap.splitDuration || lap.movingDuration;
    return d && t ? t / (d / 1000) : 0;
  }).filter((p: number) => p > 0);
  const avgSplitPace = splitPaces.length > 0
    ? splitPaces.reduce((a: number, b: number) => a + b, 0) / splitPaces.length
    : 0;

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading activity details...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Header */}
      <Text style={styles.activityName}>{actName}</Text>
      {summary.startTimeLocal && (
        <Text style={styles.activityDate}>
          {(summary.startTimeLocal || summary.start_time || '').replace('T', ' ').slice(0, 16)}
        </Text>
      )}

      {/* Metrics Grid */}
      <View style={styles.metricsGrid}>
        {dist ? <MetricBox label="Distance" value={fmtDist(dist)} /> : null}
        {dur ? <MetricBox label="Duration" value={fmtDuration(dur)} /> : null}
        {avgPace && avgPace > 0 ? <MetricBox label="Avg Pace" value={fmtPace(avgPace)} accent={colors.primary} /> : null}
        {avgHR ? <MetricBox label="Avg HR" value={`${Math.round(avgHR)}`} unit="bpm" accent={colors.danger} /> : null}
        {maxHR ? <MetricBox label="Max HR" value={`${Math.round(maxHR)}`} unit="bpm" /> : null}
        {cadence ? <MetricBox label="Cadence" value={`${Math.round(cadence)}`} unit="spm" /> : null}
        {calories ? <MetricBox label="Calories" value={`${Math.round(calories)}`} unit="kcal" /> : null}
        {elevation ? <MetricBox label="Elevation" value={`${Math.round(elevation)}`} unit="m" /> : null}
        {aerobicTE ? <MetricBox label="Aerobic TE" value={aerobicTE.toFixed(1)} accent={colors.sky} /> : null}
        {anaerobicTE ? <MetricBox label="Anaerobic TE" value={anaerobicTE.toFixed(1)} accent={colors.amber} /> : null}
      </View>

      {/* Splits Table */}
      {laps.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Splits</Text>
          <View style={styles.splitsHeader}>
            <Text style={[styles.splitCell, styles.splitNum]}>#</Text>
            <Text style={[styles.splitCell, styles.splitDist]}>Dist</Text>
            <Text style={[styles.splitCell, styles.splitPace]}>Pace</Text>
            <Text style={[styles.splitCell, styles.splitHR]}>HR</Text>
            <View style={styles.splitBar} />
          </View>
          {laps.map((lap: any, i: number) => {
            const d = lap.distance || lap.splitDistance;
            const t = lap.duration || lap.splitDuration || lap.movingDuration;
            const pace = d && t ? t / (d / 1000) : 0;
            const hr = lap.averageHR || lap.averageHeartRate;
            const isFaster = pace > 0 && pace <= avgSplitPace;
            const barWidth = avgSplitPace > 0 && pace > 0
              ? Math.min(100, Math.max(20, (avgSplitPace / pace) * 80))
              : 50;

            return (
              <View key={i} style={styles.splitRow}>
                <Text style={[styles.splitCell, styles.splitNum]}>{i + 1}</Text>
                <Text style={[styles.splitCell, styles.splitDist]}>{fmtDist(d)}</Text>
                <Text style={[
                  styles.splitCell, styles.splitPace,
                  { color: isFaster ? colors.primary : colors.danger },
                ]}>
                  {fmtPace(pace)}
                </Text>
                <Text style={[styles.splitCell, styles.splitHR]}>
                  {hr ? Math.round(hr) : '—'}
                </Text>
                <View style={styles.splitBar}>
                  <View style={[
                    styles.splitBarFill,
                    {
                      width: `${barWidth}%`,
                      backgroundColor: isFaster ? colors.primary : colors.danger,
                    },
                  ]} />
                </View>
              </View>
            );
          })}
        </View>
      )}

      {/* HR Zone Distribution */}
      {hrEntries.length > 0 && totalZoneTime > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Heart Rate Zones</Text>
          {hrEntries.slice(0, 5).map((zone: any, i: number) => {
            const secs = zone.secsInZone || 0;
            const pct = totalZoneTime > 0 ? (secs / totalZoneTime) * 100 : 0;
            return (
              <View key={i} style={styles.zoneRow}>
                <Text style={styles.zoneLabel}>{ZONE_LABELS[i] || `Z${i + 1}`}</Text>
                <View style={styles.zoneBarBg}>
                  <View style={[
                    styles.zoneBarFill,
                    { width: `${pct}%`, backgroundColor: ZONE_COLORS[i] },
                  ]} />
                </View>
                <Text style={styles.zoneTime}>{fmtDuration(secs)}</Text>
                <Text style={styles.zonePct}>{pct.toFixed(0)}%</Text>
              </View>
            );
          })}
        </View>
      )}

      {/* Weather */}
      {weather && (weather.temp || weather.temperature) && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Weather</Text>
          <View style={styles.weatherRow}>
            {(weather.temp ?? weather.temperature) != null && (
              <Text style={styles.weatherItem}>
                🌡 {Math.round(weather.temp ?? weather.temperature)}°C
              </Text>
            )}
            {weather.weatherTypeDTO?.weatherTypeName && (
              <Text style={styles.weatherItem}>
                {weather.weatherTypeDTO.weatherTypeName}
              </Text>
            )}
            {weather.humidity != null && (
              <Text style={styles.weatherItem}>💧 {weather.humidity}%</Text>
            )}
            {weather.windSpeed != null && (
              <Text style={styles.weatherItem}>
                💨 {Math.round(weather.windSpeed)} km/h
              </Text>
            )}
          </View>
        </View>
      )}

      {error && !detail && (
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: colors.danger }]}>{error}</Text>
          <Text style={styles.fallbackText}>
            Showing basic data from activity summary. Full splits require Garmin connection.
          </Text>
        </View>
      )}
    </ScrollView>
  );
}

function MetricBox({ label, value, unit, accent }: {
  label: string; value: string; unit?: string; accent?: string;
}) {
  return (
    <View style={styles.metricBox}>
      <Text style={[styles.metricValue, accent ? { color: accent } : null]}>{value}</Text>
      {unit && <Text style={styles.metricUnit}>{unit}</Text>}
      <Text style={styles.metricLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.md, paddingBottom: spacing.xl * 2 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: colors.background },
  loadingText: { color: colors.textSecondary, marginTop: spacing.md, fontSize: fontSize.sm },

  activityName: { fontSize: fontSize.xl, fontWeight: '700', color: colors.text },
  activityDate: { fontSize: fontSize.sm, color: colors.textSecondary, marginTop: spacing.xs, marginBottom: spacing.lg },

  metricsGrid: {
    flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, marginBottom: spacing.lg,
  },
  metricBox: {
    backgroundColor: colors.card, borderRadius: 12, padding: spacing.md,
    alignItems: 'center', minWidth: 90, flex: 1,
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  metricValue: { fontSize: fontSize.lg, fontWeight: '700', color: colors.text },
  metricUnit: { fontSize: fontSize.xs, color: colors.textTertiary, marginTop: 1 },
  metricLabel: { fontSize: fontSize.xs, color: colors.textSecondary, marginTop: 2 },

  section: {
    backgroundColor: colors.card, borderRadius: 12, padding: spacing.md, marginBottom: spacing.md,
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  sectionTitle: {
    fontSize: fontSize.sm, fontWeight: '700', color: colors.text,
    marginBottom: spacing.sm, textTransform: 'uppercase', letterSpacing: 0.5,
  },

  // Splits table
  splitsHeader: {
    flexDirection: 'row', alignItems: 'center', paddingBottom: spacing.xs,
    borderBottomWidth: 1, borderBottomColor: colors.borderSubtle, marginBottom: spacing.xs,
  },
  splitRow: {
    flexDirection: 'row', alignItems: 'center', paddingVertical: spacing.xs + 2,
    borderBottomWidth: 1, borderBottomColor: colors.borderSubtle,
  },
  splitCell: { fontSize: fontSize.sm, color: colors.text },
  splitNum: { width: 28, color: colors.textTertiary, fontWeight: '600' },
  splitDist: { width: 70 },
  splitPace: { width: 72, fontWeight: '600' },
  splitHR: { width: 40, textAlign: 'center', color: colors.textSecondary },
  splitBar: { flex: 1, height: 6, borderRadius: 3, backgroundColor: colors.elevated, marginLeft: spacing.sm },
  splitBarFill: { height: 6, borderRadius: 3 },

  // HR zones
  zoneRow: {
    flexDirection: 'row', alignItems: 'center', marginBottom: spacing.sm,
  },
  zoneLabel: { width: 80, fontSize: fontSize.xs, color: colors.textSecondary, fontWeight: '500' },
  zoneBarBg: {
    flex: 1, height: 10, borderRadius: 5, backgroundColor: colors.elevated, marginHorizontal: spacing.sm,
  },
  zoneBarFill: { height: 10, borderRadius: 5 },
  zoneTime: { width: 48, fontSize: fontSize.xs, color: colors.text, textAlign: 'right' },
  zonePct: { width: 36, fontSize: fontSize.xs, color: colors.textSecondary, textAlign: 'right' },

  // Weather
  weatherRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  weatherItem: { fontSize: fontSize.sm, color: colors.text },

  fallbackText: { fontSize: fontSize.sm, color: colors.textSecondary, marginTop: spacing.sm },
});
