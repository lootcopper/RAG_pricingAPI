# sedai-llm-pricing-api

## Project Structure

The project is organized as follows:

```
.
├── app/                  # Core application logic
│   ├── api/              # FastAPI routing, schemas, and dependencies
│   ├── db/               # Database connection and repository functions
│   ├── models.py         # SQLAlchemy ORM models
│   └── scheduler.py      # Logic for discovering and scheduling scrapers
│
├── scrapers/             # Pluggable scraper implementations
│   ├── base.py           # Abstract base class for all scrapers
│   └── example_scraper.py # An example scraper implementation
│
├── scripts/              # Utility scripts
│   └── create_db.py
│
├── tests/                # Tests
│
├── main.py               # FastAPI app entry point and scheduler startup
└── requirements.txt      # Project dependencies
```

## Setup and Initialization

Follow these steps to set up the project environment and initialize the database.

### 1. Create a Virtual Environment

It is recommended to use a Python virtual environment to manage dependencies.

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

Install all required Python packages from the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 3. Initialize the Database

Before running the application for the first time, you must create the database and its tables. Run the following command from the project's root directory:

```bash
python -m scripts.create_db
```

This will create a `database.db` file in the root directory with the required table schemas.

## Running the Application

To run the FastAPI server, use uvicorn:

```bash
uvicorn main:app --reload
```

This will start the server, typically on http://127.0.0.1:8000.

## Adding a New Scraper

To add a new data source, create a new Python file in the `scrapers/` directory. Inside this file, create a class that inherits from `scrapers.base.BaseProviderModelScraper` and implement the `scrape()` method. The scheduler will automatically discover and run your new scraper on the next startup.

## API Documentation

You can access the automatically generated API documentation at:
```
http://127.0.0.1:8000/docs
```
