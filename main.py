import sqlite3
import csv
from flask import Flask, request, jsonify, render_template, make_response
from flask_cors import CORS
import openai
import logging
import os
import uuid
from datetime import datetime

# App setup
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
openai.api_key = os.getenv("OpenAIKey")

# Updated Category definitions for additional context in the prompt
category_definitions = {
    'Health & Wellbeing': 'This category focuses on physical, mental, and emotional health, addressing medical concerns, overall wellbeing, and mental health.',
    'Feeding and Nutrition': 'This category includes breastfeeding, formula feeding, introducing solid foods, and questions about nutrition and diet.',
    'Development & Playing': 'This category addresses developmental milestones, physical and cognitive growth, and ideas for play-based learning.',
    'Sleep': 'This category covers sleep routines, sleep training, and managing sleep difficulties for children.',
    'Education': 'This category includes questions about early childhood education, learning strategies, and preparing for school.',
    'Legal & Financial': 'This category addresses legal rights, parental leave, child benefits, and financial planning related to child care.',
    'Travel': 'This category includes travel safety tips, preparing for family vacations, and advice on traveling with a child.',
    'Other': 'This category is for any questions that do not fit into the above categories.'
}

# Blacklist of phrases
blacklist_phrases = [
    "stock market", "bitcoin", "politics", "adult content", "gambling", 
    "crypto", "drugs", "alcohol", "violence", "weapons", "racism", "terrorism",
    "money laundering", "hacking", "illegal activity"
]

# Database and CSV initialization
def init_db():
    try:
        with sqlite3.connect('questions.db') as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    name TEXT,
                    age INTEGER,
                    category TEXT,
                    question TEXT,
                    response TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            logging.info("Database initialized successfully")
    except Exception as e:
        logging.error(f"Error initializing database: {e}")

def init_csv():
    if not os.path.exists('questions.csv'):
        with open('questions.csv', mode='w', newline='') as file:
            csv.writer(file).writerow(['User ID', 'Name', 'Age', 'Category', 'Question', 'Response', 'Timestamp'])

init_db()
init_csv()

# Utility functions
def get_or_set_user_id():
    user_id = request.cookies.get('user_id')
    if not user_id:
        user_id = str(uuid.uuid4())
    return user_id

def save_to_db(user_id, data, answer, timestamp):
    with sqlite3.connect('questions.db') as conn:
        conn.execute('''
            INSERT INTO questions (user_id, name, age, category, question, response, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, data['name'], data['age'], data['category'], data['question'], answer, timestamp))

def save_to_csv(user_id, data, answer, timestamp):
    with open('questions.csv', mode='a', newline='') as file:
        csv.writer(file).writerow([user_id, data['name'], data['age'], data['category'], data['question'], answer, timestamp])

# Flask routes
@app.route('/')
def index():
    user_id = get_or_set_user_id()
    response = make_response(render_template('index.html'))
    response.set_cookie('user_id', user_id, max_age=31536000)
    return response

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()

    # Check if question contains blacklisted phrases
    if any(phrase in data['question'].lower() for phrase in blacklist_phrases):
        return jsonify({'error': 'Your question contains inappropriate content.'}), 400

    # Check if question is too long (max 500 characters or 100 words)
    if len(data['question']) > 500 or len(data['question'].split()) > 100:
        return jsonify({'error': 'Your question is too long. Please limit your question to 500 characters or 100 words.'}), 400

    if not data or not all(key in data for key in ['question', 'name', 'age', 'category', 'additional_notes']):
        return jsonify({'error': 'Missing required data'}), 400

    user_id = get_or_set_user_id()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Get category definition for added context
    category_description = category_definitions.get(data['category'], 'No specific definition available for this category.')

    # Consistent tone and style guidance
    prompt = f"""
    You are a warm, conversational, and supportive parenting and childcare expert well-versed in authoritative sources. A parent has asked you for guidance and provided additional details about their child to ensure they receive the most accurate and tailored advice possible.

    Question about {data['category']} ({category_description}): {data['question']}
    Child's details: Name - {data['name']}, Age - {data['age']} weeks,
    Additional notes: {data['additional_notes']}
    Previous responses (if any): {data.get('previous_responses', '')}

    Please use the following sources where appropriate:
    - NHS (National Health Service): https://www.nhs.uk
    - The Lullaby Trust: https://www.lullabytrust.org.uk
    - National Childbirth Trust (NCT): https://www.nct.org.uk
    - Family Lives: https://www.familylives.org.uk
    - GOV.UK Childcare and Parenting: https://www.gov.uk/browse/childcare-parenting
    - Mayo Clinic: https://www.mayoclinic.org
    - Childcare Choices: https://www.childcarechoices.gov.uk
    - Netmums: https://www.netmums.com
    - Government Parenting and Childcare: https://www.gov.uk/parenting-childcare
    - Family Rights Group: https://www.frg.org.uk
    - World Health Organization (WHO): https://www.who.int/health-topics/maternal-health
    - KidsHealth (Nemours): https://kidshealth.org
    - National Institute for Health and Care Excellence (NICE): https://www.nice.org.uk/guidance
    - BabyCenter: https://www.babycenter.com

    *Important*: Flag responses that require more specific professional advice, and where appropriate, suggest the parent reach out to healthcare professionals or government services. This is particularly relevant for complex legal, medical, or financial questions. 
    Please ensure your response:
    1. Starts with a warm, friendly greeting acknowledging the parent's concern.
    2. Summarizes the key points from the trusted sources related to their question.
    3. Provides at least three actionable steps, if applicable. If the question does not require immediate actions, offer concise, evidence-based information that addresses the query fully.
    4. End with a friendly note, but without a formal sign-off.
    """

    # OpenAI API call
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            temperature=0,
            messages=[
                {"role": "system", "content": "You are a helpful assistant trained to provide detailed and reliable advice on parenting and child healthcare. Use information from specified trusted sources. Maintain a warm, supportive tone."},
                {"role": "user", "content": prompt}
            ]
        )
        answer = response.choices[0].message.content
    except Exception as e:
        return jsonify({'error': f'OpenAI API error: {str(e)}'}), 500

    # Save data
    save_to_db(user_id, data, answer, timestamp)
    save_to_csv(user_id, data, answer, timestamp)

    return jsonify({'response': answer})

if __name__ == '__main__':
    app.run(debug=True)
