DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS experiences;
DROP TABLE IF EXISTS saved_experiences;
DROP TABLE IF EXISTS experience_photos;
DROP TABLE IF EXISTS experience_ratings;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    location TEXT,
    latitude REAL,
    longitude REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE experiences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    location TEXT NOT NULL,
    city TEXT NOT NULL,
    country TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    date_visited DATE NOT NULL,
    budget_category TEXT CHECK(budget_category IN ('budget', 'moderate', 'luxury')),
    duration TEXT,
    best_season TEXT,
    external_links TEXT,
    tips TEXT,
    user_id INTEGER NOT NULL,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE experience_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experience_id INTEGER NOT NULL,
    photo_url TEXT NOT NULL,
    caption TEXT,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (experience_id) REFERENCES experiences (id)
);

CREATE TABLE experience_ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experience_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    FOREIGN KEY (experience_id) REFERENCES experiences (id)
);

CREATE TABLE saved_experiences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    experience_id INTEGER NOT NULL,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (experience_id) REFERENCES experiences (id),
    UNIQUE(user_id, experience_id)
);
