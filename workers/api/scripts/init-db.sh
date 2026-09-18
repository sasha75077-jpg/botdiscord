#!/bin/bash

# Script to create all tables in D1 database
# Run: bash scripts/init-db.sh

echo "Creating tables in D1 database..."

# Guilds table
npx wrangler d1 execute melancholia-db --remote --command="CREATE TABLE IF NOT EXISTS guilds (guild_id TEXT PRIMARY KEY, guild_name TEXT NOT NULL, is_active INTEGER DEFAULT 1, joined_at DATETIME DEFAULT CURRENT_TIMESTAMP, left_at DATETIME);"

# Guild settings table
npx wrangler d1 execute melancholia-db --remote --command="CREATE TABLE IF NOT EXISTS guild_settings (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT NOT NULL, setting_key TEXT NOT NULL, setting_value TEXT, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE, UNIQUE(guild_id, setting_key));"

# Guild modules table
npx wrangler d1 execute melancholia-db --remote --command="CREATE TABLE IF NOT EXISTS guild_modules (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT NOT NULL, module_name TEXT NOT NULL, is_enabled INTEGER DEFAULT 1, FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE, UNIQUE(guild_id, module_name));"

# Permissions table
npx wrangler d1 execute melancholia-db --remote --command="CREATE TABLE IF NOT EXISTS permissions (id INTEGER PRIMARY KEY AUTOINCREMENT, discord_id TEXT NOT NULL, guild_id TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('owner', 'admin', 'recruiter', 'user')), assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP, assigned_by TEXT, FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE, UNIQUE(discord_id, guild_id));"

# Users table
npx wrangler d1 execute melancholia-db --remote --command="CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, discord_id TEXT NOT NULL, guild_id TEXT NOT NULL, discord_username TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE, UNIQUE(discord_id, guild_id));"

# Contracts table
npx wrangler d1 execute melancholia-db --remote --command="CREATE TABLE IF NOT EXISTS contracts (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT NOT NULL, discord_id TEXT NOT NULL, discord_username TEXT, contract_type TEXT NOT NULL, nickname TEXT NOT NULL, price REAL, status TEXT DEFAULT 'pending', screenshot_url TEXT, admin_notes TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE);"

# Applications table
npx wrangler d1 execute melancholia-db --remote --command="CREATE TABLE IF NOT EXISTS applications (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT NOT NULL, discord_id TEXT NOT NULL, discord_username TEXT, age INTEGER, experience TEXT, playtime TEXT, reason TEXT, status TEXT DEFAULT 'pending', admin_notes TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE);"

# Create indexes
npx wrangler d1 execute melancholia-db --remote --command="CREATE INDEX IF NOT EXISTS idx_contracts_guild_status ON contracts(guild_id, status);"
npx wrangler d1 execute melancholia-db --remote --command="CREATE INDEX IF NOT EXISTS idx_contracts_discord_id ON contracts(discord_id);"
npx wrangler d1 execute melancholia-db --remote --command="CREATE INDEX IF NOT EXISTS idx_permissions_guild ON permissions(guild_id);"

echo "✅ All tables created successfully!"
