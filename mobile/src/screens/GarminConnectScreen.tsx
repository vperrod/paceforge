import React from 'react';
import {
  View, Text, StyleSheet, TextInput, TouchableOpacity,
  Alert, ActivityIndicator, KeyboardAvoidingView, Platform, ScrollView,
} from 'react-native';
import { colors, spacing, fontSize } from '../theme';
import api from '../api/client';

type GarminState = 'loading' | 'disconnected' | 'login' | 'mfa' | 'connecting' | 'connected';

export default function GarminConnectScreen() {
  const [state, setState] = React.useState<GarminState>('loading');
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [mfaCode, setMfaCode] = React.useState('');
  const [lastSynced, setLastSynced] = React.useState<string | null>(null);

  React.useEffect(() => {
    checkStatus();
  }, []);

  const checkStatus = async () => {
    setState('loading');
    try {
      const { data } = await api.get('/garmin/status');
      if (data.connected) {
        setLastSynced(data.last_synced?.slice(0, 16).replace('T', ' ') || null);
        setState('connected');
      } else {
        setState('disconnected');
      }
    } catch {
      setState('disconnected');
    }
  };

  const handleLogin = async () => {
    if (!email.trim() || !password) {
      Alert.alert('Error', 'Please enter your Garmin email and password');
      return;
    }
    setState('connecting');
    try {
      const { data } = await api.post('/garmin/login', {
        email: email.trim(),
        password,
      });
      if (data.status === 'mfa_required') {
        setState('mfa');
      } else {
        setState('connected');
        setLastSynced(new Date().toISOString().slice(0, 16).replace('T', ' '));
      }
    } catch (err: any) {
      setState('login');
      const msg = err?.response?.data?.detail || 'Failed to connect to Garmin';
      Alert.alert('Connection Failed', msg);
    }
  };

  const handleMfa = async () => {
    if (!mfaCode.trim()) {
      Alert.alert('Error', 'Please enter the verification code');
      return;
    }
    setState('connecting');
    try {
      await api.post('/garmin/mfa', { code: mfaCode.trim() });
      setState('connected');
      setLastSynced(new Date().toISOString().slice(0, 16).replace('T', ' '));
    } catch (err: any) {
      setState('mfa');
      const msg = err?.response?.data?.detail || 'Invalid code';
      Alert.alert('MFA Failed', msg);
    }
  };

  if (state === 'loading') {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  if (state === 'connected') {
    return (
      <ScrollView style={styles.container} contentContainerStyle={styles.content}>
        <View style={styles.statusCard}>
          <View style={styles.connectedIcon}>
            <Text style={styles.checkmark}>✓</Text>
          </View>
          <Text style={styles.connectedTitle}>Garmin Connected</Text>
          {lastSynced && (
            <Text style={styles.lastSync}>Last synced: {lastSynced}</Text>
          )}
        </View>
        <TouchableOpacity style={styles.refreshBtn} onPress={checkStatus}>
          <Text style={styles.refreshText}>Refresh Status</Text>
        </TouchableOpacity>
      </ScrollView>
    );
  }

  if (state === 'connecting') {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.connectingText}>Connecting to Garmin...</Text>
        <Text style={styles.connectingHint}>This may take 30–45 seconds on first login</Text>
      </View>
    );
  }

  if (state === 'mfa') {
    return (
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView contentContainerStyle={styles.formContent} keyboardShouldPersistTaps="handled">
          <Text style={styles.title}>Verification Required</Text>
          <Text style={styles.subtitle}>
            Garmin sent a verification code to your email. Enter it below.
          </Text>
          <TextInput
            style={styles.input}
            value={mfaCode}
            onChangeText={setMfaCode}
            placeholder="6-digit code"
            placeholderTextColor={colors.textTertiary}
            keyboardType="number-pad"
            autoFocus
          />
          <TouchableOpacity style={styles.button} onPress={handleMfa}>
            <Text style={styles.buttonText}>Verify</Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    );
  }

  // disconnected or login state
  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView contentContainerStyle={styles.formContent} keyboardShouldPersistTaps="handled">
        <Text style={styles.title}>Connect Garmin</Text>
        <Text style={styles.subtitle}>
          Sign in with your Garmin Connect credentials to sync your running data.
        </Text>

        <Text style={styles.label}>Garmin Email</Text>
        <TextInput
          style={styles.input}
          value={email}
          onChangeText={setEmail}
          placeholder="you@example.com"
          placeholderTextColor={colors.textTertiary}
          keyboardType="email-address"
          autoCapitalize="none"
          autoCorrect={false}
        />

        <Text style={styles.label}>Password</Text>
        <TextInput
          style={styles.input}
          value={password}
          onChangeText={setPassword}
          placeholder="••••••••"
          placeholderTextColor={colors.textTertiary}
          secureTextEntry
        />

        <TouchableOpacity
          style={[styles.button, (!email.trim() || !password) && styles.buttonDisabled]}
          onPress={handleLogin}
          disabled={!email.trim() || !password}
        >
          <Text style={styles.buttonText}>Connect</Text>
        </TouchableOpacity>

        <Text style={styles.privacyNote}>
          Your credentials are sent securely to our server and used only to authenticate with Garmin.
          They are not stored.
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingTop: spacing.xl },
  formContent: { flexGrow: 1, justifyContent: 'center', padding: spacing.lg },
  title: { fontSize: fontSize.xl, fontWeight: '700', color: colors.text, marginBottom: spacing.sm },
  subtitle: {
    fontSize: fontSize.sm, color: colors.textSecondary, lineHeight: 20, marginBottom: spacing.lg,
  },
  label: {
    fontSize: fontSize.sm, fontWeight: '600', color: colors.text,
    marginBottom: spacing.xs, marginTop: spacing.md,
  },
  input: {
    backgroundColor: colors.inputBg, borderRadius: 8, padding: spacing.md,
    fontSize: fontSize.md, color: colors.text, borderWidth: 1, borderColor: colors.border,
  },
  button: {
    backgroundColor: colors.primary, borderRadius: 10, padding: spacing.md,
    alignItems: 'center', marginTop: spacing.lg,
  },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: '#fff', fontSize: fontSize.md, fontWeight: '600' },
  privacyNote: {
    fontSize: fontSize.xs, color: colors.textTertiary, textAlign: 'center',
    marginTop: spacing.lg, lineHeight: 18,
  },
  statusCard: {
    backgroundColor: colors.card, borderRadius: 16, padding: spacing.xl,
    alignItems: 'center', borderWidth: 1, borderColor: colors.primary + '30',
  },
  connectedIcon: {
    width: 56, height: 56, borderRadius: 28, backgroundColor: colors.primary + '20',
    justifyContent: 'center', alignItems: 'center', marginBottom: spacing.md,
  },
  checkmark: { fontSize: 24, color: colors.primary, fontWeight: '700' },
  connectedTitle: {
    fontSize: fontSize.lg, fontWeight: '700', color: colors.text, marginBottom: spacing.xs,
  },
  lastSync: { fontSize: fontSize.sm, color: colors.textSecondary },
  refreshBtn: {
    marginTop: spacing.lg, padding: spacing.md, backgroundColor: colors.card,
    borderRadius: 12, alignItems: 'center', borderWidth: 1, borderColor: colors.borderSubtle,
  },
  refreshText: { color: colors.sky, fontWeight: '600', fontSize: fontSize.sm },
  connectingText: {
    color: colors.text, fontSize: fontSize.md, fontWeight: '600', marginTop: spacing.lg,
  },
  connectingHint: {
    color: colors.textSecondary, fontSize: fontSize.sm, marginTop: spacing.sm, textAlign: 'center',
    paddingHorizontal: spacing.xl,
  },
});
