# decider.py
# AI Decider: Wedding Venue Comparison
# Pairs with ACTIVITY_decider.md
# Tim Fraser

# Use a local Ollama model to extract structured data from
# unstructured venue descriptions, then recommend a shortlist
# based on a couple's priorities.

# 0. Setup #################################

## 0.1 Load Packages ############################

import requests
import json
import textwrap

## 0.2 Configuration ############################

PORT = 11434
OLLAMA_HOST = f"http://localhost:{PORT}"
CHAT_URL = f"{OLLAMA_HOST}/api/chat"
MODEL = "gemma3:latest"

# 1. Define Prompts #################################

SYSTEM_PROMPT = textwrap.dedent("""\
    You are a structured data extractor and decision analyst.
    Your job is to extract key attributes from unstructured venue descriptions,
    build a comparison table, and recommend the top 3 venues based on the client's priorities.

    Always return:
    1. A markdown table with columns: Venue, Capacity, Approx. Price/Night, Catering, Outdoor, Parking, Vibe (1 word)
    2. A ranked shortlist of top 3 venues with 1-sentence justification each
    3. One sentence noting any venues you had to exclude due to missing information

    Be concise. Do not invent data that is not in the descriptions.""")

VENUE_DATA = textwrap.dedent("""\
    --- VENUES ---

    Venue 1 — The Rosewood Estate
    A sprawling property in the Hudson Valley with manicured gardens and a restored barn.
    Capacity up to 175 guests. Rental fee is $17,500 Friday–Sunday. They have a preferred
    catering list with 4 approved vendors. Outdoor ceremony space available with a rain
    backup tent. Parking for ~80 cars on site.

    Venue 2 — The Grand Metropolitan Hotel
    Downtown ballroom, seats up to 300. In-house catering only. Pricing starts at $12,000
    for the ballroom rental, catering packages extra. Valet parking. No outdoor space.

    Venue 3 — Lakeview Pavilion
    Outdoor lakeside pavilion. No indoor backup. BYOB catering. Fits about 90 people
    comfortably, 110 at a squeeze. Very affordable — around $2,500 for a weekend.

    Venue 4 — Thornfield Manor
    Historic manor house, 8 acres. Exclusive use for the weekend. Price: $18,000.
    In-house catering team. Ceremony can be held on the grounds or in the chapel.
    Capacity 150. Featured in several bridal magazines.

    Venue 5 — The Foundry at Millworks
    Industrial-chic converted factory. Very trendy. Capacity 250. Bring your own vendors.
    Rental is $5,000. Rooftop available for cocktail hour. No on-site parking — street
    parking and nearby garage only.

    Venue 6 — Sunrise Farm & Vineyard
    Working vineyard with barn and outdoor ceremony terrace. Stunning views. Capacity 130.
    Weekend rental $9,800. Catering through their in-house team or 2 approved vendors.
    Ample parking. Very popular — books 18 months out.

    Venue 7 — The Atrium Club
    Corporate event space that does weddings on weekends. Very flexible on catering.
    Fits 300+. Located downtown. Pricing on request — sales team says "typically $9,000–$14,000
    depending on date." Not particularly romantic but very professional.

    Venue 8 — Cedar Hollow Retreat
    Rustic woodland lodge. Intimate and cozy. Max 60 guests. $3,200 for a Saturday.
    Outside catering allowed. No formal parking lot — guests park in a field.

    Venue 9 — The Belvedere
    Upscale rooftop venue with skyline views. Indoor/outdoor setup. Capacity 180.
    In-house catering required. Rental + minimum catering spend is $28,000.
    Very elegant. Valet only.

    Venue 10 — Harborside Event Center
    Waterfront venue, brand new. Capacity 220. Pricing TBD — still finalizing packages.
    Flexible on catering. Outdoor terrace available. Large parking lot.

    Venue 11 — The Ivy House
    Garden venue in a residential neighborhood. Permits outdoor ceremonies.
    Capacity 100. $4,500 rental. BYOB catering. Street parking only — coordinator
    recommends a shuttle from a nearby lot.

    Venue 12 — Maple Ridge Country Club
    Classic country club setting. Capacity 160. In-house catering only, known for
    being very good. Rental from $28,500. Golf course backdrop for photos.
    Ample parking. Private feel.

    Venue 13 — The Glasshouse Conservatory
    All-glass event space surrounded by botanical gardens. Very dramatic.
    Capacity 140. $18,000 rental, catering open. Outdoor garden available for ceremonies.
    Parking on site. Popular for spring weddings.

    Venue 14 — Millbrook Inn
    Country inn with event lawn. Venue rental $10,500. Capacity 120. Outside catering
    allowed. Some overnight rooms available for wedding party. Very charming.

    Venue 15 — The Warehouse District Loft
    Raw, urban space. Very minimal. No catering kitchen. Capacity 200.
    $8,800 rental. Not ideal for traditional weddings.

    Venue 16 — Cloverfield Farms
    Family-owned working farm. Barn + outdoor space. Capacity 135.
    $6,000 Friday–Sunday. Preferred caterer list (3 vendors).
    Casual, warm atmosphere. Lots of parking. Dogs welcome.""")

