import React from 'react';
import {
  View, Text, StyleSheet, FlatList, RefreshControl,
  TouchableOpacity, TextInput, KeyboardAvoidingView, Platform,
} from 'react-native';
import { colors, spacing, fontSize } from '../theme';
import api from '../api/client';

export default function FeedScreen() {
  const [events, setEvents] = React.useState<any[]>([]);
  const [refreshing, setRefreshing] = React.useState(false);
  const [expandedComments, setExpandedComments] = React.useState<string | null>(null);
  const [comments, setComments] = React.useState<Record<string, any[]>>({});
  const [commentText, setCommentText] = React.useState('');
  const [postingComment, setPostingComment] = React.useState(false);

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

  const handleLike = async (eventId: string) => {
    // Optimistic update
    setEvents((prev) =>
      prev.map((e) =>
        e.id === eventId
          ? { ...e, liked_by_me: !e.liked_by_me, like_count: e.like_count + (e.liked_by_me ? -1 : 1) }
          : e,
      ),
    );
    try {
      await api.post(`/feed/${eventId}/like`);
    } catch {
      // Revert on failure
      setEvents((prev) =>
        prev.map((e) =>
          e.id === eventId
            ? { ...e, liked_by_me: !e.liked_by_me, like_count: e.like_count + (e.liked_by_me ? -1 : 1) }
            : e,
        ),
      );
    }
  };

  const toggleComments = async (eventId: string) => {
    if (expandedComments === eventId) {
      setExpandedComments(null);
      return;
    }
    setExpandedComments(eventId);
    if (!comments[eventId]) {
      try {
        const { data } = await api.get(`/feed/${eventId}/comments`);
        setComments((prev) => ({ ...prev, [eventId]: data }));
      } catch {}
    }
  };

  const postComment = async (eventId: string) => {
    const body = commentText.trim();
    if (!body) return;
    setPostingComment(true);
    try {
      await api.post(`/feed/${eventId}/comment`, { body });
      setCommentText('');
      // Refresh comments
      const { data } = await api.get(`/feed/${eventId}/comments`);
      setComments((prev) => ({ ...prev, [eventId]: data }));
      // Update count
      setEvents((prev) =>
        prev.map((e) => (e.id === eventId ? { ...e, comment_count: (e.comment_count || 0) + 1 } : e)),
      );
    } catch {}
    setPostingComment(false);
  };

  const renderEvent = ({ item }: { item: any }) => (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.userDot}>
          <Text style={styles.userDotText}>{(item.user_name || '?')[0].toUpperCase()}</Text>
        </View>
        <Text style={styles.cardUser}>{item.user_name || 'You'}</Text>
      </View>
      <Text style={styles.cardTitle}>{item.title}</Text>
      {item.body ? <Text style={styles.cardBody}>{item.body}</Text> : null}
      <View style={styles.cardActions}>
        <TouchableOpacity style={styles.actionBtn} onPress={() => handleLike(item.id)}>
          <Text style={[styles.actionIcon, item.liked_by_me && styles.liked]}>
            {item.liked_by_me ? '♥' : '♡'}
          </Text>
          <Text style={styles.actionCount}>{item.like_count || 0}</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionBtn} onPress={() => toggleComments(item.id)}>
          <Text style={styles.actionIcon}>💬</Text>
          <Text style={styles.actionCount}>{item.comment_count || 0}</Text>
        </TouchableOpacity>
      </View>
      {expandedComments === item.id && (
        <View style={styles.commentsSection}>
          {(comments[item.id] || []).map((c: any) => (
            <View key={c.id} style={styles.commentRow}>
              <Text style={styles.commentAuthor}>{c.user_name}</Text>
              <Text style={styles.commentBody}>{c.body}</Text>
            </View>
          ))}
          <View style={styles.commentInput}>
            <TextInput
              style={styles.commentField}
              value={commentText}
              onChangeText={setCommentText}
              placeholder="Add a comment..."
              placeholderTextColor={colors.textTertiary}
              editable={!postingComment}
            />
            <TouchableOpacity
              onPress={() => postComment(item.id)}
              disabled={postingComment || !commentText.trim()}
            >
              <Text style={[styles.sendBtn, (!commentText.trim() || postingComment) && styles.sendDisabled]}>
                Send
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      )}
    </View>
  );

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <FlatList
        data={events}
        keyExtractor={(item) => item.id}
        renderItem={renderEvent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />
        }
        contentContainerStyle={events.length === 0 ? styles.empty : styles.list}
        ListEmptyComponent={
          <View style={styles.emptyView}>
            <Text style={styles.emptyIcon}>🏃</Text>
            <Text style={styles.emptyText}>No activity yet</Text>
            <Text style={styles.emptyHint}>
              Complete a workout or add friends to see their activity here
            </Text>
          </View>
        }
      />
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  list: { padding: spacing.md },
  card: {
    backgroundColor: colors.card,
    borderRadius: 12,
    padding: spacing.md,
    marginBottom: spacing.md,
    borderWidth: 1,
    borderColor: colors.borderSubtle,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: spacing.sm },
  userDot: {
    width: 28, height: 28, borderRadius: 14, backgroundColor: colors.primary + '25',
    justifyContent: 'center', alignItems: 'center', marginRight: spacing.sm,
  },
  userDotText: { color: colors.primary, fontSize: 12, fontWeight: '700' },
  cardUser: { fontSize: fontSize.xs, color: colors.textSecondary, fontWeight: '500' },
  cardTitle: { fontSize: fontSize.md, fontWeight: '600', color: colors.text },
  cardBody: { fontSize: fontSize.sm, color: colors.textSecondary, marginTop: spacing.xs, lineHeight: 20 },
  cardActions: { marginTop: spacing.sm, flexDirection: 'row', gap: spacing.lg },
  actionBtn: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  actionIcon: { fontSize: 16, color: colors.textSecondary },
  actionCount: { fontSize: fontSize.xs, color: colors.textSecondary },
  liked: { color: colors.danger },
  commentsSection: {
    marginTop: spacing.sm, paddingTop: spacing.sm,
    borderTopWidth: 1, borderTopColor: colors.borderSubtle,
  },
  commentRow: { marginBottom: spacing.sm },
  commentAuthor: { fontSize: fontSize.xs, color: colors.primary, fontWeight: '600' },
  commentBody: { fontSize: fontSize.sm, color: colors.text, marginTop: 2 },
  commentInput: {
    flexDirection: 'row', alignItems: 'center', gap: spacing.sm, marginTop: spacing.xs,
  },
  commentField: {
    flex: 1, backgroundColor: colors.elevated, borderRadius: 8,
    padding: spacing.sm, fontSize: fontSize.sm, color: colors.text,
  },
  sendBtn: { color: colors.primary, fontWeight: '600', fontSize: fontSize.sm },
  sendDisabled: { opacity: 0.4 },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  emptyView: { alignItems: 'center', padding: spacing.xl },
  emptyIcon: { fontSize: 48, marginBottom: spacing.md },
  emptyText: { fontSize: fontSize.lg, fontWeight: '600', color: colors.text },
  emptyHint: {
    fontSize: fontSize.sm, color: colors.textSecondary, textAlign: 'center', marginTop: spacing.sm,
  },
});
