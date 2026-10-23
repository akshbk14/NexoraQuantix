StockSense frontend fix bundle
==============================

This bundle includes the supplied Python backend files plus the missing Flask frontend:
- templates/index.html
- templates/product.html
- static/style.css

Run locally:
1. Extract the entire ZIP into a folder.
2. Open that extracted folder in VS Code/Cursor.
3. Install dependencies if needed:
   python -m pip install -r requirements.txt
4. Run:
   python app.py
5. Open http://127.0.0.1:5000
6. Click "Load demo data" to populate the local database with synthetic data.

Important:
- Demo data is synthetic, not real store measurements.
- The CSS uses a Google Fonts import as an optional enhancement; the UI has fallback fonts and remains styled offline.
- Keep all .py files together with templates/ and static/.
