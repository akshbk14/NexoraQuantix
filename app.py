"""
StockSense — Flask application
Team Nexora · Quantix 2K26 · PS11
"""

import csv
import io
import os
import functools
import copy
import threading
from pathlib import Path

import pandas as pd
import numpy as np

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, Response, session, jsonify, abort
)

import db
from forecast import daily_series, forecast_product
from optimizer import optimize_product, rank_reorders
from generate_demo_data import BASE


# ──────────────────────────────────────────────
# APP SETUP
# ──────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = os.environ.get('STOCKSENSE_SECRET', 'local-hackathon-dev-key-change-in-prod')
db.init()


# ──────────────────────────────────────────────
# AUTH HELPERS
# ──────────────────────────────────────────────

def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        # A browser can keep an old session cookie after the local SQLite
        # database is replaced or an account is removed. Never trust the cookie
        # alone: validate its user_id against the current database first.
        uid = session.get('user_id')
        user = None
        if uid is not None:
            try:
                user = db.get_user_by_id(int(uid))
            except (TypeError, ValueError, OverflowError):
                user = None
        if not user:
            session.clear()
            flash('Your session expired or the account could not be found. Please sign in again.', 'info')
            return redirect(url_for('signin'))
        return f(*args, **kwargs)
    return decorated


def current_user():
    uid = session.get('user_id')
    if uid:
        return db.get_user_by_id(uid)
    return None


def current_uid():
    return session.get('user_id')


# ──────────────────────────────────────────────
# LANGUAGE / I18N
# ──────────────────────────────────────────────

SUPPORTED_LANGUAGES = ("en", "ta", "hi", "ml", "te", "kn")

