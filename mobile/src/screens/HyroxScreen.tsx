import React from 'react';
import {
  View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity,
  ActivityIndicator, Alert, RefreshControl,
} from 'react-native';
import { colors, spacing, fontSize } from '../theme';
import api from '../api/client';

function fmtTime(seconds: number | null | undefined): string {
  if (!seconds) return '—';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.round(seconds % 60);
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function fmtPace(secPerKm: number | null | undefined): string {
  if (!secPerKm || secPerKm <= 0) return '—';
  const m = Math.floor(secPerKm / 60);
  const s = Math.round(secPerKm % 60);
  return `${m}:${s.toString().padStart(2, '0')}/km`;
}

type SearchState = 'search' | 'preview' | 'loading' | 'results';

export default function HyroxScreen() {
  const [state, setState] = React.useState<SearchState>('loading');
  const [lastName, setLastName] = React.useState('');
  const [firstName, setFirstName] = React.useState('');
  const [gender, setGender] = React.useState('M');
  const [searching, setSearching] = React.useState(false);
  const [summaries, setSummaries] = React.useState<any[]>([]);
  const [selected, setSelected] = React.useState<Set<string>>(new Set());
  const [races, setRaces] = React.useState<any[]>([]);
  const [selectedRace, setSelectedRace] = React.useState(0);
  const [analysis, setAnalysis] = React.useState<any>(null);
  const [refreshing, setRefreshing] = React.useState(false);

  React.useEffect(() => {
    checkExisting();
  }, []);

  const checkExisting = async () => {
    try {
      // Try to load existing cached HYROX data via the profile endpoint
      const { data } = await api.get('/auth/profile');
      if (data?.hyrox_json) {
        const hyrox = JSON.parse(data.hyrox_json);
        if (hyrox?.results?.length > 0) {
          setRaces(hyrox.results);
          setState('results');
          loadAnalysis(0);
          return;
        }
      }
    } catch {}
    setState('search');
  };

  const handleSearch = async () => {
    if (!lastName.trim()) {
      Alert.alert('Required', 'Please enter your last name');
      return;
    }
    setSearching(true);
    try {
      const params = new URLSearchParams({
        name: lastName.trim(),
        firstname: firstName.trim(),
        gender,
      });
      const { data } = await api.get(`/hyrox/search?${params}`);
      setSummaries(data.summaries || []);
      setState('preview');
    } catch {
      Alert.alert('Error', 'Could not search HYROX results');
    } finally {
      setSearching(false);
    }
  };

  const toggleSelection = (url: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(url)) next.delete(url);
      else next.add(url);
      return next;
    });
  };

  const handleConfirm = async () => {
    if (selected.size === 0) {
      Alert.alert('Select', 'Please select at least one race');
      return;
    }
    setSearching(true);
    try {
      const { data } = await api.post('/hyrox/confirm', {
        name: lastName.trim(),
        firstname: firstName.trim(),
        gender,
        selected_urls: Array.from(selected),
      });
      const results = data?.results || [];
      setRaces(results);
      setSelectedRace(0);
      setState('results');
      if (results.length > 0) loadAnalysis(0);
    } catch {
      Alert.alert('Error', 'Could not import HYROX results');
    } finally {
      setSearching(false);
    }
  };

  const loadAnalysis = async (index: number) => {
    setAnalysis(null);
    try {
      const { data } = await api.get(`/hyrox/analyze/${index}`);
      setAnalysis(data);
    } catch {}
  };

  const onRefresh = async () => {
    setRefreshing(true);
    try {
      const { data } = await api.post('/hyrox/refresh');
      if (data?.results?.length > 0) {
        setRaces(data.results);
        setSelectedRace(0);
        loadAnalysis(0);
      }
    } catch {}
    setRefreshing(false);
  };

  const race = races[selectedRace];

  // SEARCH STATE
  if (state === 'search') {
    return (
      <ScrollView style={styles.container} contentContainerStyle={styles.searchContent}>
        <Text style={styles.searchTitle}>Find Your HYROX Results</Text>
        <Text style={styles.searchHint}>
          Search by name to import your HYROX race data
        </Text>

        <Text style={styles.inputLabel}>Last Name *</Text>
        <TextInput
          style={styles.input}
          value={lastName}
          onChangeText={setLastName}
          placeholder="e.g. Smith"
          placeholderTextColor={colors.textTertiary}
          autoCapitalize="words"
        />

        <Text style={styles.inputLabel}>First Name</Text>
        <TextInput
          style={styles.input}
          value={firstName}
          onChangeText={setFirstName}
          placeholder="e.g. John"
          placeholderTextColor={colors.textTertiary}
          autoCapitalize="words"
        />

        <Text style={styles.inputLabel}>Gender</Text>
        <View style={styles.genderRow}>
          {['M', 'F'].map(g => (
            <TouchableOpacity
              key={g}
              style={[styles.genderBtn, gender === g && styles.genderActive]}
              onPress={() => setGender(g)}
            >
              <Text style={[styles.genderText, gender === g && styles.genderTextActive]}>
                {g === 'M' ? 'Male' : 'Female'}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        <TouchableOpacity
          style={[styles.searchButton, searching && { opacity: 0.6 }]}
          onPress={handleSearch}
          disabled={searching}
        >
          {searching ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Text style={styles.searchButtonText}>Search</Text>
          )}
        </TouchableOpacity>
      </ScrollView>
    );
  }

  // PREVIEW / SELECT STATE
  if (state === 'preview') {
    return (
      <ScrollView style={styles.container} contentContainerStyle={styles.searchContent}>
        <Text style={styles.searchTitle}>Select Your Races</Text>
        <Text style={styles.searchHint}>
          {summaries.length} result{summaries.length !== 1 ? 's' : ''} found. Tap to select.
        </Text>

        {summaries.map((s: any, i: number) => {
          const url = s.athlete_url || s.url || `${i}`;
          const isSelected = selected.has(url);
          return (
            <TouchableOpacity
              key={i}
              style={[styles.previewCard, isSelected && styles.previewSelected]}
              onPress={() => toggleSelection(url)}
            >
              <View style={styles.previewCheck}>
                <Text style={{ color: isSelected ? colors.primary : colors.textTertiary, fontSize: 18 }}>
                  {isSelected ? '☑' : '☐'}
                </Text>
              </View>
              <View style={styles.previewInfo}>
                <Text style={styles.previewName}>{s.name || `${firstName} ${lastName}`}</Text>
                <Text style={styles.previewMeta}>
                  {s.city || ''}{s.city && s.total_time ? ' · ' : ''}{s.total_time || ''}
                </Text>
                {s.rank && <Text style={styles.previewRank}>Rank: #{s.rank}</Text>}
              </View>
            </TouchableOpacity>
          );
        })}

        {summaries.length === 0 && (
          <View style={styles.emptyPreview}>
            <Text style={styles.emptyText}>No results found</Text>
            <Text style={styles.emptyHint}>Try a different name or check spelling</Text>
          </View>
        )}

        <View style={styles.previewActions}>
          <TouchableOpacity
            style={styles.backButton}
            onPress={() => setState('search')}
          >
            <Text style={styles.backButtonText}>← Back</Text>
          </TouchableOpacity>
          {summaries.length > 0 && (
            <TouchableOpacity
              style={[styles.searchButton, { flex: 1 }, searching && { opacity: 0.6 }]}
              onPress={handleConfirm}
              disabled={searching}
            >
              {searching ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <Text style={styles.searchButtonText}>Import {selected.size} Race{selected.size !== 1 ? 's' : ''}</Text>
              )}
            </TouchableOpacity>
          )}
        </View>
      </ScrollView>
    );
  }

  // LOADING STATE
  if (state === 'loading') {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  // RESULTS STATE
  if (!race) {
    return (
      <View style={styles.center}>
        <Text style={styles.emptyText}>No HYROX data</Text>
        <TouchableOpacity style={styles.searchButton} onPress={() => setState('search')}>
          <Text style={styles.searchButtonText}>Search Races</Text>
        </TouchableOpacity>
      </View>
    );
  }

  // Parse splits
  const runSplits = race.run_splits || race.split_analysis?.filter((s: any) =>
    s.name?.toLowerCase().includes('run') || s.name?.toLowerCase().includes('km')
  ) || [];
  const stationSplits = race.split_analysis?.filter((s: any) =>
    !s.name?.toLowerCase().includes('run') && !s.name?.toLowerCase().includes('km') &&
    !s.name?.toLowerCase().includes('roxzone')
  ) || [];

  // Find fastest/slowest run for fade calc
  const runTimes = runSplits.map((s: any) => s.athlete_seconds || s.seconds || 0).filter((t: number) => t > 0);
  const fastestRun = Math.min(...runTimes);

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}
    >
      {/* Race selector */}
      {races.length > 1 && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.raceTabs}>
          {races.map((r: any, i: number) => (
            <TouchableOpacity
              key={i}
              style={[styles.raceTab, i === selectedRace && styles.raceTabActive]}
              onPress={() => { setSelectedRace(i); loadAnalysis(i); }}
            >
              <Text style={[styles.raceTabText, i === selectedRace && styles.raceTabTextActive]}>
                {r.city || `Race ${i + 1}`}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      )}

      {/* Summary */}
      <View style={styles.summaryCard}>
        <Text style={styles.raceCityTitle}>
          {race.city || 'HYROX Race'} {race.event_date ? `· ${race.event_date}` : ''}
        </Text>
        {race.division && <Text style={styles.raceDivision}>{race.division}</Text>}

        <View style={styles.summaryMetrics}>
          <SummaryMetric label="Total Time" value={race.total_time_display || fmtTime(race.total_time_seconds)} accent={colors.primary} />
          {race.rank && <SummaryMetric label="Rank" value={`#${race.rank}`} />}
          {race.avg_run_pace && <SummaryMetric label="Avg Run Pace" value={fmtPace(race.avg_run_pace)} accent={colors.sky} />}
          {race.running_class && <SummaryMetric label="Runner Class" value={race.running_class.replace(/_/g, ' ')} />}
          {race.fade_pct != null && <SummaryMetric label="Fade" value={`${race.fade_pct.toFixed(1)}%`} accent={race.fade_pct > 10 ? colors.danger : colors.primary} />}
        </View>
      </View>

      {/* Running Splits */}
      {runSplits.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Running Splits (8 × 1km)</Text>
          {runSplits.map((split: any, i: number) => {
            const secs = split.athlete_seconds || split.seconds || 0;
            const fade = fastestRun > 0 && secs > 0 ? ((secs - fastestRun) / fastestRun) * 100 : 0;
            const maxFade = 30;
            const barPct = Math.max(30, 100 - (fade / maxFade) * 70);
            const barColor = fade <= 3 ? colors.primary : fade <= 10 ? colors.amber : colors.danger;

            return (
              <View key={i} style={styles.splitRow}>
                <Text style={styles.splitLabel}>{split.name || `Run ${i + 1}`}</Text>
                <View style={styles.splitBarBg}>
                  <View style={[styles.splitBarFill, { width: `${barPct}%`, backgroundColor: barColor }]} />
                </View>
                <Text style={styles.splitTime}>{fmtTime(secs)}</Text>
                {fade > 0 && <Text style={[styles.splitFade, { color: barColor }]}>+{fade.toFixed(0)}%</Text>}
              </View>
            );
          })}
        </View>
      )}

      {/* Station Performance */}
      {stationSplits.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Station Performance</Text>
          {stationSplits.map((split: any, i: number) => {
            const athlete = split.athlete_seconds || 0;
            const fieldAvg = split.field_avg || 0;
            const isBetter = fieldAvg > 0 && athlete < fieldAvg;

            return (
              <View key={i} style={styles.stationRow}>
                <Text style={styles.stationName}>{split.name}</Text>
                <Text style={[styles.stationTime, { color: isBetter ? colors.primary : colors.text }]}>
                  {fmtTime(athlete)}
                </Text>
                {fieldAvg > 0 && (
                  <Text style={styles.stationAvg}>
                    avg {fmtTime(fieldAvg)}
                  </Text>
                )}
              </View>
            );
          })}
        </View>
      )}

      {/* Analysis */}
      {analysis?.priorities?.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Training Priorities</Text>
          {analysis.priorities.map((p: any, i: number) => (
            <View key={i} style={styles.priorityRow}>
              <Text style={styles.priorityNum}>{i + 1}</Text>
              <View style={styles.priorityContent}>
                <Text style={styles.priorityTitle}>{p.area || p.name || p.station}</Text>
                {p.recommendation && <Text style={styles.priorityDesc}>{p.recommendation}</Text>}
              </View>
            </View>
          ))}
        </View>
      )}

      {/* New Search */}
      <TouchableOpacity
        style={styles.newSearchButton}
        onPress={() => setState('search')}
      >
        <Text style={styles.newSearchText}>Search Again</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

