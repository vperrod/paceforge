import { Platform } from 'react-native';

export const colors = {
  primary: '#4A90D9',
  secondary: '#00D26A',
  danger: '#FF5252',
  warning: '#FF9800',
  background: Platform.select({ ios: '#F2F2F7', android: '#FAFAFA' }) ?? '#F2F2F7',
  surface: '#FFFFFF',
  text: '#1C1C1E',
  textSecondary: '#8E8E93',
  border: '#E5E5EA',
  inputBg: Platform.select({ ios: '#EFEFF4', android: '#F5F5F5' }) ?? '#EFEFF4',
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
};

export const fontSize = {
  xs: 12,
  sm: 14,
  md: 16,
  lg: 20,
  xl: 28,
  xxl: 34,
};