TRANSLATIONS = {
    "en": {
        "Overview": "Overview",
        "Sales Data": "Sales Data",
        "Inventory": "Inventory",
        "Demand Forecast": "Demand Forecast",
        "Reorder Recommendations": "Reorder Recommendations",
        "Analytics": "Analytics",
        "Settings": "Settings",
        "Reorder planner": "Reorder planner",
        "Data management": "Data management",
        "WORKSPACE": "WORKSPACE",
        "INVENTORY INTELLIGENCE": "INVENTORY INTELLIGENCE",
        "Local workspace": "Local workspace",
        "Data stays on this device": "Data stays on this device",
        "INVENTORY OPERATIONS / OVERVIEW": "INVENTORY OPERATIONS / OVERVIEW",
        "Inventory overview": "Inventory overview",
        "Turn sales history into clearer replenishment decisions.": "Turn sales history into clearer replenishment decisions.",
        "Local analytics": "Local analytics",
        "Load demo data": "Load demo data",
        "GET STARTED": "GET STARTED",
        "Your inventory decisions,": "Your inventory decisions,",
        "backed by data.": "backed by data.",
        "Load the included synthetic demo data to explore demand forecasts, stock risk, shelf-life-aware recommendations and reorder costs.": "Load the included synthetic demo data to explore demand forecasts, stock risk, shelf-life-aware recommendations and reorder costs.",
        "Load demo workspace": "Load demo workspace",
        "Demo values are synthetic and intended for demonstration only.": "Demo values are synthetic and intended for demonstration only.",
        "DEMAND SIGNAL": "DEMAND SIGNAL",
        "Forecast movement": "Forecast movement",
        "Explainable recommendations": "Explainable recommendations",
        "Products monitored": "Products monitored",
        "Across active inventory": "Across active inventory",
        "Products at risk": "Products at risk",
        "Critical or high priority": "Critical or high priority",
        "Units to reorder": "Units to reorder",
        "After budget prioritization": "After budget prioritization",
        "Estimated order cost": "Estimated order cost",
        "Estimated from unit costs": "Estimated from unit costs",
        "Replenishment priorities": "Replenishment priorities",
        "Products ranked by urgency and estimated risk": "Products ranked by urgency and estimated risk",
        "LIVE CALCULATION": "LIVE CALCULATION",
        "units": "units",
        "Critical": "Critical",
        "High": "High",
        "Medium": "Medium",
        "Low": "Low",
        "Other priorities": "Other priorities",
        "Decision insights": "Decision insights",
        "What the current plan indicates": "What the current plan indicates",
        "critical priorities": "critical priorities",
        "Review the most urgent products first to reduce stockout risk.": "Review the most urgent products first to reduce stockout risk.",
        "Lead-time-aware planning": "Lead-time-aware planning",
        "Forecast demand is considered across supplier lead time and review period.": "Forecast demand is considered across supplier lead time and review period.",
        "Shelf-life guardrails": "Shelf-life guardrails",
        "Perishable products are checked against a demand-based order cap.": "Perishable products are checked against a demand-based order cap.",
        "Forecast quality depends on data history. Review low-confidence warnings before acting.": "Forecast quality depends on data history. Review low-confidence warnings before acting.",
        "Smart reorder recommendations": "Smart reorder recommendations",
        "Recommended actions generated from sales history and product settings": "Recommended actions generated from sales history and product settings",
        "Export CSV": "Export CSV",
        "PRODUCT": "PRODUCT",
        "PRIORITY": "PRIORITY",
        "IN STOCK": "IN STOCK",
        "FORECAST DEMAND": "FORECAST DEMAND",
        "LEAD TIME": "LEAD TIME",
        "REORDER QTY": "REORDER QTY",
        "EST. COST": "EST. COST",
        "DETAILS": "DETAILS",
        "days": "days",
        "Analyze": "Analyze",
        "Showing": "Showing",
        "products": "products",
        "Recommendations are decision support, not automatic purchase orders.": "Recommendations are decision support, not automatic purchase orders.",
        "Import your data": "Import your data",
        "Upload CSV files to replace the current data": "Upload CSV files to replace the current data",
        "Sales history": "Sales history",
        "Product settings": "Product settings",
        "Upload sales CSV": "Upload sales CSV",
        "Upload settings CSV": "Upload settings CSV",
        "CSV: date, product_id, product_name, quantity_sold, unit_price": "CSV: date, product_id, product_name, quantity_sold, unit_price",
        "CSV with stock, lead time, shelf life, MOQ and pack size": "CSV with stock, lead time, shelf life, MOQ and pack size",
        "Planning settings": "Planning settings",
        "Adjust inventory planning assumptions": "Adjust inventory planning assumptions",
        "Service level": "Service level",
        "Balanced": "Balanced",
        "Recommended": "Recommended",
        "High protection": "High protection",
        "Default review period (days)": "Default review period (days)",
        "Purchase budget limit (₹)": "Purchase budget limit (₹)",
        "No limit": "No limit",
        "Save planning settings": "Save planning settings",
        "Save settings": "Save settings",
        "Built for Quantix 2K26 · PS11": "Built for Quantix 2K26 · PS11",
        "Inventory intelligence for better decisions": "Inventory intelligence for better decisions",
        "Product analysis": "Product analysis",
        "Back to overview": "Back to overview",
        "Current stock": "Current stock",
        "Units currently recorded": "Units currently recorded",
        "Forecast demand": "Forecast demand",
        "Across planning horizon": "Across planning horizon",
        "Recommended order": "Recommended order",
        "Units to consider ordering": "Units to consider ordering",
        "Priority": "Priority",
        "Based on days of cover": "Based on days of cover",
        "Historical demand & forecast": "Historical demand & forecast",
        "Daily sales history with projected demand horizon": "Daily sales history with projected demand horizon",
        "Historical sales": "Historical sales",
        "Forecast range (approx.)": "Forecast range (approx.)",
        "Recommendation reasoning": "Recommendation reasoning",
        "Why StockSense suggests this action": "Why StockSense suggests this action",
        "Supplier lead time": "Supplier lead time",
        "Safety stock": "Safety stock",
        "Days of cover": "Days of cover",
        "Estimated profit at risk": "Estimated profit at risk",
        "Forecast model": "Forecast model",
        "Forecast values": "Forecast values",
        "Projected units per day": "Projected units per day",
        "Model validation": "Model validation",
        "Not available": "Not available",
        "Historical backtest metrics are not a guarantee of future forecast accuracy.": "Historical backtest metrics are not a guarantee of future forecast accuracy.",
        "Language": "Language",
        "English": "English",
        "Tamil": "Tamil",
        "Hindi": "Hindi",
        "Malayalam": "Malayalam",
        "Telugu": "Telugu",
        "Kannada": "Kannada",
        "Product ID": "Product ID",
        "Demand and replenishment analysis": "Demand and replenishment analysis",
        "Historical and forecast demand chart": "Historical and forecast demand chart",
        "Day": "Day",
        "This recommendation is deferred because it exceeds the configured budget.": "This recommendation is deferred because it exceeds the configured budget.",
    },
    "ta": {
        "Overview": "மேலோட்டம்",
        "Sales Data": "விற்பனை தரவு",
        "Inventory": "சரக்கு",
        "Demand Forecast": "தேவை முன்னறிவிப்பு",
        "Reorder Recommendations": "மறுஆர்டர் பரிந்துரைகள்",
        "Analytics": "பகுப்பாய்வு",
        "Settings": "அமைப்புகள்",
        "Reorder planner": "மறுஆர்டர் திட்டமிடல்",
        "Data management": "தரவு மேலாண்மை",
        "WORKSPACE": "பணியிடம்",
        "INVENTORY INTELLIGENCE": "சரக்கு மேலாண்மை நுண்ணறிவு",
        "Local workspace": "உள்ளூர் பணியிடம்",
        "Data stays on this device": "தரவு இந்தச் சாதனத்திலேயே இருக்கும்",
        "Load demo data": "மாதிரித் தரவை ஏற்றவும்",
        "GET STARTED": "தொடங்குங்கள்",
        "Your inventory decisions,": "உங்கள் சரக்கு முடிவுகள்,",
        "backed by data.": "தரவின் அடிப்படையில்.",
        "Load demo workspace": "மாதிரிப் பணியிடத்தை ஏற்றவும்",
        "Demo values are synthetic and intended for demonstration only.": "மாதிரித் தரவுகள் விளக்கத்திற்காக மட்டுமே உருவாக்கப்பட்டவை.",
        "Products monitored": "கண்காணிக்கப்படும் பொருட்கள்",
        "Products at risk": "அபாயத்தில் உள்ள பொருட்கள்",
        "Units to reorder": "மறுஆர்டர் செய்ய வேண்டிய அலகுகள்",
        "Estimated order cost": "மதிப்பிடப்பட்ட ஆர்டர் செலவு",
        "units": "அலகுகள்",
        "Critical": "மிக அதிகம்",
        "High": "அதிகம்",
        "Medium": "நடுத்தரம்",
        "Low": "குறைவு",
        "Export CSV": "CSV கோப்பாக ஏற்றுமதி",
        "days": "நாட்கள்",
        "Analyze": "பகுப்பாய்வு",
        "Language": "மொழி",
        "English": "ஆங்கிலம்",
        "Tamil": "தமிழ்",
        "Hindi": "இந்தி",
        "Malayalam": "மலையாளம்",
        "Telugu": "தெலுங்கு",
        "Kannada": "கன்னடம்",
        "Current stock": "தற்போதைய இருப்பு",
        "Forecast demand": "கணிக்கப்பட்ட தேவை",
        "Recommended order": "பரிந்துரைக்கப்படும் ஆர்டர்",
        "Priority": "முன்னுரிமை",
        "Not available": "கிடைக்கவில்லை",
        "Day": "நாள்",
    },
    "hi": {
        "Overview": "अवलोकन",
        "Sales Data": "बिक्री डेटा",
        "Inventory": "इन्वेंटरी",
        "Demand Forecast": "मांग पूर्वानुमान",
        "Reorder Recommendations": "पुनः ऑर्डर सुझाव",
        "Analytics": "विश्लेषण",
        "Settings": "सेटिंग",
        "Reorder planner": "पुनः ऑर्डर योजना",
        "Data management": "डेटा प्रबंधन",
        "WORKSPACE": "कार्यस्थल",
        "INVENTORY INTELLIGENCE": "इन्वेंटरी इंटेलिजेंस",
        "Local workspace": "स्थानीय कार्यस्थल",
        "Load demo data": "डेमो डेटा लोड करें",
        "GET STARTED": "शुरू करें",
        "Load demo workspace": "डेमो कार्यस्थल लोड करें",
        "Demo values are synthetic and intended for demonstration only.": "डेमो डेटा केवल प्रदर्शन के लिए बनाया गया है।",
        "Products monitored": "निगरानी किए गए उत्पाद",
        "Products at risk": "जोखिम वाले उत्पाद",
        "Units to reorder": "पुनः ऑर्डर की इकाइयाँ",
        "Estimated order cost": "अनुमानित ऑर्डर लागत",
        "units": "इकाइयाँ",
        "Critical": "अत्यंत उच्च",
        "High": "उच्च",
        "Medium": "मध्यम",
        "Low": "कम",
        "Export CSV": "CSV निर्यात करें",
        "days": "दिन",
        "Analyze": "विश्लेषण करें",
        "Language": "भाषा",
        "English": "अंग्रेज़ी",
        "Tamil": "तमिल",
        "Hindi": "हिंदी",
        "Malayalam": "मलयालम",
        "Telugu": "तेलुगु",
        "Kannada": "कन्नड़",
        "Current stock": "मौजूदा स्टॉक",
        "Forecast demand": "अनुमानित मांग",
        "Recommended order": "अनुशंसित ऑर्डर",
        "Priority": "प्राथमिकता",
        "Not available": "उपलब्ध नहीं",
        "Day": "दिन",
    },
    "ml": {
        "Overview": "അവലോകനം",
        "Sales Data": "വിൽപ്പന ഡാറ്റ",
        "Inventory": "ഇൻവെന്ററി",
        "Demand Forecast": "ആവശ്യകതാ പ്രവചനം",
        "Reorder Recommendations": "പുനഃഓർഡർ നിർദേശങ്ങൾ",
        "Analytics": "വിശകലനം",
        "Settings": "ക്രമീകരണങ്ങൾ",
        "units": "യൂണിറ്റുകൾ",
        "Critical": "അത്യാവശ്യ",
        "High": "ഉയർന്നത്",
        "Medium": "ഇടത്തരം",
        "Low": "കുറഞ്ഞത്",
        "days": "ദിവസങ്ങൾ",
        "Language": "ഭാഷ",
        "English": "ഇംഗ്ലീഷ്",
        "Not available": "ലഭ്യമല്ല",
        "Day": "ദിവസം",
    },
    "te": {
        "Overview": "అవలోకనం",
        "Sales Data": "అమ్మకాల డేటా",
        "Inventory": "జాబితా",
        "Demand Forecast": "డిమాండ్ సూచన",
        "Reorder Recommendations": "పునరాదేశ సిఫార్సులు",
        "Analytics": "విశ్లేషణ",
        "Settings": "సెట్టింగ్‌లు",
        "units": "యూనిట్లు",
        "Critical": "అత్యంత అత్యవసరం",
        "High": "అధిక",
        "Medium": "మధ్యస్థం",
        "Low": "తక్కువ",
        "days": "రోజులు",
        "Language": "భాష",
        "English": "ఇంగ్లీష్",
        "Not available": "అందుబాటులో లేదు",
        "Day": "రోజు",
    },
    "kn": {
        "Overview": "ಅವಲೋಕನ",
        "Sales Data": "ಮಾರಾಟ ಡೇಟಾ",
        "Inventory": "ಸರಕು",
        "Demand Forecast": "ಬೇಡಿಕೆ ಮುನ್ಸೂಚನೆ",
        "Reorder Recommendations": "ಮರುಆರ್ಡರ್ ಶಿಫಾರಸುಗಳು",
        "Analytics": "ವಿಶ್ಲೇಷಣೆ",
        "Settings": "ಸೆಟ್ಟಿಂಗ್‌ಗಳು",
        "units": "ಘಟಕಗಳು",
        "Critical": "ಅತ್ಯಂತ ತುರ್ತು",
        "High": "ಹೆಚ್ಚು",
        "Medium": "ಮಧ್ಯಮ",
        "Low": "ಕಡಿಮೆ",
        "days": "ದಿನಗಳು",
        "Language": "ಭಾಷೆ",
        "English": "ಇಂಗ್ಲಿಷ್",
        "Not available": "ಲಭ್ಯವಿಲ್ಲ",
        "Day": "ದಿನ",
    },
}


