# 💱 Currency Converter API

A clean, modular **Flask-based Currency Converter API** that fetches real-time exchange rates using the **Frankfurter API**.

---

## 🚀 Features

* Convert between any two currencies
* Real-time exchange rates
* Clean and scalable project structure
* Error handling for invalid inputs
* Lightweight and easy to extend

---

## 📸 Demo / Preview

![API Demo](assets/demo.png)

---

## 🏗️ Project Structure

```
currency-converter-api/
│
├── app/
│   ├── routes/        # API endpoints
│   ├── services/      # Business logic
│   ├── utils/         # External API calls
│   └── config/        # Configuration
│
├── tests/             # Unit tests
├── run.py             # Entry point
├── requirements.txt
├── README.md
└── documentation.md
```

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/gopal092003/currency-converter-API.git
cd currency-converter-API
```

### 2. Create virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```
---

## ▶️ Run the Application

```bash
python run.py
```

Server will start at:

```
http://127.0.0.1:5000
```

---

## 🔌 API Usage

### ➤ Convert Currency

**Endpoint:**

```
GET /convert
```

**Example Request:**

```
/convert?amount=100&from=USD&to=INR
```

**Example Response:**

```json
{
  "from": "USD",
  "to": "INR",
  "amount": 100,
  "rate": 93.43,
  "converted": 9343
}
```

---

## ⚠️ Error Handling

| Status Code | Description                     |
| ----------- | ------------------------------- |
| 400         | Invalid input (amount/currency) |
| 500         | Internal server error           |

---

## 🧪 Running Tests

```bash
python -m unittest discover tests
```

---

## 📦 Dependencies

* Flask
* Requests

---

## 🔮 Future Improvements

* Add `/currencies` endpoint
* Add caching (Redis / in-memory)
* Batch currency conversion
* Docker support
* Deploy to cloud (Render / AWS)

---

## 🌐 API Reference

Powered by:

* Frankfurter Exchange Rate API

---

## 👨‍💻 Author

**Gopal Gupta**

* GitHub: https://github.com/gopal092003
n
---

## ⭐ Support

If you like this project:

* ⭐ Star the repo
* 🍴 Fork it
* 🧠 Use it in your own projects

---
=======
## References
-[Frankfurter Exchange Rates API](https://frankfurter.dev/)

## Future
- Add `/currencies` endpoint to list supported currencies.
- Support batch conversion (one-to-many).
- Add caching for faster repeated requests.
- Dockerize the application for easy deployment.
