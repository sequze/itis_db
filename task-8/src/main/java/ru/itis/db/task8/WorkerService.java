package ru.itis.db.task8;

import org.postgresql.PGConnection;
import org.postgresql.PGNotification;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Duration;
import java.time.Instant;
import java.util.concurrent.ThreadLocalRandom;

public final class WorkerService {

    private final DbConfig dbConfig;
    private final String workerName;
    private final int minProcessingMs;
    private final int maxProcessingMs;
    private final double failureProbability;
    private final int retryBaseSeconds;
    private final boolean notificationsEnabled;
    private final int waitTimeoutMs;

    public WorkerService(DbConfig dbConfig,
                         String workerName,
                         int minProcessingMs,
                         int maxProcessingMs,
                         double failureProbability,
                         int retryBaseSeconds,
                         boolean notificationsEnabled,
                         int waitTimeoutMs) {
        this.dbConfig = dbConfig;
        this.workerName = workerName;
        this.minProcessingMs = minProcessingMs;
        this.maxProcessingMs = maxProcessingMs;
        this.failureProbability = failureProbability;
        this.retryBaseSeconds = retryBaseSeconds;
        this.notificationsEnabled = notificationsEnabled;
        this.waitTimeoutMs = waitTimeoutMs;
    }

    public void run() throws SQLException, InterruptedException {
        // открываем два соединения: одно для работы с задачами, другое для прослушивания уведомлений
        try (Connection workConnection = dbConfig.open();
             Connection listenConnection = dbConfig.open()) {
            DemoDataInitializer.ensureDemoData(workConnection);
            PGConnection pgConnection = listenConnection.unwrap(PGConnection.class);

            if (notificationsEnabled) {
                try (PreparedStatement statement = listenConnection.prepareStatement("LISTEN tasks_channel")) {
                    statement.execute();
                }
            }

            long processed = 0;
            while (true) {
                ClaimedTask task = claimTask(workConnection);
                if (task == null) {
                    waitForSignal(pgConnection);
                    continue;
                }

                processed++;
                processTask(workConnection, task);

                if (processed % 50 == 0) {
                    System.out.printf("[%s] %s processed %d tasks, last task id=%d, priority=%d, type=%s%n",
                            Instant.now(), workerName, processed, task.id(), task.priority(), task.taskType());
                }
            }
        }
    }

    private ClaimedTask claimTask(Connection connection) throws SQLException {
        String sql = """
                WITH next_task AS (
                    SELECT id
                    FROM tasks
                    WHERE status = 'Ready'
                      AND scheduled_at <= NOW()
                    ORDER BY priority DESC, created_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                UPDATE tasks t
                SET status = 'Running',
                    started_at = NOW(),
                    updated_at = NOW(),
                    worker_name = ?
                FROM next_task
                WHERE t.id = next_task.id
                RETURNING t.id, t.task_type, t.priority, t.attempts, t.max_attempts, t.created_at
                """;

        connection.setAutoCommit(false);
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, workerName);
            try (ResultSet rs = statement.executeQuery()) {
                if (!rs.next()) {
                    connection.commit();
                    return null;
                }

                ClaimedTask task = new ClaimedTask(
                        rs.getLong("id"),
                        rs.getString("task_type"),
                        rs.getInt("priority"),
                        rs.getInt("attempts"),
                        rs.getInt("max_attempts"),
                        rs.getTimestamp("created_at").toInstant()
                );
                connection.commit();
                return task;
            }
        } catch (SQLException ex) {
            connection.rollback();
            throw ex;
        } finally {
            connection.setAutoCommit(true);
        }
    }

    private void processTask(Connection connection, ClaimedTask task) throws SQLException, InterruptedException {
        int processingMs = ThreadLocalRandom.current().nextInt(minProcessingMs, maxProcessingMs + 1);
        Thread.sleep(processingMs);

        boolean success = ThreadLocalRandom.current().nextDouble() >= failureProbability;
        if (success) {
            markCompleted(connection, task);
        } else {
            handleFailure(connection, task, "Synthetic processing error after " + processingMs + " ms");
        }
    }

    private void markCompleted(Connection connection, ClaimedTask task) throws SQLException {
        String sql = """
                UPDATE tasks
                SET status = 'Completed',
                    finished_at = NOW(),
                    updated_at = NOW(),
                    last_error = NULL
                WHERE id = ?
                """;
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setLong(1, task.id());
            statement.executeUpdate();
        }

        Duration waiting = Duration.between(task.createdAt(), Instant.now());
        System.out.printf("[%s] %s completed task=%d type=%s priority=%d wait=%d ms%n",
                Instant.now(), workerName, task.id(), task.taskType(), task.priority(), waiting.toMillis());
    }

    private void handleFailure(Connection connection, ClaimedTask task, String error) throws SQLException {
        int newAttempts = task.attempts() + 1;
        if (newAttempts >= task.maxAttempts()) {
            String sql = """
                    UPDATE tasks
                    SET status = 'Failed',
                        attempts = ?,
                        finished_at = NOW(),
                        updated_at = NOW(),
                        last_error = ?
                    WHERE id = ?
                    """;
            try (PreparedStatement statement = connection.prepareStatement(sql)) {
                statement.setInt(1, newAttempts);
                statement.setString(2, error);
                statement.setLong(3, task.id());
                statement.executeUpdate();
            }
            System.out.printf("[%s] %s permanently failed task=%d after %d attempts%n",
                    Instant.now(), workerName, task.id(), newAttempts);
            return;
        }

        long delaySeconds = (long) retryBaseSeconds * (1L << Math.max(0, newAttempts - 1));
        String sql = """
                UPDATE tasks
                SET status = 'Ready',
                    attempts = ?,
                    scheduled_at = ?,
                    started_at = NULL,
                    updated_at = NOW(),
                    worker_name = NULL,
                    last_error = ?
                WHERE id = ?
                """;
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setInt(1, newAttempts);
            statement.setTimestamp(2, Timestamp.from(Instant.now().plusSeconds(delaySeconds)));
            statement.setString(3, error);
            statement.setLong(4, task.id());
            statement.executeUpdate();
        }
        System.out.printf("[%s] %s re-queued task=%d after error, attempts=%d, retry_in=%d sec%n",
                Instant.now(), workerName, task.id(), newAttempts, delaySeconds);
    }

    private void waitForSignal(PGConnection pgConnection) throws SQLException, InterruptedException {
        if (!notificationsEnabled) {
            Thread.sleep(waitTimeoutMs);
            return;
        }

        PGNotification[] notifications = pgConnection.getNotifications(waitTimeoutMs);
        if (notifications != null && notifications.length > 0) {
            return;
        }
    }

    private record ClaimedTask(long id, String taskType, int priority, int attempts, int maxAttempts, Instant createdAt) {
    }
}
