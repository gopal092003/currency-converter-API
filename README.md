# Currency Converter API

A REST API built with Flask for converting currencies using real-time exchange rates from the Frankfurter Exchange Rates API. The project follows a modular architecture with separate layers for routing, business logic, configuration, and external API integration, making it easy to maintain and extend.

---

## Features

- Convert between supported currencies using live exchange rates
- Real-time data powered by the Frankfurter API
- Modular and maintainable project structure
- Input validation and error handling
- Lightweight and easy to extend

---

## Tech Stack

- Flask
- Requests
- Frankfurter Exchange Rates API

---

## Project Structure

```
currency-converter-api/
│
├── app/
│   ├── config/         # Application configuration
│   ├── routes/         # API endpoints
│   ├── services/       # Business logic
│   └── utils/          # External API integration
│
├── tests/              # Unit tests
├── documentation.md
├── requirements.txt
├── run.py
└── README.md
```

---

## Getting Started

### Clone the Repository

```
git clone https://github.com/gopal092003/currency-converter-API.git

cd currency-converter-API
```

### Create a Virtual Environment

```
python -m venv venv
```

Activate the environment:

**Windows**

```
venv\Scripts\activate
```

**Linux / macOS**

```
source venv/bin/activate
```

### Install Dependencies

```
pip install -r requirements.txt
```

---

## Running the Application

Start the development server:

```
python run.py
```

The API will be available at:

```
http://127.0.0.1:5000
```

---

## API Usage

### Convert Currency

```http
GET /convert
```

Example request:

```http
GET /convert?amount=100&from=USD&to=INR
```

### Example Response

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

## How It Works

1. The client sends a currency conversion request with the amount, source currency, and target currency.
2. The application fetches the latest exchange rate from the Frankfurter API.
3. The converted amount is calculated and returned in a structured JSON response.

---

## Error Handling

| Status Code | Description |
|-------------|-------------|
| 200 | Request completed successfully |
| 400 | Invalid amount or unsupported currency |
| 500 | Internal server error |

---

## Running Tests

```
python -m unittest discover tests
```

---

## API Reference

This project uses the **Frankfurter Exchange Rates API** to retrieve live currency exchange rates.

---

## Future Improvements

- Add an endpoint to list supported currencies
- Support batch currency conversion
- Add caching for frequently requested exchange rates
- Dockerize the application
- Deploy to a cloud platform
- Add request rate limiting

---

## Author

**Gopal Gupta**

GitHub: https://github.com/gopal092003

---

## License

This project is licensed under the MIT License.