@app.context_processor
def inject_globals():
    lang = session.get('lang', 'en')
    if current_uid() and 'lang' not in session:
        lang = db.settings(current_uid()).get('language', 'en')
    if lang not in SUPPORTED_LANGUAGES:
        lang = 'en'

    def t(text):
        tr = TRANSLATIONS.get(lang, TRANSLATIONS['en'])
        return tr.get(text, TRANSLATIONS['en'].get(text, text))

    user = current_user()
    uid = current_uid()

    # Theme
    VALID_THEMES = ('neon-dark', 'gold', 'cream')
    theme = 'neon-dark'
    if uid:
        cfg = db.settings(uid)
        t_saved = cfg.get('theme', 'neon-dark')
        if t_saved in VALID_THEMES:
            theme = t_saved

    return {
        't': t,
        'current_lang': lang,
        'supported_languages': SUPPORTED_LANGUAGES,
        'current_user': user,
        'current_theme': theme,
    }


# ──────────────────────────────────────────────
# LANGUAGE ROUTE
# ──────────────────────────────────────────────

@app.route('/set-language', methods=['POST'])
def set_language():
    lang = request.form.get('lang', 'en')
    if lang not in SUPPORTED_LANGUAGES:
        lang = 'en'
    session['lang'] = lang
    if current_uid():
        db.set_settings({'language': lang}, current_uid())
    return redirect(request.referrer or url_for('dashboard'))


