/**
 * Health data sync service.
 * Reads body composition from Apple HealthKit (iOS) or Google Health Connect (Android)
 * and posts to the PaceForge API.
 */
import { Platform } from 'react-native';
import api from '../api/client';

// ── Types ──

interface HealthDataPoint {
  date: string; // YYYY-MM-DD
  value: number;
  source: string;
}

interface BodyComposition {
  height_cm: number | null;
  weight_kg: HealthDataPoint[];
  bmi: HealthDataPoint[];
  body_fat_pct: HealthDataPoint[];
  lean_body_mass_kg: HealthDataPoint[];
}

interface HealthPayload {
  sources: string[];
  last_sync?: string;
  body_composition: BodyComposition;
}

// ── Apple HealthKit (iOS) ──

async function fetchAppleHealth(days: number): Promise<BodyComposition> {
  // Lazy-import to avoid crash on Android
  const AppleHealthKit = require('react-native-health').default;
  const { HealthKitDataType } = require('react-native-health');

  const permissions = {
    permissions: {
      read: [
        HealthKitDataType.Weight,
        HealthKitDataType.Height,
        HealthKitDataType.BodyFatPercentage,
        HealthKitDataType.LeanBodyMass,
        HealthKitDataType.BodyMassIndex,
      ],
      write: [],
    },
  };

  await new Promise<void>((resolve, reject) => {
    AppleHealthKit.initHealthKit(permissions, (err: unknown) => {
      if (err) reject(err);
      else resolve();
    });
  });

  const startDate = new Date();
  startDate.setDate(startDate.getDate() - days);
  const options = { startDate: startDate.toISOString() };

  const toPoints = (
    samples: Array<{ startDate: string; value: number }>,
    source: string,
  ): HealthDataPoint[] =>
    samples.map((s) => ({
      date: s.startDate.slice(0, 10),
      value: s.value,
      source,
    }));

  const [weightSamples, bmiSamples, bfSamples, lbmSamples, heightSamples] =
    await Promise.all([
      new Promise<any[]>((res, rej) =>
        AppleHealthKit.getWeightSamples(options, (e: unknown, r: any[]) =>
          e ? rej(e) : res(r ?? []),
        ),
      ),
      new Promise<any[]>((res, rej) =>
        AppleHealthKit.getBmiSamples(options, (e: unknown, r: any[]) =>
          e ? rej(e) : res(r ?? []),
        ),
      ),
      new Promise<any[]>((res, rej) =>
        AppleHealthKit.getBodyFatPercentageSamples(
          options,
          (e: unknown, r: any[]) => (e ? rej(e) : res(r ?? [])),
        ),
      ),
      new Promise<any[]>((res, rej) =>
        AppleHealthKit.getLeanBodyMassSamples(
          options,
          (e: unknown, r: any[]) => (e ? rej(e) : res(r ?? [])),
        ),
      ),
      new Promise<any[]>((res, rej) =>
        AppleHealthKit.getHeightSamples(options, (e: unknown, r: any[]) =>
          e ? rej(e) : res(r ?? []),
        ),
      ),
    ]);

  const height_cm =
    heightSamples.length > 0
      ? heightSamples[heightSamples.length - 1].value * 100
      : null;

  return {
    height_cm,
    weight_kg: toPoints(weightSamples, 'apple_health'),
    bmi: toPoints(bmiSamples, 'apple_health'),
    body_fat_pct: toPoints(bfSamples, 'apple_health'),
    lean_body_mass_kg: toPoints(lbmSamples, 'apple_health'),
  };
}

// ── Google Health Connect (Android) ──

