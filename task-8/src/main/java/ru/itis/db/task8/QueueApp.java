package ru.itis.db.task8;

import java.sql.SQLException;

public final class QueueApp {

    private QueueApp() {
    }

    public static void main(String[] args) throws Exception {
        if (args.length == 0) {
            printUsage();
            return;
        }

        DbConfig config = DbConfig.fromEnv();
        String mode = args[0];

        switch (mode) {
            case "producer" -> runProducer(config, args);
            case "worker" -> runWorker(config, args);
            default -> printUsage();
        }
    }

    private static void runProducer(DbConfig config, String[] args) throws SQLException, InterruptedException {
        int ratePerSecond = intArg(args, 1, envInt("TASK_RATE_PER_SECOND", 100));
        boolean notificationsEnabled = envBool("TASK_NOTIFY_ENABLED", true);
        System.out.printf("Starting producer with rate=%d tasks/sec, notifications=%s%n",
                ratePerSecond, notificationsEnabled);
        new ProducerService(config, ratePerSecond, notificationsEnabled).run();
    }

    private static void runWorker(DbConfig config, String[] args) throws SQLException, InterruptedException {
        String workerName = stringArg(args, 1, "worker-" + envInt("WORKER_ID", 1));
        int minProcessingMs = envInt("WORKER_MIN_PROCESSING_MS", 400);
        int maxProcessingMs = envInt("WORKER_MAX_PROCESSING_MS", 900);
        double failureProbability = envDouble("WORKER_FAILURE_PROBABILITY", 0.15);
        int retryBaseSeconds = envInt("TASK_RETRY_BASE_SECONDS", 50);
        boolean notificationsEnabled = envBool("TASK_NOTIFY_ENABLED", true);
        int waitTimeoutMs = envInt("WORKER_WAIT_TIMEOUT_MS", 1000);

        System.out.printf(
                "Starting worker=%s, processing=%d-%d ms, failureProbability=%.2f, retryBaseSeconds=%d, notifications=%s%n",
                workerName, minProcessingMs, maxProcessingMs, failureProbability, retryBaseSeconds, notificationsEnabled
        );

        new WorkerService(
                config,
                workerName,
                minProcessingMs,
                maxProcessingMs,
                failureProbability,
                retryBaseSeconds,
                notificationsEnabled,
                waitTimeoutMs
        ).run();
    }

    private static int intArg(String[] args, int index, int defaultValue) {
        if (args.length <= index) {
            return defaultValue;
        }
        return Integer.parseInt(args[index]);
    }

    private static String stringArg(String[] args, int index, String defaultValue) {
        if (args.length <= index || args[index].isBlank()) {
            return defaultValue;
        }
        return args[index];
    }

    private static int envInt(String key, int defaultValue) {
        String value = System.getenv(key);
        if (value == null || value.isBlank()) {
            return defaultValue;
        }
        return Integer.parseInt(value);
    }

    private static double envDouble(String key, double defaultValue) {
        String value = System.getenv(key);
        if (value == null || value.isBlank()) {
            return defaultValue;
        }
        return Double.parseDouble(value);
    }

    private static boolean envBool(String key, boolean defaultValue) {
        String value = System.getenv(key);
        if (value == null || value.isBlank()) {
            return defaultValue;
        }
        return Boolean.parseBoolean(value);
    }

    private static void printUsage() {
        System.out.println("""
                Usage:
                  mvn exec:java -Dexec.mainClass=ru.itis.db.task8.QueueApp -Dexec.args="producer 200"
                  mvn exec:java -Dexec.mainClass=ru.itis.db.task8.QueueApp -Dexec.args="worker worker-1"
                """);
    }
}