# ──────────────────────────────────────────────
# AUTH ROUTES
# ──────────────────────────────────────────────

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter your email and password.', 'error')
            return render_template('auth/signin.html', email=email)

        user = db.get_user_by_email(email)
        if not user or not db.verify_password(user, password):
            flash('Incorrect email or password. Please try again.', 'error')
            return render_template('auth/signin.html', email=email)

        session.clear()
        session['user_id'] = user['id']
        session['user_name'] = user['full_name']
        session.permanent = True
        flash(f"Welcome back, {user['full_name'].split()[0]}!", 'success')
        return redirect(url_for('dashboard'))

    return render_template('auth/signin.html', email='')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    form_data = {}

    if request.method == 'POST':
        full_name   = request.form.get('full_name', '').strip()
        store_name  = request.form.get('store_name', '').strip()
        email       = request.form.get('email', '').strip()
        password    = request.form.get('password', '')
        confirm     = request.form.get('confirm_password', '')

        form_data = {'full_name': full_name, 'store_name': store_name, 'email': email}

        errors = []
        if not full_name:
            errors.append('Full name is required.')
        if not email or '@' not in email:
            errors.append('A valid email address is required.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if password != confirm:
            errors.append('Passwords do not match.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('auth/signup.html', form=form_data)

        try:
            db.create_user(full_name, store_name or full_name + "'s Store", email, password)
            flash('Account created! Please sign in.', 'success')
            return redirect(url_for('signin'))
        except ValueError as exc:
            flash(str(exc), 'error')
            return render_template('auth/signup.html', form=form_data)

    return render_template('auth/signup.html', form=form_data)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been signed out.', 'info')
    return redirect(url_for('signin'))


# ──────────────────────────────────────────────
# DATA VALIDATION
# ──────────────────────────────────────────────

SALE_COLS = {'date', 'product_id', 'product_name', 'quantity_sold', 'unit_price'}
PROD_COLS = {
    'product_id', 'current_stock', 'incoming_stock', 'lead_time_days',
    'review_period_days', 'shelf_life_days', 'min_order_qty', 'pack_size', 'unit_cost'
}


def read_upload(file, required, label):
    if not file or not file.filename:
        raise ValueError(f'Choose a {label} CSV file.')
    df = pd.read_csv(file)
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f'{label} CSV missing columns: {", ".join(sorted(missing))}')
    if df.empty:
        raise ValueError(f'{label} CSV has no rows.')
    return df


def clean_sales(df):
    df = df.copy()
    df['date'] = pd.to_datetime(df.date, errors='coerce')
    if df.date.isna().any():
        raise ValueError('Sales CSV has invalid dates; use YYYY-MM-DD.')
    df['date'] = df.date.dt.strftime('%Y-%m-%d')

    for col in ['quantity_sold', 'unit_price']:
        df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)
        if df[col].isna().any() or (df[col] < 0).any():
            raise ValueError(f'{col} must be non-negative numeric values.')

    if df[['date', 'product_id', 'product_name', 'quantity_sold', 'unit_price']].duplicated().any():
        raise ValueError('Duplicate sales rows found; remove duplicates and upload again.')

    if 'unit_cost' not in df:
        df['unit_cost'] = np.nan
    else:
        df['unit_cost'] = pd.to_numeric(df['unit_cost'], errors='coerce')
        if (df.unit_cost.dropna() < 0).any():
            raise ValueError('unit_cost cannot be negative.')

    df['outlier_flag'] = False
    for _, idx in df.groupby('product_id').groups.items():
        values = df.loc[idx, 'quantity_sold'].astype(float)
        median = values.median()
        mad = np.median(np.abs(values - median))
        upper = (
            median + 6 * 1.4826 * mad if mad > 0
            else (median * 5 if len(values) >= 10 and median > 0 else float('inf'))
        )
        mask = values > upper
        df.loc[idx, 'outlier_flag'] = mask
        df.loc[idx, 'quantity_sold'] = values.clip(upper=upper)

    return df


def clean_products(df):
    df = df.copy()
    missing = PROD_COLS - set(df.columns)
    if missing:
        raise ValueError('Product settings missing columns: ' + ', '.join(sorted(missing)))

    if 'stock_age_days' not in df:
        df['stock_age_days'] = np.nan

    if 'expiry_date' not in df:
        df['expiry_date'] = None
    else:
        df['expiry_date'] = df['expiry_date'].where(df['expiry_date'].notna(), None)
        for value in df['expiry_date'].dropna():
            try:
                pd.to_datetime(value, format='%Y-%m-%d', errors='raise')
            except Exception:
                raise ValueError('expiry_date must use YYYY-MM-DD format.')

    if df.product_id.astype(str).duplicated().any():
        raise ValueError('product_id must be unique in settings CSV.')

    numeric_cols = list(PROD_COLS - {'product_id'}) + ['stock_age_days']
    required_numeric = {
        'current_stock', 'incoming_stock', 'lead_time_days',
        'review_period_days', 'shelf_life_days', 'min_order_qty', 'pack_size'
    }

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        if col in required_numeric and df[col].isna().any():
            raise ValueError(f'{col} must be numeric.')
        if (df[col].dropna() < 0).any():
            raise ValueError(f'{col} cannot be negative.')

    for col in ['lead_time_days', 'review_period_days', 'shelf_life_days', 'min_order_qty', 'pack_size']:
        if (df[col] < 1).any():
            raise ValueError(f'{col} must be at least 1.')
        df[col] = df[col].astype(int)

    return df


# ──────────────────────────────────────────────
# DEMO DATA LOADER
# ──────────────────────────────────────────────

def load_demo(user_id):
    import generate_demo_data  # ensure files are written
    _ = generate_demo_data

    sales_df = clean_sales(pd.read_csv(BASE / 'data/sales.csv'))
    products_df = clean_products(pd.read_csv(BASE / 'data/product_settings.csv'))

    # Get product names from sales for the products table
    name_map = (
        sales_df.groupby('product_id')['product_name']
        .last().to_dict()
    )

    db.replace_sales([
        (row.date, str(row.product_id), str(row.product_name),
         float(row.quantity_sold), float(row.unit_price),
         None if pd.isna(row.unit_cost) else float(row.unit_cost))
        for row in sales_df.itertuples()
    ], user_id)

    db.replace_products([
        {
            'product_id': str(row.product_id),
            'product_name': name_map.get(str(row.product_id), str(row.product_id)),
            'category': '',
            'unit': 'units',
            'current_stock': float(row.current_stock),
            'incoming_stock': float(row.incoming_stock),
            'lead_time_days': int(row.lead_time_days),
            'review_period_days': int(row.review_period_days),
            'shelf_life_days': int(row.shelf_life_days),
            'min_order_qty': int(row.min_order_qty),
            'pack_size': int(row.pack_size),
            'unit_cost': None if pd.isna(row.unit_cost) else float(row.unit_cost),
            'stock_age_days': None if pd.isna(getattr(row, 'stock_age_days', float('nan'))) else int(row.stock_age_days),
            'supplier_name': '',
        }
        for row in products_df.itertuples()
    ], user_id)


# ──────────────────────────────────────────────
# PLANNING ENGINE
# ──────────────────────────────────────────────

# Planning can be CPU-heavy for large catalogs. Keep a small process-local cache
# keyed by the SQLite file/WAL signature. Any database write changes the signature,
# so sales/product/settings updates automatically invalidate the cached plan.
_PLAN_CACHE = {}
_PLAN_CACHE_LOCK = threading.Lock()
_PLAN_CACHE_LIMIT = 12


def _database_signature():
    paths = (db.DB, Path(str(db.DB) + '-wal'), Path(str(db.DB) + '-shm'))
    signature = []
    for path in paths:
        try:
            stat = path.stat()
            signature.append((str(path), stat.st_mtime_ns, stat.st_size))
        except OSError:
            signature.append((str(path), 0, 0))
    return tuple(signature)


