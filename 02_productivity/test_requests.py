# test_requests.py
# POST request with JSON using the requests library
# Tim Fraser

# Sends a POST request to httpbin.org with JSON body.
# Uses the json= parameter so requests encodes the body and sets Content-Type.

# 0. Setup #################################

import requests

# 1. POST with JSON #################################

url = "https://httpbin.org/post"
payload = {"name": "test"}

# json= encodes the dict as JSON and sets Content-Type: application/json
r = requests.post(url, json=payload)

# Optional: check status and print response
r.raise_for_status()
print(r.json())
