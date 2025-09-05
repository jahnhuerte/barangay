import mysql.connector
import pickle
import numpy as np
from tensorflow.keras.models import load_model

def get_database_connection():
    return mysql.connector.connect(
        host='localhost', user='root', password='', database='barangay_db'
    )

# Load pre-trained model and encoders
model = load_model('rnn_recommendation_model.h5')
with open('label_encoders.pkl', 'rb') as f:
    label_encoders = pickle.load(f)
with open('scaler.pkl', 'rb') as f:
    scaler = pickle.load(f)

def get_high_priority_needs(cursor):
    """Identify barangay needs based on trends in requests and blotter reports."""
    cursor.execute("""
        SELECT 'job_fair' AS program, COUNT(*) AS count FROM business_clearances WHERE purpose LIKE '%job%'
        UNION ALL
        SELECT 'crime_prevention' AS program, COUNT(*) FROM blotters WHERE status = 'unresolved'
    """)
    trends = cursor.fetchall()
    return {row[0]: row[1] for row in trends if row[1] > 10}  # Set threshold for priority

def recommend_programs():
    db = get_database_connection()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM residents WHERE programID IS NULL")
    residents = cursor.fetchall()
    
    priority_needs = get_high_priority_needs(cursor)
    
    for resident in residents:
        features = np.array([[
            resident['age'],
            resident['isOccupation'],
            resident['pwd'],
            resident['isBeneficiaries']
        ]])
        features = scaler.transform(features)
        prediction = model.predict(features)
        recommended_program = np.argmax(prediction)
        
        if 'job_fair' in priority_needs:
            recommended_program = 'job_fair'
        elif 'crime_prevention' in priority_needs:
            recommended_program = 'crime_prevention'
        
        cursor.execute("UPDATE residents SET programID = %s WHERE id = %s", (recommended_program, resident['id']))
        db.commit()
        send_notification(resident['id'], recommended_program)
    
    cursor.close()
    db.close()

def send_notification(resident_id, program):
    """Send real-time notification to the resident."""
    db = get_database_connection()
    cursor = db.cursor()
    cursor.execute("INSERT INTO notifications (resident_id, message) VALUES (%s, %s)",
                   (resident_id, f'New recommended program: {program}'))
    db.commit()
    cursor.close()
    db.close()

if __name__ == "__main__":
    recommend_programs()
