"""Build the public demo dataset: fictional sellers in the real CSV format, no customer data.

    python -m vani.tools.make_demo_data

Writes demo/raw/*.csv (8 made-up sellers, their made-up VANI calls and turns),
demo/warehouse.duckdb, and copies only AGGREGATES from the real data:
demo/evidence.json (140 findings: rates and counts, no rows) and
demo/demand.json (top-10% enquiries per category group). Safe to commit and deploy.
"""
import csv
import json
import shutil
from pathlib import Path

from vani.config import REPO_ROOT, get_settings
from vani.data.warehouse import build

OUT = REPO_ROOT / "demo"

PROFILE_COLS = (
    "fk_glusr_usr_id,seller_city,seller_district,seller_state,seller_pincode,seller_locality,business_type,annual_turnover,"
    "nature_of_business,nature_of_business_secondary,gst_registration_year,top_category_1,top_category_2,top_category_3,"
    "top_parent_category,top_category_group,num_categories,eng_activity_30d,eng_answered_calls_90d,eng_call_attempts_90d,"
    "eng_call_attempts_1yr,eng_pickup_ratio_90d,eng_pickup_ratio_1yr,eng_long_calls_90d,eng_short_calls_90d,eng_callback_90d,"
    "eng_callback_1yr,eng_meetings_1yr,eng_hot_meetings_1yr,eng_enq_received_90d,eng_enq_received_1yr,eng_enq_replies_90d,"
    "eng_enq_replies_1yr,eng_pns_received_90d,eng_pns_received_1yr,eng_pns_answered_90d,eng_pns_answered_1yr,eng_ni_count_1yr,"
    "eng_np_count_1yr,eng_product_count,eng_products_modified_90d,eng_products_modified_1yr,eng_cqs,bot_attempts,bot_answered,"
    "calls_meeting_fixed,calls_not_interested,calls_general,calls_call_later,bot_answer_rate,avg_answered_call_sec,"
    "past_objections,past_questions_asked,asked_if_talking_to_bot,showed_frustration,past_dispositions_detailed,"
    "already_in_touch_with_executive,do_not_call_requested,company_name,customer_type,is_paid,listing_status,"
    "mobile_verified_flag,email_verified_flag,gst_verified_flag,gst_flag,is_pan_number_available,business_type_flag,"
    "visiting_card_flag").split(",")
CALL_COLS = ("attempt_id,fk_glusr_usr_id,redis_bucket,lead_bot_version,call_attempt_count,call_start_time,lead_call_duration,"
             "lead_call_summary,call_recording_url,disposition_label,meeting_fixed,has_turn_transcript,has_evaluator_output").split(",")
TURN_COLS = "attempt_id,fk_glusr_usr_id,turn_no,speaker,start_sec,end_sec,text".split(",")
EXEC_COLS = ("click_to_call_id,fk_glusr_usr_id,fk_employeeid,module,status,call_start_time,call_duration,"
             "call_duration_customer,ring_duration").split(",")

