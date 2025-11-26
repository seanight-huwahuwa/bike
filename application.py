from flask import Flask, render_template_string, request, jsonify
import pyodbc
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Database connection function
def get_db_connection():
    conn_str = os.getenv('SQL_CONNECTION_STRING')
    return pyodbc.connect(conn_str)

# Initialize database tables
def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create bikes table if not exists
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='bikes' AND xtype='U')
            CREATE TABLE bikes (
                id INT IDENTITY(1,1) PRIMARY KEY,
                name NVARCHAR(100) NOT NULL,
                type NVARCHAR(50) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                description NVARCHAR(500)
            )
        ''')
        
        # Insert sample data if table is empty
        cursor.execute('SELECT COUNT(*) FROM bikes')
        if cursor.fetchone()[0] == 0:
            sample_bikes = [
                ('City Cruiser', 'City', 299.99, 'Perfect for urban commuting'),
                ('Mountain Explorer', 'Mountain', 599.99, 'Built for off-road adventures'),
                ('Road Racer', 'Road', 899.99, 'High-performance road bike'),
                ('Folding Compact', 'Folding', 399.99, 'Portable and space-saving'),
                ('Electric E-Bike', 'Electric', 1499.99, 'Powered assistance for easy riding')
            ]
            cursor.executemany(
                'INSERT INTO bikes (name, type, price, description) VALUES (?, ?, ?, ?)',
                sample_bikes
            )
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Database initialization error: {e}")

# Initialize DB on startup
init_db()

@app.route("/")
def index():
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Bike Recommendation System</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #2c3e50; }
            .bike-card { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .bike-card h3 { color: #3498db; margin: 0 0 10px 0; }
            .price { color: #27ae60; font-weight: bold; font-size: 1.2em; }
            .type { background: #ecf0f1; padding: 5px 10px; border-radius: 3px; display: inline-block; }
        </style>
    </head>
    <body>
        <h1>🚴 Bike Recommendation System</h1>
        <p>Welcome to our Azure-powered bike catalog!</p>
        <h2>Available Bikes</h2>
        <div id="bikes"></div>
        
        <script>
            fetch('/api/bikes')
                .then(response => response.json())
                .then(bikes => {
                    const container = document.getElementById('bikes');
                    bikes.forEach(bike => {
                        container.innerHTML += `
                            <div class="bike-card">
                                <h3>${bike.name}</h3>
                                <span class="type">${bike.type}</span>
                                <p>${bike.description}</p>
                                <div class="price">$${bike.price}</div>
                            </div>
                        `;
                    });
                });
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route("/api/bikes")
def get_bikes():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, type, price, description FROM bikes')
        
        bikes = []
        for row in cursor.fetchall():
            bikes.append({
                'id': row[0],
                'name': row[1],
                'type': row[2],
                'price': float(row[3]),
                'description': row[4]
            })
        
        cursor.close()
        conn.close()
        return jsonify(bikes)
    except Exception as e:
        return jsonify({'error': str(e)}), 500