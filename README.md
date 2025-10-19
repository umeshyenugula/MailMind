# 25AACR13

# Mailmind – Mail to Agenda
<img width="200" height="68" alt="Screenshot 2025-10-18 at 2 54 15 PM" src="https://github.com/user-attachments/assets/45c65345-42a8-405b-ae27-6ee52f513d17" />

## Table of Contents
- [Introduction](#introduction)
- [Requirements](#requirements)
- [How to use](#installation-and-usage)
- [Preview](#preview)
- [Team](#team-details)
- [Contribution](#contribution)
- [Improvements](#improvements)

---

## Introduction
**Mailmind – Mail to Agenda** is an AI-powered email automation system that classifies non-spam emails into **event-based** and **non-event-based** categories.  
Event-based emails are automatically added to **Google Calendar**, while non-event-based emails are **sorted by priority** for better inbox management.  

Built with **Python, NLP, Machine Learning, and Google APIs**, Mailify transforms the chaos of daily emails into structured, actionable information — a tool for anyone who values organization and time.

---

## Requirements
| Dependency | Version |
|-------------|----------|
| Python | 3.10 or above |
| pandas | ≥ 1.5.0 |
| numpy | ≥ 1.21.0 |
| scikit-learn | ≥ 1.7.0 |
| google-auth | ≥ 2.0.0 |
| google-auth-oauthlib | ≥ 0.8.0 |
| google-auth-httplib2 | ≥ 0.1.0 |
| google-api-python-client | ≥ 2.0.0 |
| firebase-admin | ≥ 6.2.0 |
| spacy | ≥ 3.5.0 |
| transformers | ≥ 4.20.0 |
| torch | ≥ 1.12.0 |
| beautifulsoup4 | ≥ 4.11.0 |
| requests | ≥ 2.28.0 |
| google-generativeai | ≥ 0.3.0 |
| flask | ≥ 2.3.0 |
| flask-cors | ≥ 4.0.0 |
| python-dotenv | ≥ 0.19.0 |

> All dependencies are listed in the `requirements.txt` file for easy installation.

---

## Installation and Usage

he list of dependencies and versions is available in the file [`requirements.txt`](./requirements.txt).  
To install all the required dependencies, simply run:

```bash
pip install -r requirements.txt
```
Ensure that Python and Node.js are installed on your system before running the project.

Installation & Usage
Follow these steps to set up and run the project on your local machine:

## How to Use

Follow these steps to install and run the project on your local machine:


## Step 1: Clone the Repository
git clone https://github.com/yourusername/mailify.git
cd mailify

## Step 2: Set Up Python Environment
python -m venv venv
## macOS/Linux
source venv/bin/activate
## Windows
venv\Scripts\activate

## Step 3: Install Python Dependencies
pip install -r requirements.txt

## Step 4: Install Node Modules (for frontend)
npm install

## Step 5: Configure Google Calendar API
 1. Go to Google Cloud Console: https://console.cloud.google.com/
 2. Enable Google Calendar API.
 3. Create credentials and download the credentials.json file.
 4. Place the file in the root directory of the project.
 5. Set up OAuth permissions as required.

## Step 6: Run the Backend
python main.py

## Step 7: Run the Frontend
npm start

## Step 8: Access the Application
 Open your browser and visit http://localhost:3000
 The system will:
 - Classify non-spam emails into event-based and non-event-based.
 - Automatically add event-based emails to Google Calendar.
 - Prioritize non-event-based emails.
---
## Preview

Screenshots of the project will be added manually. Replace the placeholders with actual image paths.

| Screenshot | Description |
|------------|-------------|
|<img width="1451" height="658" alt="Screenshot 2025-10-18 at 3 00 16 PM" src="https://github.com/user-attachments/assets/74a05a3b-81f6-4c87-b396-d1e2382f391e" />| Main dashboard of Mailify |
| <img width="1069" height="601" alt="Screenshot 2025-10-18 at 3 04 21 PM" src="https://github.com/user-attachments/assets/91fc9e09-3baf-41ce-9cef-0dad7e31caef" />| Event added to Google Calendar |

---

## Team Details

| Role | Name |
|------|------|
| Team Number | 25AACR13 |
| Senior Mentor | Siddharth Mahesh |
| Junior Mentor | Aluri Surya Teja |
| Team Member 1 | Vinjanampati Raga Gowtami |
| Team Member 2 | Umesh Chandra Yenugula|
| Team Member 3 | Harshith Gottipati |
| Team Member 4 | K. Bhanu Prakash |
| Team Member 5 | Rida Md |

---

## Contribution

We welcome contributions to improve Mailmind. Please follow these guidelines:

1. Read the README.md and understand the project’s goal and workflow.
2. Use the same programming languages and dependency versions as in the project.
3. Document your proposed changes clearly, including any issues you found, your solution, and test cases.
4. Submit a pull request following proper [Git etiquettes](https://gist.github.com/mikepea/863f63d6e37281e329f8).

---

## Improvements

Mailmind aims to expand into a full-featured productivity assistant. Future improvements may include:

- Integration with additional email services (Outlook, Yahoo, etc.)
- Advanced NLP for smarter event detection and sentiment analysis
- Real-time Google Calendar synchronization with reminders
- AI-generated summaries of email threads
- Analytics dashboard for tracking email and productivity trends
- Cross-platform UI for desktop and mobile notifications
