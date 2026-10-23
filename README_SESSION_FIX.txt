StockSense session / SQLite foreign-key fix

If the browser has a stale login cookie for a user ID that is not in the current local database, protected pages now clear that session and redirect to Sign In. The settings function also checks that the user exists before inserting default settings.

Run from this folder with: python app.py
No virtual environment is required. Keep your stocksense.db file if you need to preserve existing account and project data.
