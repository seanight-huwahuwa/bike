from flask import Flask, render_template_string, request, jsonify
import pyodbc
import os
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Azure OpenAI Client - lazy initialization
openai_client = None

def get_openai_client():
    global openai_client
    if openai_client is None:
        openai_client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-08-01-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
    return openai_client

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
            body { font-family: Arial, sans-serif; max-width: 900px; margin: 50px auto; padding: 20px; }
            h1 { color: #2c3e50; }
            h2 { color: #34495e; margin-top: 30px; }
            .bike-card { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .bike-card h3 { color: #3498db; margin: 0 0 10px 0; }
            .price { color: #27ae60; font-weight: bold; font-size: 1.2em; }
            .type { background: #ecf0f1; padding: 5px 10px; border-radius: 3px; display: inline-block; }
            .ai-section { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 30px 0; }
            #questionInput { width: 100%; padding: 10px; font-size: 16px; border: 1px solid #ddd; border-radius: 4px; }
            #askBtn { background: #3498db; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; margin-top: 10px; }
            #askBtn:hover { background: #2980b9; }
            #recommendation { margin-top: 20px; padding: 15px; background: white; border-left: 4px solid #3498db; border-radius: 4px; white-space: pre-wrap; }
            .loading { display: none; color: #3498db; margin-top: 10px; }
        </style>
    </head>
    <body>
        <h1>🚴 Bike Recommendation System</h1>
        <p>Welcome to our Azure-powered bike catalog with AI recommendations!</p>
        
        <div class="ai-section">
            <h2>🤖 AI Bike Advisor</h2>
            <p>Ask our AI assistant to help you find the perfect bike!</p>
            <input type="text" id="questionInput" placeholder="Example: I need a bike for daily commuting in the city, budget around $400">
            <button id="askBtn" onclick="getRecommendation()">Get AI Recommendation</button>
            <div class="loading" id="loading">🔄 Thinking...</div>
            <div id="recommendation"></div>
        </div>
        
        <h2>📋 Available Bikes</h2>
        <div id="bikes"></div>
        
        <script>
            // Load bikes
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
            
            // AI Recommendation
            function getRecommendation() {
                const question = document.getElementById('questionInput').value;
                if (!question.trim()) {
                    alert('Please enter your requirements!');
                    return;
                }
                
                document.getElementById('loading').style.display = 'block';
                document.getElementById('recommendation').innerHTML = '';
                document.getElementById('askBtn').disabled = true;
                
                fetch('/api/recommend', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({question: question})
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('askBtn').disabled = false;
                    if (data.error) {
                        document.getElementById('recommendation').innerHTML = '❌ Error: ' + data.error;
                    } else {
                        document.getElementById('recommendation').innerHTML = '💡 ' + data.recommendation;
                    }
                })
                .catch(error => {
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('askBtn').disabled = false;
                    document.getElementById('recommendation').innerHTML = '❌ Error: ' + error;
                });
            }
            
            // Allow Enter key to submit
            document.getElementById('questionInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') getRecommendation();
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

@app.route("/api/recommend", methods=['POST'])
def recommend():
    try:
        data = request.json
        user_input = data.get('question', '')
        
        # Get all bikes from database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT name, type, price, description FROM bikes')
        bikes = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Format bikes data for AI
        bikes_info = "\n".join([
            f"- {bike[0]} ({bike[1]}): ${bike[2]} - {bike[3]}"
            for bike in bikes
        ])
        
        # Create prompt for OpenAI
        system_message = f"""You are a helpful bike recommendation assistant. 
Here are the available bikes:
{bikes_info}

Based on the customer's needs, recommend the most suitable bike(s) and explain why."""
        
        # Call Azure OpenAI
        client = get_openai_client()
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_input}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        recommendation = response.choices[0].message.content
        
        return jsonify({'recommendation': recommendation})
    except Exception as e:
        return jsonify({'error': str(e)}), 500