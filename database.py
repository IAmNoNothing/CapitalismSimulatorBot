import sqlite3


class Database:
    def __init__(self, database="bot.db") -> None:
        self.conn = sqlite3.connect(database)
        self.cursor = self.conn.cursor()

        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0
        )
        ''')

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventories (
            user_id INTEGER,
            item TEXT,
            amount INTEGER,
            PRIMARY KEY (user_id, item),
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS auction (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item TEXT,
            amount INTEGER,
            price INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')

        self.conn.commit()

    def update_user_ids(self, user_ids: list[int]):
        for user_id in user_ids:
            self.cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        self.conn.commit()

    def get_balance(self, user_id: int) -> tuple[int, str | None]:
        self.cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        if result is None:
            return 0, "Користувача не знайдено, спробуйте оновити базу даних (!update)."
        return result[0], None

    def create_item(self, user_id: int, item: str, amount: int):
        self.cursor.execute('''
            INSERT INTO inventories (user_id, item, amount)
            VALUES (?, ?, ?)
        ''', (user_id, item, amount))
        self.conn.commit()

    def delete_item(self, user_id: int, item: str):
        self.cursor.execute('''
            DELETE FROM inventories
            WHERE user_id = ? AND item = ?
        ''', (user_id, item))
        self.conn.commit()

    def get_inventory(self, user_id: int) -> list[tuple[str, int]]:
        self.cursor.execute('''
            SELECT item, amount
            FROM inventories
            WHERE user_id = ?
        ''', (user_id,))
        return self.cursor.fetchall()

    def get_auction(self, seller_id = None, item=None, min_price=None, max_price=None, min_amount=None) -> list[tuple[str, int, int]]:
        query = "SELECT * FROM auction WHERE 1=1"
        params = []

        if seller_id is not None:
            query += " AND seller_id = ?"
            params.append(seller_id)

        if item is not None:
            query += " AND item LIKE ?"
            params.append(f"'%{item}%'")

        if min_price is not None:
            query += " AND price >= ?"
            params.append(min_price)

        if max_price is not None:
            query += " AND price <= ?"
            params.append(max_price)

        if min_amount is not None:
            query += " AND amount >= ?"
            params.append(min_amount)

        query += " LIMIT 10"

        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def get_user_item_count(self, user_id: int, item: str) -> int:
        self.cursor.execute("SELECT amount FROM inventories WHERE user_id = ? AND item = ?", (user_id, item))
        result = self.cursor.fetchone()
        return result[0] if result is not None else 0

    def put_item_on_auction(self, user_id: int, item: str, amount: int, price: int) -> None:
        self.cursor.execute("INSERT INTO auction (user_id, item, amount, price) VALUES (?, ?, ?, ?)", (user_id, item, amount, price))
        self.cursor.execute("UPDATE inventories SET amount = amount - ? WHERE user_id = ? AND item = ?", (amount, user_id, item))
        self.cursor.execute("DELETE FROM inventories WHERE amount <= 0")
        self.conn.commit()

    def get_deal(self, auction_id):
        return self.cursor.execute("SELECT * FROM auction WHERE id = ?", (auction_id,))


    def buy_from_auction(self, buyer_id, auction_id, amount):
        deal = self.get_deal(auction_id)

        if deal is None:
            return "Лоту не існує."

        deal = deal.fetchone()

        if deal is None:
            return "Лоту не існує."

        if deal[1] == buyer_id:
            return "Ви не можете купити в самого себе."

        if amount > deal[3]:
            return "В лоті немає стільки предметів."

        if deal[4] * amount > self.get_balance(buyer_id)[0]:
            return f"Недостатньо коштів(потрібно {deal[4] * amount}, але в вас {self.get_balance(buyer_id)[0]})."

        # take money from buyer and give to seller
        self.cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (deal[4] * amount, buyer_id))
        self.cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (deal[4] * amount, deal[1]))

        # give item to buyer
        self.cursor.execute("UPDATE inventories SET amount = amount + ? WHERE user_id = ? AND item = ?", (amount, buyer_id, deal[2]))

        # delete item from auction
        self.cursor.execute("UPDATE auction SET amount = amount - ? WHERE id = ?", (amount, auction_id))
        self.cursor.execute("DELETE FROM auction WHERE amount <= 0")

        self.conn.commit()

        return f"Ви купили {amount} шт. {deal[2]} за {deal[4]} кредитів за штуку."

    def insert_liquidity(self, amount) -> None:
        user_count = self.cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]

        if user_count == 0:
            return

        add_balance = amount // user_count

        self.cursor.execute("UPDATE users SET balance = balance + ?", (add_balance,))

        self.conn.commit()

    def get_liquidity(self):
        return self.cursor.execute("SELECT SUM(balance), COUNT(*) FROM users").fetchone()