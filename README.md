# auto-parts-data-warehouse

Data warehouse and ETL pipeline for auto parts sales data. Loads raw Excel sources into a `staging` schema, then builds `core` and `marts` schemas via SQL.

## Requirements

- Python 3.10+
- Docker (for the local Postgres instance)

## Setup

1. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the project root with the database configuration:

   ```env
   DB_ENGINE=postgresql+psycopg2
   DB_USER=newuser
   DB_PASSWORD=password
   DB_NAME=autoparts
   DB_HOST=localhost
   DB_PORT=5432
   ```

3. Start the Postgres container:

   ```bash
   docker compose up -d
   ```

## Running the pipeline

Run the full ETL from the project root:

```bash
python run_pipeline.py
```

This will:

1. Load the raw Excel files under `docs/` into the `staging` schema (Python ETL).
2. Execute every `*.sql` file in `sql/core/` in alphabetical order.
3. Execute every `*.sql` file in `sql/marts/` in alphabetical order.
