# 📘 Currency Converter API – Detailed Documentation

This document provides **technical documentation** for developers using the Currency Converter API.

---

## 🔹 Base URL

```id="gk3m8r"
http://127.0.0.1:5000
```

---

## 🔹 Endpoint: `/convert`

Convert an amount from one currency to another using real-time exchange rates.

---

### 📌 Request

**Method:** `GET`
**Endpoint:**

```id="g0t9kb"
/convert
```

---

### 📌 Query Parameters

| Parameter | Type   | Required | Default | Description                     |
| --------- | ------ | -------- | ------- | ------------------------------- |
| `amount`  | float  | No       | `1`     | Amount to convert               |
| `from`    | string | No       | `USD`   | Source currency (ISO 4217 code) |
| `to`      | string | No       | `EUR`   | Target currency (ISO 4217 code) |

---

### 📌 Example Request

```http id="bq2w1n"
GET /convert?amount=100&from=USD&to=INR
```

---

### 📌 Example Response

```json id="j1cz1f"
{
  "from": "USD",
  "to": "INR",
  "amount": 100,
  "rate": 83.25,
  "converted": 8325.0
}
```

---

## 🔹 Response Fields

| Field       | Type   | Description           |
| ----------- | ------ | --------------------- |
| `from`      | string | Source currency       |
| `to`        | string | Target currency       |
| `amount`    | float  | Input amount          |
| `rate`      | float  | Exchange rate         |
| `converted` | float  | Final converted value |

---

## ⚠️ Error Handling

### 🔸 400 – Bad Request

Returned when:

* Invalid `amount` (non-numeric)
* Invalid currency code

**Example:**

```json id="b3p3rf"
{
  "error": "Invalid currency code"
}
```

---

### 🔸 500 – Internal Server Error

Returned when:

* External API fails
* Unexpected server issues occur

**Example:**

```json id="r9t2v8"
{
  "error": "Something went wrong"
}
```

---

## 🔄 Internal Workflow

```id="7yk8w9"
Client Request
     ↓
Flask Route (/convert)
     ↓
Service Layer (conversion logic)
     ↓
External API Call (Frankfurter)
     ↓
Response Returned (JSON)
```

---

## 🌐 External API Integration

This project uses the **Frankfurter API** to fetch exchange rates.

### Endpoint Used:

```id="a8n0zz"
https://api.frankfurter.app/latest
```

### Parameters:

* `base`: Source currency
* `symbols`: Target currency

---

## 🧪 Testing the API

You can test the API using:

### 🔹 Browser

```id="xxe8g0"
http://127.0.0.1:5000/convert?amount=100&from=USD&to=INR
```

### 🔹 Postman / Curl

```bash id="cg87i3"
curl "http://127.0.0.1:5000/convert?amount=100&from=USD&to=INR"
```

---

## 📌 Supported Currencies

All currencies supported by the Frankfurter API are valid.

Examples:

* USD (US Dollar)
* EUR (Euro)
* INR (Indian Rupee)
* GBP (British Pound)
* JPY (Japanese Yen)

---

## 🚧 Limitations

* No caching (every request hits external API)
* Single currency conversion per request
* Depends on third-party API availability

---

## 🔮 Future Enhancements

* `/currencies` endpoint to list supported currencies
* Batch conversion (multiple currencies at once)
* Caching layer (Redis / in-memory)
* Authentication & rate limiting
* Deployment (Docker / cloud hosting)

---

## 📎 Notes

* Currency codes must follow **ISO 4217 standard**
* Default conversion: `USD → EUR` with amount `1` if parameters are omitted

---
