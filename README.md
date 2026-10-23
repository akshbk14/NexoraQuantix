# StockSense — Team Nexora

Inventory intelligence for small retailers: demand estimation, reorder planning, sales analytics, stockout/overstock/expiry signals, and optional camera-based object detection.

## Technology stack
- Frontend: HTML5, CSS3, vanilla JavaScript, Jinja templates
- Backend: Python + Flask
- Database: SQLite
- Analytics: Pandas + NumPy
- Interactive charts: Plotly.js
- Optional computer vision: OpenCV + Ultralytics YOLO

## Run on Windows PowerShell
1. Install Python 3.11 or 3.12 (recommended).
2. Open PowerShell in this folder.
3. Install dependencies directly in your current Python installation (no virtual environment required):
   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```
4. Start the application:
   ```powershell
   python app.py
   ```
5. Open `http://127.0.0.1:5000` and create an account.

The SQLite database is created automatically on first run. This distribution intentionally excludes any prior local database and user accounts. Demo data is synthetic.

## Camera scanning
Camera dependencies are included in `requirements.txt`. If you installed the base requirements before this version, run `python -m pip install -r requirements.txt` again. On first detection, Ultralytics may need to download the default `yolov8n.pt` model. Internet access may be needed for that download. Set `STOCKSENSE_YOLO_MODEL` to a local compatible model path if you have one. Camera access requires localhost or HTTPS in a supported browser.

A general pretrained YOLO model detects its trained object classes; it does not guarantee exact retail brand/SKU identification. The scanning workflow therefore requires the user to map detections to a catalogue product and confirm quantity before stock changes.

## CSV formats
Sales CSV required columns: `date, product_id, product_name, quantity_sold, unit_price`; optional `unit_cost`. Use the sample CSV download in the app for an example.

Product settings CSV required columns: `product_id, current_stock, incoming_stock, lead_time_days, review_period_days, shelf_life_days, min_order_qty, pack_size, unit_cost`; optional `stock_age_days, expiry_date`.

## Important interpretation notes
- Forecasts are decision support, not guarantees. Short sales history lowers confidence.
- Profit analysis depends on recorded unit costs; missing costs may overstate gross profit.
- Expiry timing uses the entered expiry date where available, otherwise it may estimate remaining life from shelf life and stock age.
- The reorder export is a recommendation, not a purchase order sent to a supplier.


## Camera object detection

1. Start StockSense with `python app.py` and open it at `http://127.0.0.1:5000` (camera permission works on localhost).
2. If you have not installed the updated requirements, open a second terminal in this project folder and run `python -m pip install -r requirements.txt`. No virtual environment is required.
3. Restart Flask, open **Scan Products**, click **Start camera**, wait for the live picture, then click **Capture & detect**.
4. The first detection run may need an internet connection to download the pretrained `yolov8n.pt` weights.

The default pretrained model recognizes common COCO object categories; it does not identify every retail package, SKU, or brand. Review detections and map them to a catalogue product before adding stock. If detection fails, the result panel now shows the actual setup/model error instead of hiding it.
