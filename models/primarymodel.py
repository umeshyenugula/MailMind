# primarymodel.py

import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
import pickle

MODEL_PATH = "spam_classifier_model.pkl"
VECTORIZER_PATH = "vectorizer.pkl"

def train_model():
    print("[INFO] Training model from dataset...")
    df = pd.read_csv('datapreprocessing/processeddataset/processed.csv')
    df['comt'] = df['body'] + ' ' + df['subject']
    X = df['comt']
    y = df['is_spam']
    vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
    X_tfidf = vectorizer.fit_transform(X)
    model = MultinomialNB()
    model.fit(X_tfidf, y)
    with open(MODEL_PATH, 'wb') as model_file:
        pickle.dump(model, model_file)
    with open(VECTORIZER_PATH, 'wb') as vec_file:
        pickle.dump(vectorizer, vec_file)
    print("[INFO] Training complete. Model saved.")

def load_model_and_vectorizer():
    if not os.path.exists(MODEL_PATH) or not os.path.exists(VECTORIZER_PATH):
        train_model()
    with open(MODEL_PATH, 'rb') as model_file:
        model = pickle.load(model_file)
    with open(VECTORIZER_PATH, 'rb') as vec_file:
        vectorizer = pickle.load(vec_file)
    return model, vectorizer

def classify_emails(useremails):
    model, vectorizer = load_model_and_vectorizer()
    test_df = pd.DataFrame(useremails)
    if test_df.empty:
        return []
    test_df['subject'] = test_df.get('subject', '(No Subject)')
    test_df['body'] = test_df.get('body', '(No Body)')
    test_df['combined_text'] = test_df['body'].fillna('') + ' ' + test_df['subject'].fillna('')
    X_test_tfidf = vectorizer.transform(test_df['combined_text'])
    predictions = model.predict(X_test_tfidf)
    result = []
    for i, email in test_df.iterrows():
        result.append({
            'subject': email['subject'],
            'body': email['body'],
            'prediction': 'Spam' if predictions[i] == 1 else 'Not Spam'
        })
    return result   # ✅ FIXED HERE
