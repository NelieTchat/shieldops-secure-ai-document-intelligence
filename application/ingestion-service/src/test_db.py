import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="shieldops",
    user="postgres",
    password="localdevpassword",
)

print("Connected to Postgres!")

cur = conn.cursor()
cur.execute("SELECT version();")
print("Postgres version:", cur.fetchone())

cur.close()
conn.close()