# Fictional sellers. Names, places and numbers are invented to show contrasting personas.
SELLERS = [
    dict(fk_glusr_usr_id=90000001, company_name="Sharma Embroidery Works (demo)", seller_city="Lucknow",
         seller_state="Uttar Pradesh", business_type="Proprietorship", annual_turnover="0 - 40 L",
         nature_of_business="Trader - Retailer", gst_registration_year=2021, top_category_1="Embroidered Patches",
         top_category_group="Fashion & Garment Accessories for Men, Women & Kids", eng_enq_received_90d=1,
         eng_pns_received_90d=1, bot_attempts=4, bot_answered=3, calls_call_later=2, calls_not_interested=1,
         avg_answered_call_sec=12, past_dispositions_detailed="callback_requested (2); call_dropped (1)",
         past_objections="Seller Unavailability & Scheduling Constraints (2)"),
    dict(fk_glusr_usr_id=90000002, company_name="Coastal Plywood Traders (demo)", seller_city="Chennai",
         seller_state="Tamil Nadu", business_type="Partnership", annual_turnover="1.5 - 5 Cr",
         nature_of_business="Manufacturer", gst_registration_year=2009, top_category_1="Hardwood Plywood",
         top_category_group="Building Construction Material, Equipment, Civil Engineering and Real Estate",
         eng_enq_received_90d=2, eng_pns_received_90d=1, bot_attempts=2, bot_answered=1, calls_general=1,
         avg_answered_call_sec=45, past_dispositions_detailed="callback_requested (0)"),
    dict(fk_glusr_usr_id=90000003, company_name="Navrang Textiles (demo)", seller_city="Vadodara",
         seller_state="Gujarat", business_type="Proprietorship", annual_turnover="40 L - 1.5 Cr",
         nature_of_business="Trader - Wholesaler/Distributor", gst_registration_year=2016, top_category_1="Cotton Sarees",
         top_category_group="Apparel, Clothing & Garments", eng_enq_received_90d=2, eng_pns_received_90d=3,
         bot_attempts=1, bot_answered=0),
    dict(fk_glusr_usr_id=90000004, company_name="Om Sai Packaging (demo)", seller_city="Pune",
         seller_state="Maharashtra", business_type="Proprietorship", annual_turnover="40 L - 1.5 Cr",
         nature_of_business="Manufacturer", gst_registration_year=2018, top_category_1="Corrugated Boxes",
         top_category_group="Packaging Material, Supplies & Machines", eng_enq_received_90d=4, eng_pns_received_90d=2,
         bot_attempts=2, bot_answered=1, calls_call_later=1, avg_answered_call_sec=38),
    dict(fk_glusr_usr_id=90000005, company_name="Shree Balaji Agro (demo)", seller_city="Jaipur",
         seller_state="Rajasthan", business_type="Proprietorship", annual_turnover="0 - 40 L",
         nature_of_business="Trader - Wholesaler/Distributor", gst_registration_year=2020, top_category_1="Makhana",
         top_category_group="Vegetables, Fruits, Grains, Dairy Products & Other FMCG and Grocery Items",
         eng_enq_received_90d=3, bot_attempts=2, bot_answered=1, calls_not_interested=1, avg_answered_call_sec=30,
         past_dispositions_detailed="not_interested (1)", past_objections="Explicit Disinterest / Refusal (1)"),
    dict(fk_glusr_usr_id=90000006, company_name="Bharat Steel Fabricators Ltd (demo)", seller_city="Ludhiana",
         seller_state="Punjab", business_type="Limited Company", annual_turnover="25 - 100 Cr",
         nature_of_business="Manufacturer", gst_registration_year=2001, top_category_1="Steel Racks",
         top_category_group="Industrial Plants, Machinery & Equipment", eng_enq_received_90d=6, eng_pns_received_90d=5,
         bot_attempts=2, bot_answered=1, calls_meeting_fixed=1, avg_answered_call_sec=70),
    dict(fk_glusr_usr_id=90000007, company_name="Green Leaf Spices (demo)", seller_city="Kochi",
         seller_state="Kerala", business_type="Proprietorship", annual_turnover="0 - 40 L",
         nature_of_business="Manufacturer", gst_registration_year=2022, top_category_1="Black Pepper",
         top_category_group="Vegetables, Fruits, Grains, Dairy Products & Other FMCG and Grocery Items",
         eng_enq_received_90d=0, bot_attempts=0, bot_answered=0),
    dict(fk_glusr_usr_id=90000008, company_name="Kolkata Jute Bags (demo)", seller_city="Kolkata",
         seller_state="West Bengal", business_type="Partnership", annual_turnover="40 L - 1.5 Cr",
         nature_of_business="Manufacturer", gst_registration_year=2012, top_category_1="Jute Shopping Bags",
         top_category_group="Packaging Material, Supplies & Machines", eng_enq_received_90d=1, bot_attempts=1,
         bot_answered=1, calls_general=1, avg_answered_call_sec=25),
]

