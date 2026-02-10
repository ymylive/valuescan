#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/opt/valuescan/signal_monitor/valuescan.db')
c = conn.cursor()
c.execute('SELECT name FROM sqlite_master WHERE type="table"')
print('Tables:', [r[0] for r in c.fetchall()])
c.execute('SELECT * FROM messages ORDER BY id DESC LIMIT 10')
for row in c.fetchall():
    print(row)
conn.close()
