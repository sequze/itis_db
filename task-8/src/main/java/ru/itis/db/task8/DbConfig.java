package ru.itis.db.task8;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.util.Locale;

public record DbConfig(String host, int port, String database, String user, String password) {

    public static DbConfig fromEnv() {
        String host = env("DB_HOST", "localhost");
        int port = Integer.parseInt(env("DB_PORT", "5432"));
        String database = env("POSTGRES_DB", "music");
        String user = env("DB_USER", env("POSTGRES_USER", "app"));
        String password = env("DB_PASSWORD", env("POSTGRES_PASSWORD", "app_pass"));
        return new DbConfig(host, port, database, user, password);
    }

    public Connection open() throws SQLException {
        String url = String.format(Locale.ROOT, "jdbc:postgresql://%s:%d/%s", host, port, database);
        return DriverManager.getConnection(url, user, password);
    }

    private static String env(String key, String defaultValue) {
        String value = System.getenv(key);
        if (value == null || value.isBlank()) {
            return defaultValue;
        }
        return value;
    }
}
