StockSense Fix 4 — Overview performance optimization

What changed
- The planning engine now groups sales rows by product/date once rather than repeatedly scanning the entire sales table for every product.
- Forecast/reorder results are cached in memory per user, keyed to the SQLite database/WAL file signature. A sales upload, product update, settings change, or other database write invalidates the cache automatically.
- Cached values are copied before being returned, so page rendering cannot mutate the stored plan.
- Cache size is bounded; this is a performance optimization only and does not change or delete SQLite data.

Install/run
1. Stop the existing Flask process with Ctrl+C.
2. Back up stocksense.db.
3. Extract this ZIP and copy the contents of the inner StockSense folder into your existing project folder, replacing source files.
4. Keep stocksense.db and all user data unchanged.
5. Run: python -m pip install -r requirements.txt
6. Run: python app.py
7. Refresh http://127.0.0.1:5000 and sign in if needed.

Expected behavior
- The first Overview visit after a database change still calculates forecasts, but should be faster on large datasets due to single-pass grouping.
- Reopening Overview or moving to another page that needs the same plan should be substantially faster until the database changes.
- After importing sales/products or changing planning settings, the next request recalculates to keep results current.

Validation
- Python syntax compilation passed for app.py, db.py, forecast.py and optimizer.py.
- Full Flask tests could not be run in the build environment because Flask is not installed there. Run the app locally and verify dashboard, sales upload, product edits and planning settings.
