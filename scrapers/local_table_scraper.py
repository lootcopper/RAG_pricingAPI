from bs4 import BeautifulSoup
import sqlite3

with open("sample_together_pricing.html") as f:
    soup = BeautifulSoup(f, "html.parser")


table = soup.find("table")
if not table:
    print("No table found.")
    exit()

rows = table.find_all("tr")[1:]  # skip header


data = []
for row in rows:
    cols = row.find_all("td")
    model = cols[0].text.strip()
    input = float(cols[1].text.strip().replace("$", ""))
    output = float(cols[2].text.strip().replace("$", ""))
    provider = "Mistral" if "Mistral" in model else "DeepSeek"

    data.append((provider, model, input, output))


conn = sqlite3.connect("llm_pricing.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS llm_pricing (
    provider TEXT,
    model TEXT,
    input REAL,
    output REAL
)
""")

c.executemany("INSERT INTO llm_pricing VALUES (?, ?, ?, ?)", data)
conn.commit()
conn.close()

print("Scraped and saved:")
for item in data:
    print(item)
