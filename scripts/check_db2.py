#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/opt/valuescan/signal_monitor/valuescan.db')
c = conn.cursor()
c.execute('SELECT * FROM processed_messages ORDER BY rowid DESC LIMIT 10')
rows = c.fetchall()
print(f"Found {len(rows)} records")
for row in rows:
    print(row)
conn.close()