def plan(user_id):
    cache_key = (str(user_id), _database_signature())
    with _PLAN_CACHE_LOCK:
        cached = _PLAN_CACHE.get(cache_key)
        if cached is not None:
            # Do not let callers mutate the cached nested results or DataFrame.
            return copy.deepcopy(cached[0]), cached[1].copy(), cached[2].copy(deep=True)

    computed = _plan_uncached(user_id)
    # Re-check after computation because reading settings may create missing
    # defaults, which itself updates the SQLite signature.
    cache_key = (str(user_id), _database_signature())
    with _PLAN_CACHE_LOCK:
        _PLAN_CACHE[cache_key] = (copy.deepcopy(computed[0]), computed[1].copy(), computed[2].copy(deep=True))
        # Bound memory use and discard stale versions for this same user.
        stale = [key for key in _PLAN_CACHE if key[0] == str(user_id) and key != cache_key]
        for key in stale:
            _PLAN_CACHE.pop(key, None)
        while len(_PLAN_CACHE) > _PLAN_CACHE_LIMIT:
            _PLAN_CACHE.pop(next(iter(_PLAN_CACHE)))
    return computed


def _plan_uncached(user_id):
    sales_df = db.sales(user_id)
    prods = db.products(user_id)
    cfg = db.settings(user_id)
    output = []

    empty_kpis = {
        'products_at_risk': 0,
        'products_to_reorder': 0,
        'critical_count': 0,
        'total_order_units': 0,
        'estimated_order_cost': 0,
        'total_reorder_cost': 0,
        'total_profit_at_risk': 0,
        'profit_protected': 0,
        'budget_limit': None,
    }

    if sales_df.empty or not prods:
        return [], empty_kpis, sales_df

    # Group the sales table once instead of scanning every sales row for every
    # product. This avoids O(products × sales_rows) filtering on large imports.
    sales_by_product = {}
    series_by_product = {}
    if not sales_df.empty:
        sales_work = sales_df.copy()
        sales_work['product_id'] = sales_work['product_id'].astype(str)
        last_rows = sales_work.groupby('product_id', sort=False).tail(1)
        sales_by_product = {str(row['product_id']): row for _, row in last_rows.iterrows()}

        sales_work['_parsed_date'] = pd.to_datetime(sales_work['date'], errors='coerce')
        valid_sales = sales_work.dropna(subset=['_parsed_date'])
        if not valid_sales.empty:
            grouped_daily = valid_sales.groupby(['product_id', '_parsed_date'], sort=False)['quantity_sold'].sum()
            for pid, product_daily in grouped_daily.groupby(level=0, sort=False):
                daily = product_daily.droplevel(0).sort_index()
                series_by_product[str(pid)] = daily.asfreq('D', fill_value=0).to_numpy(dtype=float)

    for product in prods:
        pid = str(product['product_id'])
        series = series_by_product.get(pid, np.array([], dtype=float))
        horizon = int(product['lead_time_days']) + int(product['review_period_days'])
        forecast = forecast_product(series, horizon)

        product_sales = sales_by_product.get(pid)
        product_info = {
            'product_id': product['product_id'],
            'product_name': (
                str(product_sales['product_name'])
                if product_sales is not None else product.get('product_name', product['product_id'])
            ),
            'unit_price': float(product_sales['unit_price']) if product_sales is not None else 0,
            'unit_cost': product.get('unit_cost'),
        }

        result = optimize_product(
            product_info, forecast, product,
            float(cfg.get('service_level', 0.95))
        )
        result['incoming_stock'] = float(product.get('incoming_stock', 0) or 0)
        result['target_stock'] = round(result.get('forecast_demand', 0) + result.get('safety_stock', 0), 2)
        result['shelf_life_days'] = int(product.get('shelf_life_days', 365) or 365)
        result['pack_size'] = int(product.get('pack_size', 1) or 1)
        result['min_order_qty'] = int(product.get('min_order_qty', 1) or 1)
        result['forecast_meta'] = forecast
        output.append(result)

    budget = cfg.get('budget_limit', '')
    output = rank_reorders(output, budget if budget else None)

    budget_limit = float(budget) if budget else None
    kpis = {
        'products_at_risk': sum(r['priority'] in ('Critical', 'High') for r in output),
        'products_to_reorder': sum(r['recommended_order'] > 0 for r in output),
        'critical_count': sum(r['priority'] == 'Critical' for r in output),
        'total_order_units': sum(r['recommended_order'] for r in output if not r.get('deferred_over_budget')),
        'estimated_order_cost': round(sum(r['estimated_order_cost'] for r in output if not r.get('deferred_over_budget')), 2),
        'total_reorder_cost': round(sum(r['estimated_order_cost'] for r in output if not r.get('deferred_over_budget')), 2),
        'total_profit_at_risk': round(sum(r['profit_at_risk'] for r in output), 2),
        'profit_protected': round(sum(r['profit_at_risk'] for r in output if r['recommended_order'] and not r.get('deferred_over_budget')), 2),
        'budget_limit': budget_limit,
    }

    return output, kpis, sales_df