# (glid, attempt, start, seconds, disposition, meeting, summary, turns[(speaker, start, end, text)])
CALLS = [
    (90000001, 1, "2026-08-04 11:20:00", 11, "Call Later / Busy", 0,
     "The seller said he was busy at the shop and asked to be called later.",
     [("bot", 0, 4, "Namaste ji, main IndiaMART se Payal bol rahi hoon."), ("seller", 4.5, 6.5, "Haan bolo jaldi"),
      ("bot", 7, 9, "Aapke business ke liye ek free meeting..."), ("seller", 9.2, 11, "Abhi busy hoon baad mein karna")]),
    (90000001, 2, "2026-09-02 12:05:00", 9, "Call Later / Busy", 0,
     "The seller cut the call short, saying he would talk later.",
     [("bot", 0, 4, "Namaste ji, IndiaMART se Payal."), ("seller", 4.2, 6.2, "Haan ji baad mein baat karte hain")]),
    (90000002, 1, "2026-08-20 15:10:00", 45, "General (talked)", 0,
     "The seller spoke in English, asked what the meeting is about, and said he would think about it.",
     [("bot", 0, 5, "Namaste ji, main IndiaMART se Payal bol rahi hoon."), ("seller", 5.5, 9, "Sorry, I don't understand Hindi, please speak in English"),
      ("bot", 9.5, 15, "Sure. Our executive can help improve your listing."), ("seller", 15.5, 22, "Okay, what exactly will the executive do for my plywood business"),
      ("bot", 22.5, 30, "They fix your catalogue so the right buyers find you."), ("seller", 30.5, 36, "Alright, let me think about it and get back to you")]),
    (90000004, 1, "2026-09-10 16:40:00", 38, "Call Later / Busy", 0,
     "The seller was interested but asked to be called back next week.",
     [("bot", 0, 5, "Namaste ji, IndiaMART se Payal bol rahi hoon."), ("seller", 5.5, 8, "Haan ji boliye kya baat hai"),
      ("bot", 8.5, 15, "Aapki listing ke liye ek free meeting..."), ("seller", 15.5, 21, "Achha theek hai lekin agle hafte call kijiye abhi time nahi hai")]),
    (90000005, 1, "2026-08-28 17:15:00", 30, "Not Interested", 0,
     "The seller said he did not need IndiaMART services right now.",
     [("bot", 0, 5, "Namaste ji, IndiaMART se Payal bol rahi hoon."), ("seller", 5.5, 9, "Haan ji kya hai"),
      ("bot", 9.5, 15, "Free meeting ke baare mein..."), ("seller", 15.5, 19, "Nahi ji abhi zaroorat nahi hai")]),
    (90000006, 1, "2026-08-12 15:30:00", 70, "Meeting Fixed", 1,
     "The seller agreed to a meeting with the executive at his factory.",
     [("bot", 0, 5, "Namaskar ji, main IndiaMART se Payal bol rahi hoon."), ("seller", 5.5, 9, "Haan ji boliye, main sun raha hoon"),
      ("bot", 9.5, 16, "Hamare executive aapki listing ke liye..."), ("seller", 16.5, 22, "Theek hai, kal shaam paanch baje factory aa jaiye")]),
    (90000008, 1, "2026-09-15 14:20:00", 25, "General (talked)", 0,
     "The seller listened and asked for details on WhatsApp.",
     [("bot", 0, 5, "Namaste ji, IndiaMART se Payal bol rahi hoon."), ("seller", 5.5, 8.5, "Haan bolo"),
      ("bot", 9, 15, "Free meeting..."), ("seller", 15.5, 20, "Details WhatsApp par bhej dijiye")]),
]


def _write(path: Path, cols: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def main() -> None:
    raw = OUT / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    sellers = []
    for s in SELLERS:
        a = s.get("bot_attempts", 0)
        sellers.append({**s, "seller_district": s["seller_city"], "num_categories": 1,
                        "bot_answer_rate": round(100 * s.get("bot_answered", 0) / a, 1) if a else "",
                        "customer_type": "Demo seller", "listing_status": "LST"})
    calls, turns = [], []
    for glid, att, start, secs, disp, met, summary, tt in CALLS:
        aid = f"{glid}{att:02d}"
        calls.append(dict(attempt_id=aid, fk_glusr_usr_id=glid, redis_bucket="DEMO", lead_bot_version="main_vani",
                          call_attempt_count=att, call_start_time=start, lead_call_duration=secs, lead_call_summary=summary,
                          disposition_label=disp, meeting_fixed=met, has_turn_transcript=1, has_evaluator_output=0))
        for i, (spk, a0, a1, text) in enumerate(tt, 1):
            turns.append(dict(attempt_id=aid, fk_glusr_usr_id=glid, turn_no=i, speaker=spk, start_sec=a0, end_sec=a1, text=text))
    _write(raw / "gc_seller_profile.csv", PROFILE_COLS, sellers)
    _write(raw / "gc_bot_calls.csv", CALL_COLS, calls)
    _write(raw / "gc_bot_call_turns.csv", TURN_COLS, turns)
    _write(raw / "gc_executive_calls.csv", EXEC_COLS, [])
    print(build(raw, OUT / "warehouse.duckdb"))

    # Aggregates only from the real data (no rows): the evidence book and the category benchmarks.
    s = get_settings()
    ev = s.resolve(s.evidence_path)
    if ev.exists():
        shutil.copy(ev, OUT / "evidence.json")
    wh = s.resolve(s.warehouse_path)
    if wh.exists():
        from vani.data.repository import DuckDBSellerRepository
        from vani.evidence.demand import CategoryDemand
        demand = CategoryDemand.build(DuckDBSellerRepository(wh, s.reference_year).iter_profiles())
        (OUT / "demand.json").write_text(json.dumps(demand.groups, indent=1))
    print("demo data ->", OUT)


if __name__ == "__main__":
    main()
