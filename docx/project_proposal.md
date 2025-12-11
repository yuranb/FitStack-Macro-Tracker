# Project Proposal - FitStack Macro Tracker

## What I'm Building

A simple nutrition tracker to log daily food intake and track macros (calories, protein, carbs, fat).

## Why

I want to track what I eat for fitness goals. Existing apps are too complicated.

## Features (Initial Plan)

**Must have:**
- Log food with quantity
- Show daily totals
- Set nutrition goals

**Maybe later:**
- Charts for weekly trends

## Tech Stack

- Streamlit (frontend)
- Supabase/PostgreSQL (database)
- Plotly (charts)

## Database Design (Rough)

```
products: id, name, calories, protein, carbs, fat
    ↓
daily_logs: id, product_id (FK), quantity, date
    
user_goals: id, daily_calories, daily_protein, daily_carbs, daily_fat
```

## Timeline

- Week 1: Learn Streamlit, design database
- Week 2: Build core features (add food, show logs)
- Week 3: Add goals, charts, testing

## Questions

- How to handle caching?
- Should I add user authentication?

---

*Initial thoughts - will figure out details as I go*
