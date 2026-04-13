import React from 'react';
import { View, Text, StyleSheet, FlatList, RefreshControl } from 'react-native';
import { colors, spacing, fontSize } from '../theme';
import api from '../api/client';

export default function FeedScreen() {
  const [events, setEvents] = React.useState<any[]>([]);
  const [refreshing, setRefreshing] = React.useState(false);

  const loadFeed = async () => {
    try {
      const { data } = await api.get('/feed');
      setEvents(data);
    } catch {}
  };

  React.useEffect(() => {
    loadFeed();
  }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadFeed();
    setRefreshing(false);
  };

  const renderEvent = ({ item }: { item: any }) => (
    <View style={styles.card}>
      <Text style={styles.cardUser}>{item.user_name || 'You'}</Text>
      <Text style={styles.cardTitle}>{item.title}</Text>
      {item.body ? <Text style={styles.cardBody}>{item.body}</Text> : null}
      <View style={styles.cardFooter}>
        <Text style={styles.cardMeta}>
          ❤️ {item.like_count || 0} · 💬 {item.comment_count || 0}
        </Text>
      </View>
    </View>
  );

  return (
    <View style={styles.container}>
      <FlatList
        data={events}
        keyExtractor={(item) => item.id}
        renderItem={renderEvent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        contentContainerStyle={events.length === 0 ? styles.empty : styles.list}
        ListEmptyComponent={
          <View style={styles.emptyView}>
            <Text style={styles.emptyIcon}>🏃</Text>
            <Text style={styles.emptyText}>No activity yet</Text>
            <Text style={styles.emptyHint}>Complete a workout or add friends to see their activity here</Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  list: { padding: spacing.md },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: spacing.md,
    marginBottom: spacing.md,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 1,
  },
  cardUser: { fontSize: fontSize.xs, color: colors.textSecondary, marginBottom: spacing.xs },
  cardTitle: { fontSize: fontSize.md, fontWeight: '600', color: colors.text },
  cardBody: { fontSize: fontSize.sm, color: colors.textSecondary, marginTop: spacing.xs },
  cardFooter: { marginTop: spacing.sm, flexDirection: 'row' },
  cardMeta: { fontSize: fontSize.xs, color: colors.textSecondary },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  emptyView: { alignItems: 'center', padding: spacing.xl },
  emptyIcon: { fontSize: 48, marginBottom: spacing.md },
  emptyText: { fontSize: fontSize.lg, fontWeight: '600', color: colors.text },
  emptyHint: { fontSize: fontSize.sm, color: colors.textSecondary, textAlign: 'center', marginTop: spacing.sm },
});
