# 💰 Budget Tracker | Smart Expense Manager

A modern Django-based financial management web application designed to help users track expenses, manage budgets, analyze spending habits, and achieve financial goals efficiently.

---

# 📌 Overview

Budget Tracker helps users organize their personal finances through a clean and interactive dashboard.

The system allows users to:
- Track income & expenses by category
- Set budgets with smart alerts before overspending
- Visualize spending using charts and analytics
- Create financial goals and monitor savings progress
- Export transaction history as CSV
- Manage accounts securely with full authentication features

---

# 🚀 Features

## 🔐 Authentication System
- User Signup with email validation
- Secure Login & Logout
- Password change functionality
- Account deletion support

---

## 👤 User Profile
- Update profile information
- View financial summary
- Track balance, income, and expenses
- Secure password management

---

## 💸 Transactions Management
- Add income transactions
- Add expense transactions
- Edit & delete transactions
- Categorize financial records
- Search transactions
- Filter by transaction type
- Paginated transaction history

---

## 📊 Financial Dashboard
- Financial overview dashboard
- Real-time balance calculation
- Recent transactions section
- Active goals preview

---

## 📈 Data Analysis
- Expense analysis by category
- Income vs expense comparison
- Interactive financial charts using Chart.js

---

## 📂 Category Management
- Dynamic category creation
- Custom category support
- Organized expense classification

---

## 💰 Budget Management
- Create budgets per category
- Spending vs budget tracking
- Budget progress monitoring
- Over-budget detection & alerts
- Visual progress indicators

---

## 🎯 Financial Goals System
- Create saving goals
- Track savings progress
- Update saved amount dynamically
- Deadline support

---

## 🔔 Notification System
- Smart budget alerts
- Overspending warnings
- Real-time financial notifications

---

## 📤 Export System
- Export transactions as CSV files

---

## ⚡ Dynamic Features
- AJAX-powered interactions
- Fetch API integration
- JSON-based communication
- Responsive user experience

---

# 🛠️ Tech Stack

### Backend
- Python
- Django
- Django REST Framework (DRF)

### Frontend
- HTML5
- CSS3
- Vanilla JavaScript
- Chart.js

### Database
- SQLite3

### Additional Libraries
- django-cors-headers
- python-decouple

---


# ⚙️ Installation

## 1️⃣ Clone Repository

```bash
git clone <your-repository-link>
```

---

## 2️⃣ Navigate to Project Folder

```bash
cd Budget-Tracker
```

---

## 3️⃣ Create Virtual Environment

```bash
python -m venv venv
```

---

## 4️⃣ Activate Virtual Environment

### Windows
```bash
venv\Scripts\activate
```

### Mac/Linux
```bash
source venv/bin/activate
```

---

## 5️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🔐 Environment Variables

This project uses `python-decouple` for configuration management.

Create a `.env` file in the root directory and add:

```env
SECRET_KEY=your_secret_key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CORS_ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
```

---

# 🗄️ Database Setup

Run the following commands:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

---

# ▶️ Run Project

Start the development server:

```bash
python manage.py runserver
```

Then open:

```text
http://127.0.0.1:8000/
```

---

# 🔗 API Endpoints

This project uses **Django REST Framework (DRF)** with **Fetch API** to enable dynamic frontend-backend communication.

The API layer supports:
- JSON responses
- Real-time UI updates
- Frontend integration
- Dynamic financial operations

---

## 📦 API Modules

### 💸 Transactions API
- Create transactions
- Update transactions
- Delete transactions
- Retrieve transaction history

---

### 💰 Income & Expense API
- Income tracking
- Expense tracking
- Dashboard analytics integration

---

### 📊 Budget API
- Create budgets
- Budget monitoring
- Spending analysis
- Over-budget detection

---

### 🎯 Goals API
- Create financial goals
- Update savings progress
- Goal tracking system

---

### 🔔 Notifications API
- Budget alerts
- Overspending warnings
- Real-time notifications

---

## 🌐 Frontend Communication Example

```javascript
fetch('/api/endpoint/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(data)
})
.then(response => response.json())
.then(data => {
    console.log(data);
});
```

---

# 🧠 System Architecture Flow

1. Frontend sends requests using Fetch API  
2. Django REST Framework handles requests  
3. Serializers convert models ↔ JSON  
4. Backend processes business logic  
5. JSON response is returned dynamically  

---

# 🔮 Future Improvements

The project can be enhanced further with:

- AI-powered financial insights
- Spending prediction system
- PDF financial reports
- Mobile application version
- Multi-currency support
- Recurring transactions system
- Push & email notifications
- Advanced analytics dashboard
- Two-factor authentication (2FA)
- Dark mode support

---

# 👨‍💻 Team Members

- **Mariam Sayed Ramadan** — S5 — 20242327
- **Mahmoud Mohamed** — S5 — 20250913
- **Khaled Ali** — S5 — 20240178
- **Ayat Ali** — S18 — 20242060

---

# 📄 License

This project is licensed for educational purposes.

---

# ⭐ Project Highlights

- Full Stack Django Application
- REST API Integration
- Interactive Financial Dashboard
- Real-Time Budget Alerts
- Clean & Responsive UI
- Secure Authentication System
- Modular & Scalable Architecture