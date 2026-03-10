import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

def copy_csv_to_db(engine, file_path, table_name):
    try: 
        with engine.connect() as conn:
            conn.execute(text(f"TRUNCATE TABLE {table_name} CASCADE;"))
            conn.commit()
            print(f"Truncated {table_name}!")

        chunk_size = 10000
        for chunk in pd.read_csv(file_path, chunksize=chunk_size):
            chunk.to_sql(table_name, engine, if_exists='append', index=False)
        
        print(f"Successfully loaded {table_name}!\n")
    except Exception as e:
        print(f"Error loading the {table_name}: {e}")

def to_datetime_conversion(engine):
    to_timestamp = [
        "ALTER TABLE orders ALTER COLUMN order_purchase_timestamp TYPE TIMESTAMP USING order_purchase_timestamp::timestamp;",
        "ALTER TABLE orders ALTER COLUMN order_approved_at TYPE TIMESTAMP USING order_approved_at::timestamp;",
        "ALTER TABLE orders ALTER COLUMN order_delivered_carrier_date TYPE TIMESTAMP USING order_delivered_carrier_date::timestamp;",
        "ALTER TABLE orders ALTER COLUMN order_delivered_customer_date TYPE TIMESTAMP USING order_delivered_customer_date::timestamp;",
        "ALTER TABLE orders ALTER COLUMN order_estimated_delivery_date TYPE TIMESTAMP USING order_estimated_delivery_date::timestamp;",

        "ALTER TABLE order_items ALTER COLUMN shipping_limit_date TYPE TIMESTAMP USING shipping_limit_date::timestamp;",

        "ALTER TABLE order_reviews ALTER COLUMN review_creation_date TYPE TIMESTAMP USING review_creation_date::timestamp;",
        "ALTER TABLE order_reviews ALTER COLUMN review_answer_timestamp TYPE TIMESTAMP USING review_answer_timestamp::timestamp;",
    ]

    with engine.connect() as conn:
        print("Converting Timestamp Columns....")
        for sql in to_timestamp:
            try: 
                conn.execute(text(sql))
                conn.commit()
            except Exception as e:
                print(f"Error on conversion: {e}")

if __name__  == "__main__":
    dbname=os.getenv('DB_NAME')
    user=os.getenv('DB_USER')
    password=os.getenv('DB_PASS')
    host=os.getenv('DB_HOST')
    port=os.getenv('DB_PORT')

    engine = create_engine(
        f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
)
    root_path = os.getcwd()
    data_path = os.path.join(root_path, 'data/raw_data_used')
    
    files_to_load = [
        ('1_customers_dataset.csv', 'customers'),
        ('2_products_dataset.csv', 'products'),
        ('3_orders_dataset.csv', 'orders'),
        ('4_order_items_dataset.csv', 'order_items'),
        ('5_order_payments_dataset.csv', 'order_payments'),
        ('6_order_reviews_dataset.csv', 'order_reviews'),
        ('7_product_category_name_translation.csv', 'product_category_name_translation')
    ]

    for filename, table in files_to_load:
        print(f"Starting load for {table}...")
        full_path = os.path.join(data_path, filename)
        if os.path.exists(full_path):
            copy_csv_to_db(engine, full_path, table)
        else:
            print(f"⚠️ Warning: {filename} not found. Skipping {table}.")
    to_datetime_conversion(engine)