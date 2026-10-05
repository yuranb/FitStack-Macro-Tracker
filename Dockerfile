# FitStack Macro Tracker
#
# The app reads Supabase credentials from Streamlit secrets or the
# SUPABASE_URL / SUPABASE_KEY env vars (see src/app.py::_supabase_config):
#
#   docker run -p 8501:8501 \
#       -e SUPABASE_URL=https://your-project.supabase.co \
#       -e SUPABASE_KEY=your-anon-key \
#       fitstack-macro-tracker
#
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

EXPOSE 8501

# headless: never try to open a browser from inside the container
CMD ["streamlit", "run", "src/app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true"]
