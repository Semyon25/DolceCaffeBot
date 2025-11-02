#!/bin/bash

DB_FILE="../dolce_db.db"

sqlite3 "$DB_FILE" <<'SQL'
CREATE TABLE IF NOT EXISTS "subscriptions" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "user_id" NUMERIC NOT NULL UNIQUE,
    "start_date" TEXT NOT NULL,
    "end_date" TEXT NOT NULL,
    "sub_name" TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS "subscription_codes" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "user_id" NUMERIC NOT NULL,
    "subscription_id" INTEGER NOT NULL,
    "code" TEXT NOT NULL,
    "used_at" TEXT
);
SQL

echo "✅ Таблицы успешно созданы в $DB_FILE"
