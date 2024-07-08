from datetime import datetime
from typing import List, Dict

import asyncpg
from environs import Env

from config import logger


class Database:
    def __init__(self):
        self.env = Env()
        self.env.read_env(path='config/.env')

        self.user = self.env.str('DB_USER')
        self.password = self.env.str('DB_PASSWORD')
        self.host = self.env.str('DB_HOST')
        self.db_name = self.env.str('DB_NAME')
        self.db_port = self.env.str('DB_PORT')
        self.pool = None

    async def create_pool(self):
        try:
            self.pool = await asyncpg.create_pool(
                user=self.user,
                password=self.password,
                host=self.host,
                database=self.db_name,
                port=self.db_port,
            )

        except (Exception, asyncpg.PostgresError) as error:
            logger.error("Error while creating connection pool", error)
            print(error)

    async def close_pool(self):
        if self.pool:
            await self.pool.close()

    async def execute_query(self, query, *args):
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query, *args)
        except (Exception, asyncpg.PostgresError) as error:
            print("Error while executing query", error)

    async def fetch_row(self, query, *args):
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetchrow(query, *args)
        except (Exception, asyncpg.PostgresError) as error:
            print("Error while fetching row", error)

    async def fetch_all(self, query, *args):
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetch(query, *args)
        except (Exception, asyncpg.PostgresError) as error:
            logger.error("Error while fetching all", error)

    async def db_start(self) -> None:
        """
        Initializes the connection to the database and creates the tables if they do not exist.
        """
        try:
            await self.create_pool()

            await self.execute_query("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    balance INTEGER DEFAULT 0,
                    promo_codes TEXT DEFAULT ''
                )
            """)

            await self.execute_query("""
                            CREATE TABLE IF NOT EXISTS bot_settings (
                                user_id BIGINT PRIMARY KEY,
                                photo_path TEXT,
                                main_text TEXT,
                                game_search_text TEXT
                            )
                        """)

            await self.execute_query("""
                                       CREATE TABLE IF NOT EXISTS promo_codes (
                                           code TEXT PRIMARY KEY,
                                           value INTEGER
                                       )
                                   """)

            await self.execute_query("""
                                       CREATE TABLE IF NOT EXISTS reviews (
                                           g_id BIGINT,
                                           rev_id BIGINT PRIMARY KEY,
                                           from_username TEXT,
                                           date TEXT, 
                                           rev_text TEXT
                                       )
                                    """)

            await self.execute_query("""
                                        CREATE TABLE IF NOT EXISTS user_states (
                                            user_id BIGINT PRIMARY KEY,
                                            state VARCHAR(255),
                                            last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                        );
            """)

            logger.info('connected to database')

        except (Exception, asyncpg.PostgresError) as error:
            logger.error("Error while connecting to DB", error)

    async def set_user_state(self, user_id: int, state: str):
        user_id = int(user_id)
        query = """
        INSERT INTO user_states (user_id, state) VALUES ($1, $2)
        ON CONFLICT (user_id) DO UPDATE SET state = EXCLUDED.state, last_update = CURRENT_TIMESTAMP;
        """
        await self.execute_query(query, user_id, state)
        logger.info(f'State updated for user {user_id} to {state}')

    async def check_user_state(self, user_id: int, state_to_check: str):
        current_state = await self.get_user_state(user_id)
        print(current_state)
        return current_state == state_to_check

    async def get_user_state(self, user_id: int):
        query = """
        SELECT state FROM user_states WHERE user_id = $1;
        """
        result = await self.fetch_row(query, int(user_id))
        if result:
            return result['state']
        return None

    async def get_reviews_for_g_id(self, g_id: int) -> List[Dict[str, str]]:
        try:
            query = """
                SELECT rev_id, from_username, date, rev_text
                FROM reviews
                WHERE g_id = $1
            """
            reviews = await self.fetch_all(query, g_id)
            return [
                {
                    'rev_id': str(review['rev_id']),
                    'from_username': review['from_username'],
                    'date': review['date'],
                    'rev_text': review['rev_text']
                }
                for review in reviews
            ]
        except Exception as error:
            print("Error while fetching reviews for g_id:", error)
            return []

    async def write_bot_settings(self, user_id: int, photo_path: str, main_text: str, game_search_text: str) -> None:
        try:
            query = """
                INSERT INTO bot_settings (user_id, photo_path, main_text, game_search_text)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id)
                DO UPDATE SET photo_path = $2, main_text = $3, game_search_text = $4
            """
            await self.execute_query(query, user_id, photo_path, main_text, game_search_text)
        except Exception as error:
            logger.error("Error while writing bot settings:", error)

    async def get_user_balance(self, user_id: int, girl=None) -> int:
        try:
            if girl:
                query = "SELECT balance FROM girls WHERE user_id = $1"
            else:
                query = "SELECT balance FROM users WHERE user_id = $1"
            result = await self.fetch_row(query, user_id)
            return result['balance'] if result else 0
        except (Exception, asyncpg.PostgresError) as error:
            print("Error while getting user balance:", error)
            return 0

    async def get_all_users(self):
        try:
            users = await self.fetch_all("""
            SELECT * FROM users
            """)
            return users
        except (Exception, asyncpg.PostgresError) as error:
            logger.error(f'Error while fetching all users {error}')

    async def add_user(self, user_id: int, username: str):
        try:
            await self.execute_query("""
                INSERT INTO users (user_id, username)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE SET
                    username = EXCLUDED.username
            """, user_id, username)
        except (Exception, asyncpg.PostgresError) as error:
            logger.error(f"Error while adding user {user_id} to DB", error)

    async def top_up_balance(self, user_id: int, amount: int) -> None:
        try:
            current_balance = await self.get_user_balance(user_id)
            new_balance = current_balance + amount
            await self.execute_query("""
                UPDATE users 
                SET balance = $1 
                WHERE user_id = $2
            """, new_balance, user_id)
            logger.info(f"User {user_id} balance topped up by {amount}. New balance: {new_balance}")
        except (Exception, asyncpg.PostgresError) as error:
            logger.error(f"Error while topping up balance for user {user_id}", error)

    async def top_up_girl_balance(self, girl_id: int, amount: int) -> None:
        try:
            current_balance = await self.get_user_balance(girl_id, girl=True)
            new_balance = current_balance + amount
            await self.execute_query("""
                UPDATE girls 
                SET balance = $1 
                WHERE user_id = $2
            """, new_balance, girl_id)
            logger.info(f"Girl {girl_id} balance topped up by {amount}. New balance: {new_balance}")
        except (Exception, asyncpg.PostgresError) as error:
            logger.error(f"Error while topping up girl balance for girl {girl_id}", error)

    async def withdraw_from_balance(self, user_id: int, amount: int) -> None:
        try:
            current_balance = await self.get_user_balance(user_id)

            # Проверка, достаточно ли средств на балансе для снятия
            if current_balance >= amount:
                new_balance = current_balance - amount
                await self.execute_query("""
                    UPDATE users 
                    SET balance = $1 
                    WHERE user_id = $2
                """, new_balance, user_id)
                logger.info(f"User {user_id} balance withdrawn by {amount}. New balance: {new_balance}")
            else:
                # Недостаточно средств для снятия
                logger.error(f"Insufficient funds to withdraw {amount} for user {user_id}. Current balance: {current_balance}")
        except (Exception, asyncpg.PostgresError) as error:
            logger.error(f"Error while topping up girl balance for girl {user_id}", error)

    async def get_girls_by_game(self, game_name: str):
        try:
            query = """
                SELECT * FROM girls
                WHERE games LIKE '%' || $1 || '%'
            """
            return await self.fetch_all(query, game_name)
        except (Exception, asyncpg.PostgresError) as error:
            logger.error("Error while getting girls by game:", error)
            return []

    async def get_all_girls(self):
        try:
            query = """
                SELECT * FROM girls
            """
            return await self.fetch_all(query)
        except (Exception, asyncpg.PostgresError) as error:
            logger.error("Error while getting girls:", error)
            return []

    async def get_girls_by_id(self, g_id: int):
        try:
            query = """
                SELECT * FROM girls
                WHERE user_id = $1
            """
            return await self.fetch_all(query, g_id)
        except (Exception, asyncpg.PostgresError) as error:
            logger.error("Error while getting girls by id:", error)
            return []

    async def add_promo_code(self, code: str, value: int):
        query = """
            INSERT INTO promo_codes (code, value)
            VALUES ($1, $2)
            ON CONFLICT (code) DO UPDATE SET
                code = EXCLUDED.code,
                value = EXCLUDED.value
        """
        try:
            await self.execute_query(query, code, value)
            print("Promo code added successfully.")
        except Exception as e:
            print(f"Failed to add promo code: {e}")

    async def remove_promo_code(self, code: str):
        query = "DELETE FROM promo_codes WHERE code = $1"
        try:
            await self.execute_query(query, code)
            print("Promo code removed successfully.")
        except Exception as e:
            print(f"Failed to remove promo code: {e}")

    async def get_all_promo(self):
        query = "SELECT * FROM promo_codes"
        try:
            codes = await self.fetch_all(query)
            logger.info('promo codes executed')
            return codes
        except Exception as e:
            print(f"Failed to execute pc's: {e}")

    async def get_user_promo_codes(self, user_id: int) -> str:
        query = "SELECT promo_codes FROM users WHERE user_id = $1"
        row = await self.fetch_row(query, user_id)
        if row:
            return row['promo_codes']
        else:
            return ""

    async def add_promo_code_to_user(self, user_id: int, new_code: str) -> None:
        current_codes = await self.get_user_promo_codes(user_id)
        if current_codes and new_code not in current_codes:
            # There are already some promo codes present, append the new one
            new_codes = f"{current_codes},{new_code}"
        elif new_code in current_codes:
            raise Exception('code already in current codes')
            # No promo codes present yet, start a new list
        else:
            new_codes = new_code
        # Update the user's promo codes in the database
        query = "UPDATE users SET promo_codes = $1 WHERE user_id = $2"
        try:
            await self.execute_query(query, new_codes, user_id)
            logger.info(f"Added new promo code {new_code} for user {user_id}. Updated promo codes: {new_codes}")
        except (Exception, asyncpg.PostgresError) as error:
            logger.error(f"Error while adding promo code {new_code} for user {user_id}", error)

    async def add_review(self, g_id: int, rev_id: int, from_username: str, rev_text: str) -> None:
        """
        Adds a review to the reviews table with the current date.

        :param g_id: The group ID associated with the review.
        :param rev_id: The unique review ID.
        :param from_username: The username of the reviewer.
        :param rev_text: The text of the review.
        """
        try:
            # Get the current date in the dd/mm/yy format
            current_date = datetime.now().strftime("%d/%m/%y")

            query = """
                INSERT INTO reviews (g_id, rev_id, from_username, date, rev_text)
                VALUES ($1, $2, $3, $4, $5)
            """
            await self.execute_query(query, g_id, rev_id, from_username, current_date, rev_text)
            logger.info("Review added successfully with current date")
        except (Exception, asyncpg.PostgresError) as error:
            logger.error("Error while adding review to DB", error)

    async def delete_review(self, review_id: int) -> None:
        query = "DELETE FROM reviews WHERE rev_id = $1;"
        try:
            await self.execute_query(query, review_id)
            logger.info(f"Review deleted. Id:{review_id}.")
        except Exception as e:
            logger.error(f"Error while deleting review {e}")

    async def get_shift_status(self, user_id: int):
        try:
            result = await self.fetch_row(
                "SELECT * FROM girl_shift WHERE user_id = $1", user_id)
            if result:
                return result
            else:
                return "User not found"
        except (Exception, asyncpg.PostgresError) as error:
            logger.error("Error retrieving shift status", error)
            return str(error)

    async def get_services_by_user_id(self, user_id: int):
        query = """
            SELECT user_id, username, service_name, price, s_id
            FROM g_services
            WHERE user_id = $1
        """
        try:
            services = await self.fetch_all(query, user_id)
            return services
        except (Exception, asyncpg.PostgresError) as error:
            logger.error(f"Error while getting services for user_id '{user_id}': {error}")
            return []

    async def get_service_name_by_s_id(self, s_id: int):
        query = """
            SELECT service_name
            FROM g_services
            WHERE s_id = $1
        """
        try:
            result = await self.fetch_row(query, s_id)
            return result['service_name'] if result else None
        except (Exception, asyncpg.PostgresError) as error:
            logger.error(f"Error while getting service name for s_id '{s_id}': {error}")
            return None


db = Database()