# ──────────────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
@login_required
def dashboard():
    uid = current_uid()

    if request.method == 'POST':
        action = request.form.get('action')
        try:
            if action == 'demo':
                load_demo(uid)
                flash('Synthetic demo data loaded. Labelled as demo — not real measurements.', 'success')

            elif action == 'sales':
                df = clean_sales(read_upload(request.files.get('sales_file'), SALE_COLS, 'sales'))
                db.replace_sales([
                    (row.date, str(row.product_id), str(row.product_name),
                     float(row.quantity_sold), float(row.unit_price),
                     None if pd.isna(row.unit_cost) else float(row.unit_cost))
                    for row in df.itertuples()
                ], uid)
                flash(f'Sales uploaded — {int(df.outlier_flag.sum())} possible outlier row(s) flagged/capped.', 'success')

            elif action == 'products':
                df = clean_products(read_upload(request.files.get('products_file'), PROD_COLS, 'product settings'))
                sales_df = db.sales(uid)
                name_map = sales_df.groupby('product_id')['product_name'].last().to_dict() if not sales_df.empty else {}
                db.replace_products([
                    {
                        'product_id': str(row.product_id),
                        'product_name': name_map.get(str(row.product_id), str(row.product_id)),
                        'category': '',
                        'unit': 'units',
                        'current_stock': float(row.current_stock),
                        'incoming_stock': float(row.incoming_stock),
                        'lead_time_days': int(row.lead_time_days),
                        'review_period_days': int(row.review_period_days),
                        'shelf_life_days': int(row.shelf_life_days),
                        'min_order_qty': int(row.min_order_qty),
                        'pack_size': int(row.pack_size),
                        'unit_cost': None if pd.isna(row.unit_cost) else float(row.unit_cost),
                        'stock_age_days': None if pd.isna(getattr(row, 'stock_age_days', float('nan'))) else int(row.stock_age_days),
                        'supplier_name': '',
                        'expiry_date': getattr(row, 'expiry_date', None),
                    }
                    for row in df.itertuples()
                ], uid)
                flash('Product settings uploaded.', 'success')

        except Exception as exc:
            flash(str(exc), 'error')

        return redirect(url_for('dashboard'))

    results, kpis, sales_df = plan(uid)
    prods = db.products(uid)

    # Total stock for KPI card
    total_stock = sum(p.get('current_stock', 0) for p in prods)
    expiry_risk = sum(
        1 for p in prods
        if p.get('shelf_life_days', 365) < 365 and p.get('current_stock', 0) > 0
    )

    return render_template(
        'dashboard.html',
        results=results,
        kpis=kpis,
        settings=db.settings(uid),
        products=prods,
        has_data=not sales_df.empty,
        total_stock=total_stock,
        expiry_risk=expiry_risk,
    )


# ──────────────────────────────────────────────
# SALES DATA PAGE
# ──────────────────────────────────────────────

@app.route('/sales')
@login_required
def sales_page():
    uid = current_uid()
    page = int(request.args.get('page', 1))
    search = request.args.get('search', '')
    product_filter = request.args.get('product', '')

    data = db.sales_records_page(uid, page=page, search=search, product_filter=product_filter)
    product_list = db.sales_product_list(uid)

    return render_template(
        'sales.html',
        data=data,
        product_list=product_list,
        search=search,
        product_filter=product_filter,
    )


# ──────────────────────────────────────────────
# INVENTORY PAGE
# ──────────────────────────────────────────────

@app.route('/inventory')
@login_required
def inventory():
    return redirect(url_for('dashboard'))
    uid = current_uid()
    results, kpis, _ = plan(uid)
    prods = db.products(uid)

    # Merge reorder info into products
    reorder_map = {r['product_id']: r for r in results}
    for p in prods:
        r = reorder_map.get(p['product_id'], {})
        p['priority'] = r.get('priority', 'Low')
        p['recommended_order'] = r.get('recommended_order', 0)
        p['forecast_demand'] = r.get('forecast_demand', 0)

    return render_template('inventory.html', products=prods, kpis=kpis)


# ──────────────────────────────────────────────
# ADD PRODUCT (API)
# ──────────────────────────────────────────────

@app.route('/api/add-product', methods=['POST'])
@login_required
def api_add_product():
    uid = current_uid()
    try:
        d = request.get_json(force=True) or {}

        product_id = str(d.get('product_id', '')).strip()
        product_name = str(d.get('product_name', '')).strip()

        if not product_id:
            return jsonify({'ok': False, 'error': 'Product ID is required.'}), 400
        if not product_name:
            return jsonify({'ok': False, 'error': 'Product name is required.'}), 400

        def safe_int(val, default, minimum=1):
            try:
                v = int(float(str(val)))
                return max(minimum, v)
            except (ValueError, TypeError):
                return default

        def safe_float(val, default=None):
            try:
                v = float(str(val))
                return max(0.0, v)
            except (ValueError, TypeError):
                return default

        data = {
            'product_id': product_id,
            'product_name': product_name,
            'category': str(d.get('category', '')).strip(),
            'unit': str(d.get('unit', 'units')).strip() or 'units',
            'current_stock': safe_float(d.get('current_stock', 0), 0.0),
            'incoming_stock': safe_float(d.get('incoming_stock', 0), 0.0),
            'lead_time_days': safe_int(d.get('lead_time_days', 7), 7),
            'review_period_days': safe_int(d.get('review_period_days', 7), 7),
            'shelf_life_days': safe_int(d.get('shelf_life_days', 365), 365),
            'min_order_qty': safe_int(d.get('min_order_qty', 1), 1),
            'pack_size': safe_int(d.get('pack_size', 1), 1),
            'unit_cost': safe_float(d.get('unit_cost')),
            'stock_age_days': safe_int(d.get('stock_age_days'), None, 0) if d.get('stock_age_days') not in ('', None) else None,
            'supplier_name': str(d.get('supplier_name', '')).strip(),
            'expiry_date': str(d.get('expiry_date', '')).strip() or None,
        }

        db.upsert_product(data, uid)
        return jsonify({'ok': True, 'product_id': product_id, 'product_name': product_name})

    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 500


# ──────────────────────────────────────────────
# DEMAND FORECAST PAGE
# ──────────────────────────────────────────────

@app.route('/forecast')
@login_required
def forecast_page():
    return redirect(url_for('dashboard'))
    uid = current_uid()
    results, kpis, sales_df = plan(uid)
    return render_template('forecast.html', results=results, kpis=kpis, has_data=not sales_df.empty)


# ──────────────────────────────────────────────
# REORDER RECOMMENDATIONS PAGE
# ──────────────────────────────────────────────

@app.route('/reorder')
@login_required
def reorder():
    uid = current_uid()
    results, kpis, sales_df = plan(uid)
    return render_template('reorder.html', results=results, kpis=kpis, has_data=not sales_df.empty)


# ──────────────────────────────────────────────
# ANALYTICS PAGE
# ──────────────────────────────────────────────

