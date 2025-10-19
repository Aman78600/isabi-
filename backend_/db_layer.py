import os
import json
import uuid
from contextlib import contextmanager
from typing import Optional
from google.cloud.sql.connector import Connector
import pg8000

class DBLayer:
    def __init__(self):
        self._connector = Connector()
        self._instance = f"{os.getenv('GCP_PROJECT_ID')}:{os.getenv('GCP_LOCATION','us-central1')}:{os.getenv('GCP_DB_INSTANCE')}"
        self._db = os.getenv('GCP_DB_NAME')
        self._user = os.getenv('GCP_DB_USER')
        self._password = os.getenv('GCP_DB_PASSWORD')

    def _get_conn(self):
        return self._connector.connect(
            self._instance,
            "pg8000",
            user=self._user,
            password=self._password,
            db=self._db,
        )

    @contextmanager
    def transaction(self):
        conn = self._get_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def insert_product(self, conn, product_name: str, product_category: str, price: float, admin_id: str, admin_type: str):
        try:
            # Ensure a product_type exists or create a placeholder by name
            # Try find by name
            cur = conn.cursor()
            cur.execute("SELECT product_type_id FROM product_types WHERE type_name=%s", (product_category,))
            row = cur.fetchone()
            if row:
                product_type_id = row[0]
            else:
                cur.execute("INSERT INTO product_types (type_name, description) VALUES (%s,%s) RETURNING product_type_id", (product_category, None))
                product_type_id = cur.fetchone()[0]
            # Insert product
            try:
                admin_uuid = uuid.UUID(admin_id)
            except ValueError:
                # If not a valid UUID, create one from the string
                admin_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, admin_id)
            
            cur.execute(
                """
                INSERT INTO products (product_name, product_type_id, product_type_name, created_by_admin_id, admin_type, price)
                VALUES (%s,%s,%s,%s,%s,%s) RETURNING product_id
                """,
                (product_name, product_type_id, product_category, admin_uuid, admin_type, price)
            )
            return cur.fetchone()[0]
        except Exception as e:
            print(f"Database error in insert_product: {e}")
            raise

    def insert_ai_train_product(self, conn, product_id, product_name: str, product_category: str, suggestion_questions, product_vector_id: Optional[str], number_of_videos: int):
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO ai_train_products (product_id, product_name, product_category, product_vector_id, number_of_videos, suggestion_questions)
            VALUES (%s,%s,%s,%s,%s,%s)
            """,
            (product_id, product_name, product_category, product_vector_id, number_of_videos, json.dumps(suggestion_questions) if isinstance(suggestion_questions, (dict, list)) else suggestion_questions)
        )

    def update_ai_train_product(self, conn, product_id, product_vector_id: str, number_of_videos: int):
        cur = conn.cursor()
        cur.execute(
            "UPDATE ai_train_products SET product_vector_id=%s, number_of_videos=%s, updated_at=NOW() WHERE product_id=%s",
            (product_vector_id, number_of_videos, product_id)
        )

    def insert_ai_train_product_detail(self, conn, product_id, video_path: str, audio_path: str, text_path: str, pdf_path: str, lesson_title: str, lesson_order: int, metadata):
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO ai_train_product_details (product_id, video_path, audio_path, text_path, pdf_path, lesson_title, lesson_order, metadata)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (product_id, video_path, audio_path, text_path, pdf_path, lesson_title, lesson_order, json.dumps(metadata) if isinstance(metadata, (dict, list)) else metadata)
        )

    def insert_vector_metadata(self, conn, product_id, vector_index_name: str, content_type: str, source_file_path: str, metadata):
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO vector_metadata (product_id, vector_index_name, content_type, source_file_path, metadata)
            VALUES (%s,%s,%s,%s,%s)
            """,
            (product_id, vector_index_name, content_type, source_file_path, json.dumps(metadata) if isinstance(metadata, (dict, list)) else metadata)
        )

    def get_product_vectors(self, conn, product_ids: list):
        """Get vector metadata for specific product IDs"""
        cur = conn.cursor()
        placeholders = ','.join(['%s'] * len(product_ids))
        cur.execute(
            f"""
            SELECT vm.product_id, vm.vector_index_name, vm.content_type, vm.source_file_path, vm.metadata,
                   atp.product_name, atp.product_category
            FROM vector_metadata vm
            JOIN ai_train_products atp ON vm.product_id = atp.product_id
            WHERE vm.product_id IN ({placeholders})
            ORDER BY vm.product_id, vm.created_at
            """,
            product_ids
        )
        return cur.fetchall()

    def get_all_products(self, conn):
        """Get all AI training products"""
        cur = conn.cursor()
        cur.execute(
            """
            SELECT product_id, product_name, product_category, number_of_videos, 
                   product_vector_id, suggestion_questions, created_at
            FROM ai_train_products
            ORDER BY created_at DESC
            """
        )
        return cur.fetchall()

    # Digital Products methods
    def insert_digital_product(self, conn, product_id, product_name: str, product_category: str, 
                               product_location: str, product_size_mb: float, file_format: str, 
                               description: str = None):
        """Insert digital product details"""
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO digital_products (product_id, product_name, product_category, 
                                         product_location, product_size_mb, file_format)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (product_id, product_name, product_category, product_location, product_size_mb, file_format)
        )

    def get_all_digital_products(self, conn):
        """Get all digital products"""
        cur = conn.cursor()
        cur.execute(
            """
            SELECT dp.product_id, dp.product_name, dp.product_category, dp.product_location,
                   dp.product_size_mb, dp.file_format, dp.created_at, p.price
            FROM digital_products dp
            JOIN products p ON dp.product_id = p.product_id
            ORDER BY dp.created_at DESC
            """
        )
        return cur.fetchall()

    def get_digital_product_by_id(self, conn, product_id):
        """Get digital product by ID"""
        cur = conn.cursor()
        cur.execute(
            """
            SELECT dp.product_id, dp.product_name, dp.product_category, dp.product_location,
                   dp.product_size_mb, dp.file_format, dp.created_at, p.price
            FROM digital_products dp
            JOIN products p ON dp.product_id = p.product_id
            WHERE dp.product_id = %s
            """,
            (product_id,)
        )
        return cur.fetchone()

    # Authentication methods
    def get_super_admin_by_credentials(self, conn, email: str, password: str):
        """Get super admin by email and password"""
        cur = conn.cursor()
        cur.execute("SELECT admin_id, name FROM SUPER_ADMINS WHERE email = %s AND password = %s", 
                   (email, password))
        return cur.fetchone()

    def get_sub_admin_by_credentials(self, conn, email: str, password: str):
        """Get sub admin by email and password"""
        cur = conn.cursor()
        cur.execute("SELECT sub_admin_id, name FROM SUB_ADMINS WHERE email = %s AND password = %s", 
                   (email, password))
        return cur.fetchone()

    def is_super_admin(self, conn, user_id: str):
        """Check if user is super admin"""
        cur = conn.cursor()
        cur.execute("SELECT admin_id FROM SUPER_ADMINS WHERE admin_id = %s", (user_id,))
        return cur.fetchone() is not None

    def is_sub_admin(self, conn, user_id: str):
        """Check if user is sub admin"""
        cur = conn.cursor()
        cur.execute("SELECT sub_admin_id FROM SUB_ADMINS WHERE sub_admin_id = %s", (user_id,))
        return cur.fetchone() is not None

    def insert_super_admin(self, conn, name: str, email: str, password: str, phone: str = None):
        """Insert super admin"""
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO SUPER_ADMINS (name, email, password, phone)
            VALUES (%s, %s, %s, %s)
            RETURNING admin_id
        """, (name, email, password, phone))
        return cur.fetchone()[0]

    def insert_sub_admin(self, conn, name: str, created_by: str, email: str, phone_number: str, password: str):
        """Insert sub admin"""
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO SUB_ADMINS (name, created_by_super_admin_id, email, phone_number, password)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING sub_admin_id
        """, (name, created_by, email, phone_number, password))
        return cur.fetchone()[0]

    def get_table_data(self, conn, table_name: str):
        """Get all data from a table"""
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {table_name}")
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        data = [dict(zip(columns, row)) for row in rows]
        return data

    def get_super_admin_by_credentials(self, conn, email: str, password: str):
        """Get super admin by email and password"""
        cur = conn.cursor()
        cur.execute("SELECT admin_id, name FROM SUPER_ADMINS WHERE email = %s AND password = %s", (email, password))
        return cur.fetchone()

    def get_sub_admin_by_credentials(self, conn, email: str, password: str):
        """Get sub admin by email and password"""
        cur = conn.cursor()
        cur.execute("SELECT sub_admin_id, name FROM SUB_ADMINS WHERE email = %s AND password = %s", (email, password))
        return cur.fetchone()

    def is_super_admin(self, conn, admin_id: str):
        """Check if user is super admin"""
        cur = conn.cursor()
        cur.execute("SELECT admin_id FROM SUPER_ADMINS WHERE admin_id = %s", (admin_id,))
        return cur.fetchone() is not None

    def is_sub_admin(self, conn, admin_id: str):
        """Check if user is sub admin"""
        cur = conn.cursor()
        cur.execute("SELECT sub_admin_id FROM SUB_ADMINS WHERE sub_admin_id = %s", (admin_id,))
        return cur.fetchone() is not None

    def insert_super_admin(self, conn, name: str, email: str, password: str, phone: str = None):
        """Insert new super admin"""
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO SUPER_ADMINS (name, email, password, phone)
            VALUES (%s, %s, %s, %s)
            RETURNING admin_id
        """, (name, email, password, phone))
        return cur.fetchone()[0]

    def insert_sub_admin(self, conn, name: str, created_by_super_admin_id: str, email: str, phone_number: str, password: str):
        """Insert new sub admin"""
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO SUB_ADMINS (name, created_by_super_admin_id, email, phone_number, password)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING sub_admin_id
        """, (name, created_by_super_admin_id, email, phone_number, password))
        return cur.fetchone()[0]

    def get_table_data(self, conn, table_name: str):
        """Get all data from specified table"""
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {table_name}")
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in rows]
