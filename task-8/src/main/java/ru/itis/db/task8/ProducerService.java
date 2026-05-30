package ru.itis.db.task8;

import org.postgresql.util.PGobject;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.concurrent.ThreadLocalRandom;

public final class ProducerService {

    private final DbConfig dbConfig;
    private final int ratePerSecond;
    private final boolean notificationsEnabled;

    public ProducerService(DbConfig dbConfig, int ratePerSecond, boolean notificationsEnabled) {
        this.dbConfig = dbConfig;
        this.ratePerSecond = ratePerSecond;
        this.notificationsEnabled = notificationsEnabled;
    }

    public void run() throws SQLException, InterruptedException {
        try (Connection connection = dbConfig.open()) {
            DemoDataInitializer.DemoContext demoContext = DemoDataInitializer.ensureDemoData(connection);
            long intervalNanos = Math.max(1L, 1_000_000_000L / Math.max(1, ratePerSecond));
            long nextTick = System.nanoTime();
            long produced = 0;

            while (true) {
                // случайным образом выбираем тип задачи и приоритет (20% задач с высоким приоритетом)
                QueueTaskSpec taskSpec = QueueTaskSpec.random();
                int priority = ThreadLocalRandom.current().nextInt(100) < 20 ? 100 : 0;
                long taskId = produceOne(connection, demoContext, taskSpec, priority);
                produced++;

                if (produced % 100 == 0) {
                    System.out.printf("[%s] producer inserted %d tasks, last task id=%d, priority=%d, type=%s%n",
                            Instant.now(), produced, taskId, priority, taskSpec.taskType());
                }

                nextTick += intervalNanos;
                long sleepNanos = nextTick - System.nanoTime();
                if (sleepNanos > 0) {
                    Thread.sleep(sleepNanos / 1_000_000L, (int) (sleepNanos % 1_000_000L));
                } else {
                    nextTick = System.nanoTime();
                }
            }
        }
    }

    private long produceOne(Connection connection,
                            DemoDataInitializer.DemoContext demoContext,
                            QueueTaskSpec taskSpec,
                            int priority) throws SQLException {
        connection.setAutoCommit(false);
        try {
            int userId = demoContext.randomUserId();
            int trackId = demoContext.randomTrackId();
            TaskPayload payload = switch (taskSpec) {
                case REFRESH_RECOMMENDATIONS -> createListeningTask(connection, userId, trackId, "refresh_recommendations");
                case RECALCULATE_TRACK_POPULARITY -> createListeningTask(connection, userId, trackId, "recalculate_track_popularity");
                case MODERATE_COMMENT -> createCommentTask(connection, userId, trackId);
            };

            long taskId = insertTask(connection, payload, priority);
            if (notificationsEnabled) {
                notifyWorkers(connection, taskId);
            }

            connection.commit();
            return taskId;
        } catch (SQLException ex) {
            connection.rollback();
            throw ex;
        } finally {
            connection.setAutoCommit(true);
        }
    }

    private TaskPayload createListeningTask(Connection connection, int userId, int trackId, String taskType)
            throws SQLException {
        String sql = """
                INSERT INTO listening_history(user_id, track_id, listened_at, device)
                VALUES (?, ?, NOW(), ?)
                RETURNING id
                """;
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setInt(1, userId);
            statement.setInt(2, trackId);
            statement.setString(3, randomDevice());
            try (ResultSet rs = statement.executeQuery()) {
                rs.next();
                long historyId = rs.getLong(1);
                String json = "{\"task_type\":\"" + taskType + "\",\"user_id\":" + userId +
                        ",\"track_id\":" + trackId + ",\"listening_history_id\":" + historyId + "}";
                return new TaskPayload(taskType, toJsonb(json));
            }
        }
    }

    private TaskPayload createCommentTask(Connection connection, int userId, int trackId) throws SQLException {
        String sql = """
                INSERT INTO comment(user_id, track_id, content, created_at)
                VALUES (?, ?, ?, NOW())
                RETURNING id
                """;
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setInt(1, userId);
            statement.setInt(2, trackId);
            statement.setString(3, "Auto-generated comment for moderation queue demo");
            try (ResultSet rs = statement.executeQuery()) {
                rs.next();
                long commentId = rs.getLong(1);
                String json = "{\"task_type\":\"moderate_comment\",\"user_id\":" + userId +
                        ",\"track_id\":" + trackId + ",\"comment_id\":" + commentId + "}";
                return new TaskPayload("moderate_comment", toJsonb(json));
            }
        }
    }

    private long insertTask(Connection connection, TaskPayload payload, int priority) throws SQLException {
        String sql = """
                INSERT INTO tasks(task_type, status, priority, payload, scheduled_at, created_at, updated_at)
                VALUES (?, 'Ready', ?, ?, NOW(), NOW(), NOW())
                RETURNING id
                """;
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, payload.taskType());
            statement.setInt(2, priority);
            statement.setObject(3, payload.payload());
            try (ResultSet rs = statement.executeQuery()) {
                rs.next();
                return rs.getLong(1);
            }
        }
    }

    private void notifyWorkers(Connection connection, long taskId) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement("SELECT pg_notify('tasks_channel', ?)")) {
            statement.setString(1, Long.toString(taskId));
            statement.execute();
        }
    }

    private static String randomDevice() {
        String[] devices = {"ios", "android", "web", "desktop"};
        return devices[ThreadLocalRandom.current().nextInt(devices.length)];
    }

    private static PGobject toJsonb(String json) throws SQLException {
        PGobject object = new PGobject();
        object.setType("jsonb");
        object.setValue(json);
        return object;
    }

    private record TaskPayload(String taskType, PGobject payload) {
    }

    public enum QueueTaskSpec {
        REFRESH_RECOMMENDATIONS("refresh_recommendations"),
        RECALCULATE_TRACK_POPULARITY("recalculate_track_popularity"),
        MODERATE_COMMENT("moderate_comment");

        private final String taskType;

        QueueTaskSpec(String taskType) {
            this.taskType = taskType;
        }

        public String taskType() {
            return taskType;
        }

        public static QueueTaskSpec random() {
            QueueTaskSpec[] values = values();
            return values[ThreadLocalRandom.current().nextInt(values.length)];
        }
    }
}