@app.route('/analytics')
@login_required
def analytics():
    uid = current_uid()
    results, kpis, sales_df = plan(uid)
    products = db.products(uid)
    today = pd.Timestamp.today().normalize()
    stockouts = [r for r in results if r.get('priority') in ('Critical', 'High')]
    overstock = []
    expiry = []
    for p in products:
        r = next((x for x in results if x.get('product_id') == p.get('product_id')), {})
        daily = (float(r.get('forecast_demand', 0) or 0) / max(1, int(r.get('lead_time_days', 1) or 1) + int(r.get('review_period_days', 7) or 7)))
        target = daily * (int(p.get('lead_time_days', 7) or 7) + int(p.get('review_period_days', 7) or 7))
        excess = max(0, float(p.get('current_stock', 0) or 0) - target * 1.5)
        if excess > 0 and not sales_df.empty:
            cost = float(p.get('unit_cost') or 0) * excess
            price = 0.0
            if not sales_df.empty:
                q = sales_df[sales_df.product_id.astype(str) == str(p.get('product_id'))]
                if not q.empty: price = float(q.unit_price.iloc[-1] or 0)
            margin = price - float(p.get('unit_cost') or 0)
            if margin > 0:
                advice = 'Consider a modest, time-limited promotion while keeping the price above unit cost.'
            elif margin <= 0 and price > 0:
                advice = 'Review pricing and purchasing before discounting; current margin may already be weak.'
            else:
                advice = 'Pause replenishment and review product movement before offering a promotion.'
            overstock.append({**p, 'excess': round(excess, 1), 'capital': round(cost, 2), 'advice': advice})
        days_left = None
        expiry_date = p.get('expiry_date')
        if expiry_date:
            try: days_left = (pd.to_datetime(expiry_date).normalize() - today).days
            except Exception: days_left = None
        elif p.get('stock_age_days') is not None and int(p.get('shelf_life_days') or 365) < 365:
            days_left = int(p.get('shelf_life_days') or 365) - int(p.get('stock_age_days') or 0)
        if days_left is not None and days_left <= 30 and float(p.get('current_stock', 0) or 0) > 0:
            expiry.append({**p, 'days_left': days_left, 'expiry_date': expiry_date, 'estimated': not bool(expiry_date), 'capital': round(float(p.get('unit_cost') or 0) * float(p.get('current_stock') or 0), 2), 'advice': ('Prioritize selling this batch first and consider a carefully calculated short-term promotion.' if days_left > 0 else 'Check the product immediately and follow applicable safety and disposal rules.')})

    revenue = 0.0; cogs = 0.0; costed_revenue = 0.0
    profit_rows = []
    if not sales_df.empty:
        revenue = float((sales_df.quantity_sold * sales_df.unit_price).sum())
        costed = sales_df[sales_df.unit_cost.notna()].copy()
        if not costed.empty:
            costed['revenue'] = costed.quantity_sold * costed.unit_price
            costed['cost'] = costed.quantity_sold * costed.unit_cost
            costed['gross_profit'] = costed.revenue - costed.cost
            costed_revenue = float(costed.revenue.sum())
            cogs = float(costed.cost.sum())
            grouped = costed.groupby(['product_id','product_name'], as_index=False).agg(revenue=('revenue','sum'), gross_profit=('gross_profit','sum'))
            profit_rows = grouped.sort_values('gross_profit', ascending=False).to_dict('records')
    profit = (costed_revenue - cogs) if costed_revenue > 0 else 0.0
    margin_pct = (profit / costed_revenue * 100) if costed_revenue > 0 else None
    return render_template('analytics.html', results=results, kpis=kpis, has_data=not sales_df.empty,
        chart_data=[], stockouts=stockouts, overstock=overstock, expiry=expiry,
        revenue=revenue, cogs=cogs, costed_revenue=costed_revenue, gross_profit=profit, margin_pct=margin_pct, profit_rows=profit_rows)


# ──────────────────────────────────────────────
# SETTINGS PAGE
# ──────────────────────────────────────────────

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings_page():
    uid = current_uid()
    user = current_user()

    if request.method == 'POST':
        action = request.form.get('action', '')
        try:
            if action == 'profile':
                full_name  = request.form.get('full_name', '').strip()
                store_name = request.form.get('store_name', '').strip()
                if not full_name:
                    raise ValueError('Full name is required.')
                db.update_user(uid, full_name, store_name)
                session['user_name'] = full_name
                flash('Profile updated.', 'success')

            elif action == 'planning':
                service_level = float(request.form.get('service_level', '.95'))
                review_period = int(request.form.get('default_review_period', '7'))
                budget = request.form.get('budget_limit', '').strip()

                if service_level not in (.90, .95, .98):
                    raise ValueError('Invalid service level.')
                if review_period < 1:
                    raise ValueError('Review period must be at least 1 day.')
                if budget and float(budget) < 0:
                    raise ValueError('Budget cannot be negative.')

                db.set_settings({
                    'service_level': service_level,
                    'default_review_period': review_period,
                    'budget_limit': budget,
                }, uid)
                flash('Planning settings saved.', 'success')

            elif action == 'theme':
                VALID = ('neon-dark', 'gold', 'cream')
                theme = request.form.get('theme', 'neon-dark')
                if theme not in VALID:
                    theme = 'neon-dark'
                db.set_settings({'theme': theme}, uid)
                flash('Theme updated.', 'success')

        except Exception as exc:
            flash(str(exc), 'error')

        return redirect(url_for('settings_page'))

    cfg = db.settings(uid)
    return render_template('settings.html', settings=cfg, user=user)


# ──────────────────────────────────────────────
# PRODUCT DETAIL
# ──────────────────────────────────────────────

@app.route('/product/<pid>')
@login_required
def detail(pid):
    uid = current_uid()
    results, _, sales_df = plan(uid)

    result = next((item for item in results if item['product_id'] == pid), None)
    if not result:
        flash('Product not found or has no data.', 'error')
        return redirect(url_for('dashboard'))

    history = sales_df[sales_df.product_id.astype(str) == pid].copy()
    history['date'] = pd.to_datetime(history.date)
    daily = (
        history.groupby('date').quantity_sold.sum()
        .sort_index().asfreq('D', fill_value=0)
    )

    forecast_meta = result['forecast_meta']
    future = pd.date_range(
        daily.index.max() + pd.Timedelta(days=1),
        periods=len(forecast_meta['forecast'])
    )

    chart = {
        'hd': [v.strftime('%Y-%m-%d') for v in daily.index],
        'hv': [round(v, 2) for v in daily.tolist()],
        'fd': [v.strftime('%Y-%m-%d') for v in future],
        'fv': [round(v, 2) for v in forecast_meta['forecast']],
        'lo': [round(max(0, v - 1.65 * forecast_meta['sigma_daily']), 2) for v in forecast_meta['forecast']],
        'hi': [round(v + 1.65 * forecast_meta['sigma_daily'], 2) for v in forecast_meta['forecast']],
        'unit': db.get_product(uid, pid).get('unit', 'units') if db.get_product(uid, pid) else 'units',
    }

    return render_template('product.html', r=result, c=chart)


# ──────────────────────────────────────────────
# CSV EXPORT
# ──────────────────────────────────────────────

