import toml
from sqlalchemy import create_engine, text

def test_connection():
    print("🔍 Reading secrets.toml...")
    try:
        # Load secrets manually since we aren't running 'streamlit run'
        config = toml.load(".streamlit/secrets.toml")
        db_url = config["connections"]["database_url"]

        # Fix the postgres protocol if needed
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        print(f"✅ Found URL: {db_url[:25]}...") # Print first few chars to verify

        print("🔌 Attempting to connect...")
        engine = create_engine(db_url)
        connection = engine.connect()

        print("🚀 Connection Successful!")

        # Try to insert a dummy row
        print("📝 Attempting to write data...")
        # We use raw SQL for this test to be absolutely sure
        connection.execute(text("INSERT INTO users (username, email) VALUES ('TestUser', 'test@example.com')"))
        connection.commit()
        print("✅ Data written.")

        connection.close()

    except Exception as e:
        print("\n❌ FAILED:")
        print(e)

if __name__ == "__main__":
    test_connection()
