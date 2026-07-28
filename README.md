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

The run is idempotent: `sql/core/01-schema.sql` drops and recreates the `core`
schema, and every marts file drops its tables before rebuilding them.

## Business-question report

`sql/marts/` materializes one or more tables per business question — see
[`sql/marts/README.md`](sql/marts/README.md) for the question-to-table mapping.

To produce the PDF report that answers all of them from those tables:

```bash
python reports/generate_report.py
```

It queries the `marts` schema live and writes
`reports/Informe_Preguntas_Negocio.pdf`, so the report always reflects the last
pipeline run. Requires `reportlab` and `matplotlib` (see `requirements.txt`).