@app.route('/download.csv')
@login_required
def download():
    uid = current_uid()
    rows, _, _ = plan(uid)

    output = io.StringIO()
    fields = [
        'product_id', 'product_name', 'current_stock', 'forecast_demand',
        'lead_time_days', 'recommended_order', 'priority', 'profit_at_risk',
        'estimated_order_cost', 'warning', 'explanation', 'deferred_over_budget'
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows([{k: row.get(k, '') for k in fields} for row in rows])

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=stocksense_reorder_list.csv'}
    )


# ──────────────────────────────────────────────
# API — SET THEME
# ──────────────────────────────────────────────

@app.route('/api/set-theme', methods=['POST'])
@login_required
def api_set_theme():
    uid = current_uid()
    VALID = ('neon-dark', 'gold', 'cream')
    data = request.get_json(force=True) or {}
    theme = str(data.get('theme', 'neon-dark'))
    if theme not in VALID:
        theme = 'neon-dark'
    db.set_settings({'theme': theme}, uid)
    return jsonify({'ok': True, 'theme': theme})


# ──────────────────────────────────────────────
# API — DASHBOARD KPIs (for live refresh)
# ──────────────────────────────────────────────

@app.route('/api/dashboard-kpis')
@login_required
def api_dashboard_kpis():
    uid = current_uid()
    results, kpis, sales_df = plan(uid)
    prods = db.products(uid)
    return jsonify({
        'kpis': kpis,
        'product_count': len(prods),
        'has_data': not sales_df.empty,
    })


# ──────────────────────────────────────────────
# SAMPLE CSV DOWNLOAD
# ──────────────────────────────────────────────

@app.route('/sample-sales.csv')
@login_required
def sample_sales_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['date', 'product_id', 'product_name', 'quantity_sold', 'unit_price', 'unit_cost'])
    writer.writerows([
        ['2026-10-01', 'P01', 'Milk', 22, 30, 23],
        ['2026-10-01', 'P02', 'Bread', 15, 35, 25],
        ['2026-10-02', 'P01', 'Milk', 25, 30, 23],
        ['2026-10-02', 'P02', 'Bread', 18, 35, 25],
    ])
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=sample_sales.csv'}
    )


@app.route('/sample-products.csv')
@login_required
def sample_products_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['product_id', 'current_stock', 'incoming_stock', 'lead_time_days',
                     'review_period_days', 'shelf_life_days', 'min_order_qty', 'pack_size', 'unit_cost'])
    writer.writerows([
        ['P01', 18, 0, 2, 3, 18, 1, 1, 23],
        ['P02', 25, 0, 1, 2, 12, 1, 1, 25],
    ])
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=sample_products.csv'}
    )




# ──────────────────────────────────────────────
# CAMERA SCAN — OpenCV + YOLO (lazy-loaded, cached model)
# ──────────────────────────────────────────────

_YOLO_MODEL = None
_YOLO_MODEL_PATH = None

@app.route('/scan')
@login_required
def scan_page():
    return render_template('scan.html', products=db.products(current_uid()))

@app.route('/api/scan-detect', methods=['POST'])
@login_required
def scan_detect():
    data = request.get_json(silent=True) or {}
    image_data = data.get('image', '')
    if not image_data.startswith('data:image/') or ',' not in image_data:
        return jsonify({'ok': False, 'error': 'Capture an image from the camera first.'}), 400
    try:
        import base64
        import cv2
        from ultralytics import YOLO
        raw = base64.b64decode(image_data.split(',', 1)[1], validate=True)
        arr = np.frombuffer(raw, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({'ok': False, 'error': 'The captured image could not be read.'}), 400
        global _YOLO_MODEL, _YOLO_MODEL_PATH
        model_path = os.environ.get('STOCKSENSE_YOLO_MODEL', 'yolov8n.pt')
        if _YOLO_MODEL is None or _YOLO_MODEL_PATH != model_path:
            _YOLO_MODEL = YOLO(model_path)
            _YOLO_MODEL_PATH = model_path
        pred = _YOLO_MODEL.predict(source=frame, verbose=False, conf=0.25, imgsz=640)[0]
        detections = []
        for box in pred.boxes:
            cls_id = int(box.cls[0].item())
            label = str(pred.names.get(cls_id, cls_id))
            detections.append({'label': label, 'confidence': round(float(box.conf[0].item()), 3),
                'box': [round(float(v), 1) for v in box.xyxy[0].tolist()]})
        counts = {}
        for d in detections: counts[d['label']] = counts.get(d['label'], 0) + 1
        return jsonify({'ok': True, 'detections': detections, 'counts': counts,
            'notice': 'YOLO detects supported object classes, not necessarily exact retail brands or SKUs. Review and confirm before updating stock.'})
    except ImportError as exc:
        app.logger.exception('YOLO dependencies are missing')
        return jsonify({'ok': False, 'error': 'Camera detection packages are missing. In the project terminal run: python -m pip install -r requirements-vision.txt. Details: ' + str(exc)[:180]}), 503
    except Exception as exc:
        app.logger.exception('YOLO detection failed')
        detail = str(exc).strip().replace('\n', ' ')[:260]
        if 'yolov8n.pt' in str(exc).lower() or 'download' in str(exc).lower() or 'weights' in str(exc).lower():
            hint = ' Model weights may be missing; connect to the internet once so Ultralytics can download yolov8n.pt, or set STOCKSENSE_YOLO_MODEL to a local model file.'
        else:
            hint = ''
        return jsonify({'ok': False, 'error': 'YOLO detection failed: ' + (detail or type(exc).__name__) + hint}), 503

@app.route('/api/scan-confirm', methods=['POST'])
@login_required
def scan_confirm():
    data = request.get_json(silent=True) or {}
    pid = str(data.get('product_id', '')).strip()
    try: qty = int(data.get('quantity', 0))
    except (TypeError, ValueError): qty = 0
    if not pid or qty < 1 or qty > 10000:
        return jsonify({'ok': False, 'error': 'Choose a product and enter a quantity between 1 and 10000.'}), 400
    product = db.get_product(current_uid(), pid)
    if not product:
        return jsonify({'ok': False, 'error': 'Select an existing product from your catalogue.'}), 404
    product['current_stock'] = float(product.get('current_stock') or 0) + qty
    db.upsert_product(product, current_uid())
    return jsonify({'ok': True, 'message': f'Added {qty} units to {product.get("product_name", pid)}.', 'current_stock': product['current_stock']})

# ──────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)