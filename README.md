# Currency Converter API

A simple Flask-based Currency Converter API that uses the [Frankfurter API](https://www.frankfurter.app/) to fetch real-time exchange rates.

---

## Features
- Convert between any two supported currencies.
- Returns exchange rate and converted amount in JSON.
- Simple and lightweight, ideal for learning or small projects.

---

## Requirements
- Python 3.7+
- [Flask](https://palletsprojects.com/p/flask/)
- [Requests](https://docs.python-requests.org/)

Install dependencies:
```bash
pip install flask requests
```

---

## References
-[Frankfurter Exchange Rates API](https://frankfurter.dev/)

## Future
- Add `/currencies` endpoint to list supported currencies.
- Support batch conversion (one-to-many).
- Add caching for faster repeated requests.
- Dockerize the application for easy deployment.