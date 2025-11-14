# Restaurant-Ordering-API-FastAPI
Restaurant Ordering API – FastAPI

A complete backend system for restaurants that supports users, restaurants, menu items, carts, and orders.
Built using FastAPI, SQLAlchemy, and Pydantic with PostgreSQL/MySQL/SQLite support via environment-configured DATABASE_URL.

🗂️ Project Structure

├── main.py
├── requirements.txt
├── .env
└── README.md

🚀 Features

👤 User Management

1.Create new users

2.Email 

🏨 Restaurant Module

1.List restaurants

2.View restaurant details

3.Fetch restaurant menu

4.Add menu items

🍔 Menu Module

1.Add new menu items

2.Search menu items

3.Availability filter

🛒 Cart Module

Create cart (guest or user cart)

1.Add items

2.Update quantity

3.Remove items

4.Get cart details

💳 Checkout / Orders

1.Checkout an open cart

2.Auto calculates total

3.Creates order & locks cart


Installation & Setup

1. Clone repo
   
git clone https://github.com/yourusername/restaurant-api.git
cd restaurant-api

3. Create virtual environment

python -m venv venv
source venv/bin/activate     # Linux/Mac
venv\Scripts\activate        # Windows

4. Install dependencies

pip install -r requirements.txt

6. Create .env

DATABASE_URL=sqlite:///./app.db

8. Run server

uvicorn main:app --reload
