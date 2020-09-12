DROP TABLE IF EXISTS video;

CREATE TABLE video (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    ext TEXT NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);