# Stage 1 priorities: romantic, budget-conscious, outdoor
PRIORITIES_1 = textwrap.dedent("""\
    Here are the couple's priorities:
    - Budget: under $8,000 for venue rental
    - Guest count: ~120 people
    - Vibe: romantic, not too corporate
    - Must have outdoor ceremony option
    - Catering must be in-house or on an approved vendor list

    Here are descriptions of 16 venues. Please analyze and recommend.

    """) + VENUE_DATA

# Stage 2 priorities: elegant, grand, high budget
PRIORITIES_2 = textwrap.dedent("""\
    Here are the couple's priorities:
    - Budget: flexible, up to $15,000
    - Guest count: ~200 people
    - Vibe: elegant, grand
    - Outdoor is a nice-to-have but not required
    - No catering constraint

    Here are descriptions of 16 venues. Please analyze and recommend.

    """) + VENUE_DATA

# 2. Helper Function #################################

def query_ollama(system_prompt, user_prompt, label="Query"):
    """Send a chat request to local Ollama and return the response text."""
    print(f"\n{'=' * 60}")
    print(f"☁️  Sending {label} to {MODEL}...")
    print(f"{'=' * 60}")

    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
    }

    response = requests.post(CHAT_URL, json=body, timeout=300)
    response.raise_for_status()
    data = response.json()
    content = data["message"]["content"]

    print(f"✅ Response received ({len(content)} chars)")
    return content

# 3. Stage 1: Base Prompt (Budget <$8k) ################

print("📋 ACTIVITY — AI Decider: Wedding Venue Comparison")
print("=" * 60)

stage1 = query_ollama(SYSTEM_PROMPT, PRIORITIES_1, label="Stage 1 (budget <$8k, romantic, outdoor)")
print(f"\n{'─' * 60}")
print("📊 STAGE 1 RESULTS — Budget <$8k, ~120 guests, romantic")
print(f"{'─' * 60}")
print(stage1)

# 4. Stage 2: Shifted Priorities ($15k) ################

stage2 = query_ollama(SYSTEM_PROMPT, PRIORITIES_2, label="Stage 2 (budget $15k, elegant, grand)")
print(f"\n{'─' * 60}")
print("📊 STAGE 2 RESULTS — Budget $15k, ~200 guests, elegant")
print(f"{'─' * 60}")
print(stage2)

# 5. Summary ###########################################

print(f"\n{'=' * 60}")
print("📊 Summary")
print(f"{'=' * 60}")
print(f"   ✅ Stage 1 complete — {len(stage1)} chars")
print(f"   ✅ Stage 2 complete — {len(stage2)} chars")
print(f"   ☁️  Model: {MODEL}")
print(f"   🔗 Endpoint: {CHAT_URL}")
print(f"{'=' * 60}")