function SummaryMetric({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <View style={styles.summaryMetric}>
      <Text style={[styles.summaryValue, accent ? { color: accent } : null]}>{value}</Text>
      <Text style={styles.summaryLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.md, paddingBottom: spacing.xl * 2 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: colors.background, padding: spacing.xl },

  // Search
  searchContent: { padding: spacing.md, paddingBottom: spacing.xl },
  searchTitle: { fontSize: fontSize.xl, fontWeight: '700', color: colors.text, marginBottom: spacing.xs },
  searchHint: { fontSize: fontSize.sm, color: colors.textSecondary, marginBottom: spacing.lg },
  inputLabel: { fontSize: fontSize.xs, fontWeight: '600', color: colors.textSecondary, marginBottom: spacing.xs, textTransform: 'uppercase', letterSpacing: 0.5 },
  input: {
    backgroundColor: colors.card, borderRadius: 10, padding: spacing.md,
    fontSize: fontSize.md, color: colors.text, marginBottom: spacing.md,
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  genderRow: { flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.lg },
  genderBtn: {
    flex: 1, paddingVertical: spacing.sm, borderRadius: 10, alignItems: 'center',
    backgroundColor: colors.card, borderWidth: 1, borderColor: colors.borderSubtle,
  },
  genderActive: { backgroundColor: colors.primary + '20', borderColor: colors.primary + '40' },
  genderText: { fontSize: fontSize.sm, color: colors.textSecondary, fontWeight: '600' },
  genderTextActive: { color: colors.primary },
  searchButton: {
    backgroundColor: colors.primary, borderRadius: 12, padding: spacing.md,
    alignItems: 'center',
  },
  searchButtonText: { color: '#fff', fontWeight: '700', fontSize: fontSize.md },

  // Preview
  previewCard: {
    backgroundColor: colors.card, borderRadius: 12, padding: spacing.md, marginBottom: spacing.sm,
    flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: colors.borderSubtle,
  },
  previewSelected: { borderColor: colors.primary + '50', backgroundColor: colors.primary + '08' },
  previewCheck: { marginRight: spacing.md },
  previewInfo: { flex: 1 },
  previewName: { fontSize: fontSize.md, fontWeight: '600', color: colors.text },
  previewMeta: { fontSize: fontSize.sm, color: colors.textSecondary, marginTop: 2 },
  previewRank: { fontSize: fontSize.xs, color: colors.amber, marginTop: 2 },
  previewActions: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.md },
  backButton: {
    padding: spacing.md, borderRadius: 12, backgroundColor: colors.card,
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  backButtonText: { color: colors.text, fontWeight: '600', fontSize: fontSize.md },
  emptyPreview: { alignItems: 'center', padding: spacing.xl },
  emptyText: { fontSize: fontSize.lg, fontWeight: '600', color: colors.text },
  emptyHint: { fontSize: fontSize.sm, color: colors.textSecondary, textAlign: 'center', marginTop: spacing.sm },

  // Results - Race tabs
  raceTabs: { marginBottom: spacing.md },
  raceTab: {
    paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderRadius: 8,
    backgroundColor: colors.card, marginRight: spacing.sm,
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  raceTabActive: { backgroundColor: colors.primary + '20', borderColor: colors.primary + '40' },
  raceTabText: { fontSize: fontSize.sm, color: colors.textSecondary, fontWeight: '500' },
  raceTabTextActive: { color: colors.primary, fontWeight: '700' },

  // Summary
  summaryCard: {
    backgroundColor: colors.card, borderRadius: 12, padding: spacing.md, marginBottom: spacing.md,
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  raceCityTitle: { fontSize: fontSize.lg, fontWeight: '700', color: colors.text },
  raceDivision: { fontSize: fontSize.sm, color: colors.textSecondary, marginTop: spacing.xs, textTransform: 'capitalize' },
  summaryMetrics: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, marginTop: spacing.md },
  summaryMetric: {
    backgroundColor: colors.elevated, borderRadius: 10, paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md, alignItems: 'center', minWidth: 80,
  },
  summaryValue: { fontSize: fontSize.md, fontWeight: '700', color: colors.text },
  summaryLabel: { fontSize: fontSize.xs, color: colors.textSecondary, marginTop: 2 },

  // Sections
  section: {
    backgroundColor: colors.card, borderRadius: 12, padding: spacing.md, marginBottom: spacing.md,
    borderWidth: 1, borderColor: colors.borderSubtle,
  },
  sectionTitle: {
    fontSize: fontSize.sm, fontWeight: '700', color: colors.text,
    textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: spacing.sm,
  },

  // Run splits
  splitRow: { flexDirection: 'row', alignItems: 'center', marginBottom: spacing.sm },
  splitLabel: { width: 55, fontSize: fontSize.xs, color: colors.textSecondary },
  splitBarBg: { flex: 1, height: 8, borderRadius: 4, backgroundColor: colors.elevated, marginHorizontal: spacing.sm, overflow: 'hidden' },
  splitBarFill: { height: 8, borderRadius: 4 },
  splitTime: { width: 48, fontSize: fontSize.xs, color: colors.text, textAlign: 'right', fontWeight: '600' },
  splitFade: { width: 40, fontSize: fontSize.xs, textAlign: 'right' },

  // Stations
  stationRow: {
    flexDirection: 'row', alignItems: 'center', paddingVertical: spacing.sm,
    borderBottomWidth: 1, borderBottomColor: colors.borderSubtle,
  },
  stationName: { flex: 1, fontSize: fontSize.sm, color: colors.text },
  stationTime: { fontSize: fontSize.sm, fontWeight: '600', marginRight: spacing.md },
  stationAvg: { fontSize: fontSize.xs, color: colors.textTertiary, width: 65, textAlign: 'right' },

  // Priorities
  priorityRow: { flexDirection: 'row', marginBottom: spacing.sm },
  priorityNum: {
    width: 24, height: 24, borderRadius: 12, backgroundColor: colors.primary + '20',
    textAlign: 'center', lineHeight: 24, fontSize: fontSize.xs, fontWeight: '700', color: colors.primary,
    marginRight: spacing.sm,
  },
  priorityContent: { flex: 1 },
  priorityTitle: { fontSize: fontSize.sm, fontWeight: '600', color: colors.text },
  priorityDesc: { fontSize: fontSize.sm, color: colors.textSecondary, marginTop: 2, lineHeight: 20 },

  // New search
  newSearchButton: {
    backgroundColor: colors.card, borderRadius: 12, padding: spacing.md,
    alignItems: 'center', borderWidth: 1, borderColor: colors.borderSubtle,
  },
  newSearchText: { color: colors.textSecondary, fontWeight: '600', fontSize: fontSize.sm },
});