async function fetchGoogleHealthConnect(
  days: number,
): Promise<BodyComposition> {
  const {
    initialize,
    requestPermission,
    readRecords,
  } = require('react-native-health-connect');

  await initialize();

  await requestPermission([
    { accessType: 'read', recordType: 'Weight' },
    { accessType: 'read', recordType: 'Height' },
    { accessType: 'read', recordType: 'BodyFat' },
    { accessType: 'read', recordType: 'LeanBodyMass' },
  ]);

  const startTime = new Date();
  startTime.setDate(startTime.getDate() - days);
  const timeRange = {
    operator: 'after',
    startTime: startTime.toISOString(),
  };

  const [weightRecords, heightRecords, bfRecords, lbmRecords] =
    await Promise.all([
      readRecords('Weight', { timeRangeFilter: timeRange }).catch(
        () => ({ records: [] }),
      ),
      readRecords('Height', { timeRangeFilter: timeRange }).catch(
        () => ({ records: [] }),
      ),
      readRecords('BodyFat', { timeRangeFilter: timeRange }).catch(
        () => ({ records: [] }),
      ),
      readRecords('LeanBodyMass', { timeRangeFilter: timeRange }).catch(
        () => ({ records: [] }),
      ),
    ]);

  const toPoints = (
    records: Array<{ time: string; weight?: { inKilograms: number }; percentage?: number; mass?: { inKilograms: number } }>,
    extractor: (r: any) => number | null,
  ): HealthDataPoint[] =>
    records
      .map((r) => {
        const val = extractor(r);
        if (val == null) return null;
        return {
          date: (r.time ?? '').slice(0, 10),
          value: val,
          source: 'google_health_connect',
        };
      })
      .filter(Boolean) as HealthDataPoint[];

  const height_cm =
    heightRecords.records.length > 0
      ? heightRecords.records[heightRecords.records.length - 1].height
          ?.inMeters * 100
      : null;

  // Compute BMI from weight + height
  const weightPoints = toPoints(
    weightRecords.records,
    (r) => r.weight?.inKilograms ?? null,
  );
  const bmiPoints: HealthDataPoint[] = [];
  if (height_cm && height_cm > 0) {
    const hm = height_cm / 100;
    for (const wp of weightPoints) {
      bmiPoints.push({
        date: wp.date,
        value: Math.round((wp.value / (hm * hm)) * 10) / 10,
        source: 'google_health_connect',
      });
    }
  }

  return {
    height_cm: height_cm ?? null,
    weight_kg: weightPoints,
    bmi: bmiPoints,
    body_fat_pct: toPoints(
      bfRecords.records,
      (r) => r.percentage ?? null,
    ),
    lean_body_mass_kg: toPoints(
      lbmRecords.records,
      (r) => r.mass?.inKilograms ?? null,
    ),
  };
}

// ── Public API ──

/**
 * Fetch body composition from the platform health SDK and upload to PaceForge API.
 * @param days Number of days of history to fetch (default 90)
 * @returns The merged health data from the server
 */
export async function syncHealthData(days = 90): Promise<HealthPayload | null> {
  try {
    let bodyComp: BodyComposition;
    let source: string;

    if (Platform.OS === 'ios') {
      bodyComp = await fetchAppleHealth(days);
      source = 'apple_health';
    } else if (Platform.OS === 'android') {
      bodyComp = await fetchGoogleHealthConnect(days);
      source = 'google_health_connect';
    } else {
      console.log('Health sync not supported on this platform');
      return null;
    }

    const payload: HealthPayload = {
      sources: [source],
      body_composition: bodyComp,
    };

    const { data } = await api.post('/health/data', payload);
    return data;
  } catch (error) {
    console.error('Health sync failed:', error);
    return null;
  }
}

/**
 * Check if health sync is enabled in user preferences.
 */
export async function isHealthSyncEnabled(): Promise<boolean> {
  try {
    const { data } = await api.get('/preferences');
    const hc = data?.health_connections ?? {};
    if (Platform.OS === 'ios') return !!hc.apple_health;
    if (Platform.OS === 'android') return !!hc.google_health_connect;
    return false;
  } catch {
    return false;
  }
}
