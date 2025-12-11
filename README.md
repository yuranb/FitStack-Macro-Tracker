# FitStack Macro Tracker 💪

A nutrition tracking application built for my Database Modeling course final project. Tracks daily macronutrient intake with PostgreSQL backend and caching layer.

**Development Time**: 57 hours

## 🎯 What It Does

**Core Features:**
- Log daily food intake with portion sizes
- Real-time calculation of calories, protein, carbs, and fat
- Set and track daily nutritional goals
- View 7-day intake trends with charts

## 🗄️ Database Design

Built around three relational tables in PostgreSQL:

**products** → **daily_logs** ← **user_goals**

- `products`: Food/supplement nutritional data (24 items pre-loaded)
- `daily_logs`: Daily intake records (foreign key to products)
- `user_goals`: User's daily nutritional targets

**Key design choices:**
- Foreign key constraint with `ON DELETE CASCADE`
- Indexes on `log_date` and `product_id` for query optimization
- `DECIMAL` type for nutritional values (precision matters)

## 🔄 Caching Strategy (Cache-Aside)

Implemented using Streamlit's `@st.cache_data` decorator:

```python
@st.cache_data(ttl=300)  # 5 min TTL
def get_foods():
    # Products rarely change, safe to cache
    
@st.cache_data(ttl=60)   # 1 min TTL  
def get_goals():
    # Goals might be updated more frequently

def get_todays_logs(date):
    # NOT cached - logs change throughout the day
```

**Purpose:** Reduce database read load by caching static/semi-static data.

## 🛠️ Tech Stack

- **Frontend:** Streamlit (Python)
- **Database:** Supabase (hosted PostgreSQL)
- **Visualization:** Plotly
- **Caching:** Streamlit cache layer

## 🚀 Running the App

```bash
# Install dependencies
py -m pip install -r requirements.txt

# Configure .streamlit/secrets.toml with your Supabase credentials
# Run schema.sql in Supabase SQL Editor
# Start app
py -m streamlit run src/app.py
```

## 📊 Database Schema

```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    calories DECIMAL(8,2),
    protein DECIMAL(8,2),
    carbs DECIMAL(8,2),
    fat DECIMAL(8,2),
    serving_unit VARCHAR(20)
);

CREATE TABLE daily_logs (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    quantity DECIMAL(8,2),
    log_date DATE
);

CREATE INDEX idx_daily_logs_date ON daily_logs(log_date);
CREATE INDEX idx_daily_logs_product ON daily_logs(product_id);
```

## 📁 Project Structure

```
├── docx/schema.sql       # Database schema + seed data
├── src/app.py            # Main application (450 lines)
├── requirements.txt      # Python dependencies
└── progress_log.md       # Development log
```

## 💡 What I Learned

**Database concepts:**
- Relational database design with foreign keys
- Query optimization with indexes
- Trade-offs between normalization and query complexity

**Caching:**
- When to cache (static data) vs. when not to (dynamic data)
- TTL considerations based on data volatility
- Cache invalidation strategies

**Full-stack development:**
- Complete CRUD operations
- Input validation and error handling
- Connecting frontend to PostgreSQL backend
