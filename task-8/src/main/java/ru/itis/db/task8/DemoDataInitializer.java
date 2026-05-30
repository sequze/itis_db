package ru.itis.db.task8;

import java.sql.Connection;
import java.sql.Date;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

public final class DemoDataInitializer {

    private DemoDataInitializer() {
    }

    public static DemoContext ensureDemoData(Connection connection) throws SQLException {
        connection.setAutoCommit(false);
        try {
            int subscriptionId = ensureSubscription(connection);
            List<Integer> userIds = ensureUsers(connection, subscriptionId);
            int genreId = ensureGenre(connection);
            int artistId = ensureArtist(connection, userIds.get(0));
            int albumId = ensureAlbum(connection, artistId, genreId);
            List<Integer> trackIds = ensureTracks(connection, albumId, artistId, genreId);
            connection.commit();
            return new DemoContext(userIds, trackIds);
        } catch (SQLException ex) {
            connection.rollback();
            throw ex;
        } finally {
            connection.setAutoCommit(true);
        }
    }

    private static int ensureSubscription(Connection connection) throws SQLException {
        Integer existingId = findSingleId(connection, "SELECT id FROM subscription ORDER BY id LIMIT 1");
        if (existingId != null) {
            return existingId;
        }

        try (PreparedStatement statement = connection.prepareStatement(
                "INSERT INTO subscription(name, price, duration_months) VALUES ('Queue Demo', 0.00, 1) RETURNING id")) {
            try (ResultSet rs = statement.executeQuery()) {
                rs.next();
                return rs.getInt(1);
            }
        }
    }

    private static List<Integer> ensureUsers(Connection connection, int subscriptionId) throws SQLException {
        List<Integer> userIds = findIds(connection, "SELECT id FROM \"user\" ORDER BY id LIMIT 5");
        if (!userIds.isEmpty()) {
            return userIds;
        }

        List<Integer> created = new ArrayList<>();
        String sql = """
                INSERT INTO "user"(email, username, password_hash, country, date_joined, subscription_id)
                VALUES (?, ?, 'hash', 'RU', CURRENT_DATE, ?)
                RETURNING id
                """;
        for (int i = 1; i <= 5; i++) {
            try (PreparedStatement statement = connection.prepareStatement(sql)) {
                statement.setString(1, "queue-user-" + i + "@example.com");
                statement.setString(2, "queue_user_" + i);
                statement.setInt(3, subscriptionId);
                try (ResultSet rs = statement.executeQuery()) {
                    rs.next();
                    created.add(rs.getInt(1));
                }
            }
        }
        return created;
    }

    private static int ensureGenre(Connection connection) throws SQLException {
        Integer existingId = findSingleId(connection, "SELECT id FROM genre ORDER BY id LIMIT 1");
        if (existingId != null) {
            return existingId;
        }

        try (PreparedStatement statement = connection.prepareStatement(
                "INSERT INTO genre(name, description, is_active) VALUES ('queue-demo', 'Queue demo genre', TRUE) RETURNING id")) {
            try (ResultSet rs = statement.executeQuery()) {
                rs.next();
                return rs.getInt(1);
            }
        }
    }

    private static int ensureArtist(Connection connection, int userId) throws SQLException {
        Integer existingId = findSingleId(connection, "SELECT id FROM artist ORDER BY id LIMIT 1");
        if (existingId != null) {
            return existingId;
        }

        try (PreparedStatement statement = connection.prepareStatement(
                "INSERT INTO artist(name, country, description, user_id, start_year) " +
                        "VALUES ('Queue Artist', 'RU', 'Synthetic demo artist', ?, 2020) RETURNING id")) {
            statement.setInt(1, userId);
            try (ResultSet rs = statement.executeQuery()) {
                rs.next();
                return rs.getInt(1);
            }
        }
    }

    private static int ensureAlbum(Connection connection, int artistId, int genreId) throws SQLException {
        Integer existingId = findSingleId(connection, "SELECT id FROM album ORDER BY id LIMIT 1");
        if (existingId != null) {
            return existingId;
        }

        try (PreparedStatement statement = connection.prepareStatement(
                "INSERT INTO album(title, release_date, artist_id, genre_id) VALUES ('Queue Album', ?, ?, ?) RETURNING id")) {
            statement.setDate(1, Date.valueOf("2025-01-01"));
            statement.setInt(2, artistId);
            statement.setInt(3, genreId);
            try (ResultSet rs = statement.executeQuery()) {
                rs.next();
                return rs.getInt(1);
            }
        }
    }

    private static List<Integer> ensureTracks(Connection connection, int albumId, int artistId, int genreId)
            throws SQLException {
        List<Integer> trackIds = findIds(connection, "SELECT id FROM track ORDER BY id LIMIT 10");
        if (!trackIds.isEmpty()) {
            return trackIds;
        }

        List<Integer> created = new ArrayList<>();
        String sql = """
                INSERT INTO track(title, duration_seconds, album_id, artist_id, genre_id)
                VALUES (?, ?, ?, ?, ?)
                RETURNING id
                """;
        for (int i = 1; i <= 10; i++) {
            try (PreparedStatement statement = connection.prepareStatement(sql)) {
                statement.setString(1, "Queue Track " + i);
                statement.setInt(2, ThreadLocalRandom.current().nextInt(120, 300));
                statement.setInt(3, albumId);
                statement.setInt(4, artistId);
                statement.setInt(5, genreId);
                try (ResultSet rs = statement.executeQuery()) {
                    rs.next();
                    created.add(rs.getInt(1));
                }
            }
        }
        return created;
    }

    private static Integer findSingleId(Connection connection, String sql) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(sql);
             ResultSet rs = statement.executeQuery()) {
            if (rs.next()) {
                return rs.getInt(1);
            }
            return null;
        }
    }

    private static List<Integer> findIds(Connection connection, String sql) throws SQLException {
        List<Integer> ids = new ArrayList<>();
        try (PreparedStatement statement = connection.prepareStatement(sql);
             ResultSet rs = statement.executeQuery()) {
            while (rs.next()) {
                ids.add(rs.getInt(1));
            }
        }
        return ids;
    }

    public record DemoContext(List<Integer> userIds, List<Integer> trackIds) {
        public int randomUserId() {
            return userIds.get(ThreadLocalRandom.current().nextInt(userIds.size()));
        }

        public int randomTrackId() {
            return trackIds.get(ThreadLocalRandom.current().nextInt(trackIds.size()));
        }
    }
}
