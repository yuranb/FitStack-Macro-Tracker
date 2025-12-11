# Dev Log - FitStack Macro Tracker

Started: Nov 25, 2025  
Total time spent: ~57 hours (probably more if I count all the time spent debugging...)

---

## Nov 25 - Day 1 (3h)

Decided on project idea - nutrition tracker for my fitness goals. Spent way too long looking at MyFitnessPal and other apps to see what features they have.

**What I'm building:**
- Track what I eat each day
- Calculate macros automatically 
- Set daily goals
- Maybe add some charts if I have time

**Tech decisions:**
- Streamlit for frontend (looks easy to learn)
- Supabase for database (free PostgreSQL!)
- Plotly for charts maybe?

Originally wanted Flask but Streamlit seems better for data stuff.

---

## Nov 26 - Day 2 (4h)

Spent the whole day learning Streamlit. Did the tutorial and made a simple calculator to practice.

The weird thing about Streamlit is it reruns the ENTIRE script every time you click something. Took me forever to figure out why my variables kept disappearing lol. Turns out you need `st.session_state` for that.

Learned: `st.button`, `st.selectbox`, `st.columns`, etc.

---

## Nov 27 - Day 3 (3h)

Set up Supabase account. Their interface is actually pretty nice.

Drew database design on paper:
- foods table (or should it be products?)
- logs table to track daily intake
- maybe a goals table?

Decided to store nutrition per 100g since that's how most nutrition labels work.

Also learned some PostgreSQL basics from the Supabase docs.

---

## Nov 28 - Day 4 (2h)

Environment setup day. Ran into the stupid pip issue on Windows - turns out you have to use `py -m pip` instead of just `pip`. Why is Windows like this...

Installed:
- streamlit
- supabase (the Python client)
- pandas
- plotly

Got my first successful connection to Supabase! Felt good.

---

## Nov 29 - Day 5 (4h)

Redesigned the database. Added a user_goals table and renamed foods → products (sounds more professional).

```
products: name, cals, protein, carbs, fat
daily_logs: product_id, quantity, date
user_goals: daily targets for each macro
```

Wrote the schema.sql file. Added foreign keys to link logs to products.

**Problem:** Forgot to add indexes at first. Queries were super slow when testing. Added indexes on log_date and product_id - much better now.

---

## Nov 30 - Day 6 (3h)

Spent hours collecting nutrition data for 24 different foods. Found most of it on USDA database and some nutrition websites.

Categories:
- Meats (chicken, beef, salmon, etc.)
- Dairy/eggs  
- Grains (rice, oats, bread)
- Veggies
- Protein powder and supplements
- Fruits

Ran the INSERT statements in Supabase. All loaded correctly!

---

## Dec 1 - Day 7 (4h)

Started writing app.py. This is the main file with all the Streamlit code.

Got the Supabase connection working using secrets.toml (for API keys).

Wrote a function to fetch all products from database. Used `@st.cache_data` because I learned that caching can help with performance. Set TTL to 300 seconds (5 min).

**Key learning:** Difference between `@st.cache_resource` (for connections) vs `@st.cache_data` (for data). Got confused at first.

---

## Dec 2 - Day 8 (4h)

Built the "add food" feature today.

Made a dropdown with all the foods, then a number input for quantity. Added a preview box that shows nutrition before you add it - thought that would be helpful.

Struggled with the format_func parameter in selectbox. Wanted to show "Chicken Breast (165 kcal/100g)" but kept getting errors. Finally got it working.

Also wrote the add_food_log() function to INSERT into database.

---

## Dec 3 - Day 9 (3h)

Today: show what you've eaten so far

Wrote get_todays_logs() - uses Supabase's nested query thing to get product info along with the logs. Pretty cool feature actually.

Display each log as a row with a delete button. 

**Issue:** All the delete buttons had the same key and Streamlit was throwing errors. Fixed by using `key=f"del_{log['id']}"` - each button needs unique key.

---

## Dec 4 - Day 10 (4h)

Nutrition calculation time!

Made a calculate_daily_totals() function that loops through all of today's logs and sums up the macros. Had to account for the fact that nutrition is stored per 100g, so I calculate a ratio first.

Then added the 4 metric cards at top:
- Calories
- Protein  
- Carbs
- Fat

Each one shows your total vs goal, plus a progress bar.

**Bug:** Progress bars crash if you go over 100%. Fixed with `min(percentage, 100)`.

---

## Dec 5 - Day 11 (3h)

Goal settings feature.

Added a form in the sidebar where you can change your daily targets. Update button that saves to database and clears the cache.

**Important:** Have to call `get_user_goals.clear()` after updating or the UI won't show the new values (because they're cached).

Also added a date picker so you can view past days. Max date is today (can't log future meals).

---

## Dec 6 - Day 12 (4h)

Historical data charts! This is the P2 feature for extra credit.

Wrote get_week_data() to fetch past 7 days of logs.

Then I loop through each day and calculate totals for that day. Even if there's no data for a day, I still add it to the array with 0 values (so the chart doesn't have gaps).

Made 2 charts with Plotly:
1. Bar chart for calories with a red line showing goal
2. Line chart for protein/carbs/fat trends

Plotly was easier than I expected actually.

---

## Dec 7 - Day 13 (2h)

UI improvements day.

Added custom CSS to make it look nicer:
- Gradient colors for header
- Better progress bar colors
- Some spacing adjustments

Added emojis everywhere (🔥 💪 🥩 etc.) - makes it more fun

---

## Dec 8 - Day 14 (3h)

Testing and bug fixing.

Found issues:
- Empty dataframes causing errors → added `.empty` checks
- Division by zero when goals are 0 → added conditional checks
- Date format inconsistencies → switched to ISO format everywhere

Also realized I should add try-except blocks around database calls. Added error handling to all the functions.

---

## Dec 9 - Day 15 (3h)

Documentation time. Not the fun part but necessary.

Wrote README with:
- What the project does
- How the database is designed
- Caching strategy explanation
- How to run it

Also added lots of comments to the code explaining the tricky parts.

---

## Dec 10 - Day 16 (8h) 

Final push! 

Went through everything one more time:
- Tested all features end-to-end
- Fixed a few small bugs I found
- Cleaned up code organization
- Made sure constants are defined at top
- Checked that all variable names make sense

Added input validation (quantity must be > 0 and < 10000g).

Wrote this progress log (took longer than expected lol).

Updated requirements.txt with specific version numbers.

**Lessons learned:**
1. Caching is super important for performance
2. Streamlit reruns everything - use session_state when needed
3. Foreign keys and indexes make a huge difference
4. Always add error handling from the start (not at the end like I did)
5. Test with empty states - found so many bugs that way

**What could be better:**
- Could add user authentication for multiple users
- Meal categorization (breakfast/lunch/dinner)
- Barcode scanning would be cool
- Export data to CSV

But overall pretty happy with how it turned out! Learned a ton about databases, caching, and full-stack development.

---

## Summary

**Total hours:** ~57 hours across 16 days

**What I built:**
- 3 database tables with proper relationships
- Full CRUD operations  
- Cache-Aside caching strategy
- Streamlit web interface with charts
- 24 pre-loaded foods

**Main technologies:**
- Python/Streamlit for frontend
- PostgreSQL (via Supabase) for database
- Plotly for visualization

**Biggest challenges:**
- Understanding Streamlit's execution model
- Getting caching right (when to cache, when not to)
- Database query optimization
- Error handling for all edge cases

**What I learned:**
- How to design a relational database properly
- Cache-Aside strategy and when to use it
- Full-stack app development from scratch
- Importance of indexes for query performance
- Input validation and error handling best practices

