# Test Flask Application

A basic Flask web application created for testing purposes.

## Project Structure
```
test/
├── app.py              # Main application file
├── requirements.txt    # Project dependencies
├── static/            # Static files directory
│   ├── css/          # CSS files
│   └── js/           # JavaScript files
└── templates/         # HTML templates
```

## Setup Instructions

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Open your browser and navigate to `http://localhost:5000`

## Dependencies
- Flask 3.0.0
- Werkzeug 3.0.1
- Jinja2 3.1.2
