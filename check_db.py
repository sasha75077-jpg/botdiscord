import sqlite3
conn = sqlite3.connect(r"C:\Users\User\Desktop\BOT Melancholia Now\bot.db")
cursor = conn.cursor()
cursor.execute("SELECT id, ts, discord_id, contract_type FROM contracts ORDER BY id DESC LIMIT 10")
for row in cursor.fetchall():
    print(row)
conn.close()
