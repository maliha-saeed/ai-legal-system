"""
Synthetic Data Seeder
─────────────────────
Populates the database with 30 realistic synthetic cases for testing.
Run: python seed_data.py

All data is completely fictional and for academic/testing purposes only.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, create_case
from ai.logic import classify_claim, screen_viability
from sklearn.metrics import classification_report, confusion_matrix

SYNTHETIC_CASES = [
    # ── Personal Injury ──
    {
        "client_name": "James Thornton",
        "client_email": "j.thornton@example.com",
        "client_phone": "07712 345678",
        "client_dob": "1985-06-14",
        "incident_date": "2023-08-15",
        "incident_type": "Personal Injury",
        "incident_description": "I was involved in a road traffic accident on the A40 near Shepherd's Bush. A lorry ran a red light and collided with the driver's side of my vehicle. I suffered a whiplash injury and fractured wrist. I was taken to St. Mary's Hospital by ambulance. I had three months off work.",
        "incident_location": "A40, Shepherd's Bush, London"
    },
    {
        "client_name": "Priya Sharma",
        "client_email": "priya.sharma@example.com",
        "client_phone": "07845 112233",
        "client_dob": "1991-03-22",
        "incident_date": "2024-01-10",
        "incident_type": "Personal Injury",
        "incident_description": "I slipped on a wet floor in Tesco supermarket in Manchester. There were no warning signs. I fell and sustained a serious ankle sprain and bruising to my hip. A member of staff assisted me. The floor had been mopped but no wet floor sign was placed.",
        "incident_location": "Tesco, Piccadilly, Manchester"
    },
    {
        "client_name": "Robert Fielding",
        "client_email": "r.fielding@example.com",
        "client_phone": "07933 667788",
        "client_dob": "1978-11-30",
        "incident_date": "2022-03-01",
        "incident_type": "Personal Injury",
        "incident_description": "I fell from scaffolding on a construction site in Birmingham due to faulty equipment. My employer had not carried out adequate safety checks. I suffered a broken collarbone and back injury. I was hospitalised for two weeks.",
        "incident_location": "Construction site, Broad Street, Birmingham"
    },
    {
        "client_name": "Sophie Chen",
        "client_email": "s.chen@example.com",
        "client_phone": "07600 223344",
        "client_dob": "1999-09-05",
        "incident_date": "2021-04-10",
        "incident_type": "Personal Injury",
        "incident_description": "Cycling accident on road",
        "incident_location": "Bristol"
    },
    {
        "client_name": "Michael O'Brien",
        "client_email": "m.obrien@example.com",
        "client_phone": "07800 556677",
        "client_dob": "1965-02-28",
        "incident_date": "2024-05-20",
        "incident_type": "Personal Injury",
        "incident_description": "I tripped on a cracked pavement outside the local council offices in Leeds. The crack had been reported multiple times to the council by residents. I fell forwards and suffered a laceration to my forehead requiring stitches, and a sprained wrist. A witness helped me.",
        "incident_location": "Council offices, Park Row, Leeds"
    },
    {
        "client_name": "Emma Whitfield",
        "client_email": "e.whitfield@example.com",
        "client_phone": "07711 889900",
        "client_dob": "1993-07-19",
        "incident_date": "2024-08-03",
        "incident_type": "Personal Injury",
        "incident_description": "I was assaulted outside a nightclub in Liverpool by an unknown individual. I suffered bruising to my face and a broken nose. Police were called. I attended the Royal Liverpool Hospital.",
        "incident_location": "Concert Square, Liverpool"
    },
    {
        "client_name": "David Okafor",
        "client_email": "d.okafor@example.com",
        "client_phone": "07922 334455",
        "client_dob": "1988-12-11",
        "incident_date": "2023-11-14",
        "incident_type": "Personal Injury",
        "incident_description": "I was injured while operating machinery at my workplace. The guard on the machine had not been properly maintained. I sustained a deep cut and nerve damage to my left hand. I have been unable to work for six months.",
        "incident_location": "Factory, Industrial Estate, Sheffield"
    },

    # ── Clinical Negligence ──
    {
        "client_name": "Margaret Lawson",
        "client_email": "m.lawson@example.com",
        "client_phone": "07888 123456",
        "client_dob": "1955-08-04",
        "incident_date": "2022-06-15",
        "incident_type": "Clinical Negligence",
        "incident_description": "My GP failed to diagnose breast cancer for over eighteen months despite repeated visits complaining of a lump. By the time I was referred to the Royal Free Hospital and received a diagnosis, the cancer had spread to stage three. An earlier referral would have changed my prognosis significantly.",
        "incident_location": "GP Surgery, Camden, London"
    },
    {
        "client_name": "Alan Patel",
        "client_email": "a.patel@example.com",
        "client_phone": "07766 998877",
        "client_dob": "1970-04-16",
        "incident_date": "2023-03-22",
        "incident_type": "Clinical Negligence",
        "incident_description": "I underwent knee surgery at Manchester Royal Infirmary. The surgeon operated on the wrong knee initially before correcting the error. I experienced significant additional pain, extended recovery time, and psychological distress as a result of this wrong site surgery.",
        "incident_location": "Manchester Royal Infirmary"
    },
    {
        "client_name": "Catherine Brown",
        "client_email": "c.brown@example.com",
        "client_phone": "07500 112244",
        "client_dob": "1982-01-07",
        "incident_date": "2024-02-14",
        "incident_type": "Clinical Negligence",
        "incident_description": "My dentist at the NHS clinic extracted the wrong tooth during a routine procedure. The tooth that required extraction was clearly documented in my notes. I now require a dental implant and have suffered significant distress.",
        "incident_location": "NHS Dental Clinic, Nottingham"
    },
    {
        "client_name": "Thomas Griffiths",
        "client_email": "t.griffiths@example.com",
        "client_phone": "07812 667799",
        "client_dob": "1949-05-25",
        "incident_date": "2019-09-10",
        "incident_type": "Clinical Negligence",
        "incident_description": "Wrong medication prescribed by doctor at hospital",
        "incident_location": "Cardiff"
    },
    {
        "client_name": "Aisha Mohammed",
        "client_email": "a.mohammed@example.com",
        "client_phone": "07633 445566",
        "client_dob": "1990-10-29",
        "incident_date": "2023-12-01",
        "incident_type": "Clinical Negligence",
        "incident_description": "During childbirth at Northwick Park Hospital, the midwifery team failed to act on clear signs of foetal distress for over two hours. My son suffered a birth injury as a result and has been diagnosed with hypoxic-ischaemic encephalopathy. An emergency caesarean should have been performed earlier.",
        "incident_location": "Northwick Park Hospital, Harrow"
    },
    {
        "client_name": "Graham Peters",
        "client_email": "g.peters@example.com",
        "client_phone": "07744 889922",
        "client_dob": "1958-03-16",
        "incident_date": "2024-04-09",
        "incident_type": "Clinical Negligence",
        "incident_description": "I developed a post-operative infection following hip replacement surgery at St. James's University Hospital. Despite reporting symptoms of infection during follow-up appointments, the consultant dismissed my concerns. The infection spread and required two further surgical interventions.",
        "incident_location": "St. James's University Hospital, Leeds"
    },

    # ── Housing Disrepair ──
    {
        "client_name": "Fatima Hassan",
        "client_email": "f.hassan@example.com",
        "client_phone": "07855 223366",
        "client_dob": "1984-09-12",
        "incident_date": "2023-06-01",
        "incident_type": "Housing Disrepair",
        "incident_description": "My flat in Tower Hamlets has severe damp and mould throughout the bedroom and living room. I have reported this to the council landlord on five separate occasions since June 2023. No repairs have been carried out. My children have suffered respiratory problems as a result. I have photographs and written complaints.",
        "incident_location": "Flat 12, Bow Road, Tower Hamlets, London"
    },
    {
        "client_name": "Darren Wright",
        "client_email": "d.wright@example.com",
        "client_phone": "07900 112345",
        "client_dob": "1972-11-03",
        "incident_date": "2024-01-15",
        "incident_type": "Housing Disrepair",
        "incident_description": "The boiler in my council house stopped working in January during winter. I notified the housing association in writing on three occasions. I was left without heating or hot water for seven weeks. I have a young child and an elderly parent living in the property.",
        "incident_location": "15 Oak Street, Salford"
    },
    {
        "client_name": "Lisa Nguyen",
        "client_email": "l.nguyen@example.com",
        "client_phone": "07622 334477",
        "client_dob": "1996-06-24",
        "incident_date": "2024-03-10",
        "incident_type": "Housing Disrepair",
        "incident_description": "There is a persistent roof leak above the main bedroom in my rented flat. The ceiling has collapsed partially. I reported this to my private landlord immediately and followed up in writing. He has failed to carry out any repairs after three months. The structural damage is worsening.",
        "incident_location": "Flat 3B, Granville Street, Birmingham"
    },
    {
        "client_name": "Kevin McAllister",
        "client_email": "k.mcallister@example.com",
        "client_phone": "07733 556688",
        "client_dob": "1968-08-17",
        "incident_date": "2022-11-20",
        "incident_type": "Housing Disrepair",
        "incident_description": "Broken windows and pest infestation in council property",
        "incident_location": "Glasgow"
    },
    {
        "client_name": "Nadia Kowalski",
        "client_email": "n.kowalski@example.com",
        "client_phone": "07811 778899",
        "client_dob": "1987-01-31",
        "incident_date": "2023-09-05",
        "incident_type": "Housing Disrepair",
        "incident_description": "Electrical faults throughout my rented house have been reported to the housing association for over a year. Lights flicker, sockets are unsafe, and a circuit breaker trips regularly. An electrician confirmed the wiring is dangerous. The landlord has not responded to my formal complaints. I am concerned about fire risk.",
        "incident_location": "22 Victoria Road, Bristol"
    },
    {
        "client_name": "Oluwaseun Adeyemi",
        "client_email": "o.adeyemi@example.com",
        "client_phone": "07944 667711",
        "client_dob": "1993-05-08",
        "incident_date": "2024-02-01",
        "incident_type": "Housing Disrepair",
        "incident_description": "I have a severe rodent infestation in my council flat in Hackney. I notified the council housing team in February 2024 with photographs of droppings and damage. The council pest control came once but the infestation returned. My kitchen units have been gnawed and I cannot store food safely. Three further written complaints have been ignored.",
        "incident_location": "Flat 7, Pembury Estate, Hackney, London"
    },
]


def seed():
    init_db()  # Create tables if they don't exist yet
    print(f"Seeding {len(SYNTHETIC_CASES)} synthetic cases...")

    # enumerate(..., 1) gives a counter starting at 1 for the progress print
    for i, case_data in enumerate(SYNTHETIC_CASES, 1):

        # Classify the claim type (PI / CN / HD) from the incident text
        classification = classify_claim(
            case_data['incident_type'],
            case_data['incident_description']
        )

        # Check viability — limitation period, required fields, description detail
        viability = screen_viability(case_data, classification['claim_type'])

        # Attach AI results to the case dict so they're saved alongside client data
        case_data.update({
            'claim_type': classification['claim_type'],
            'claim_confidence': classification['claim_confidence'],
            'claim_keywords': classification['claim_keywords'],
            'viability_status': viability['viability_status'],
            'viability_explanation': viability['viability_explanation'],
            'limitation_ok': viability['limitation_ok'],
        })

        case_id = create_case(case_data)  # Insert into database, get assigned ID

        # Print a formatted progress line, e.g:
        # [01] CASE-0001 · James Thornton          → Personal Injury       | Potentially Viable
        # :02d = zero-pad counter to 2 digits, :04d = zero-pad ID to 4, :<25 = left-align name
        print(f"  [{i:02d}] CASE-{case_id:04d} · {case_data['client_name']:<25} "
              f"→ {classification['claim_type']:<22} | {viability['viability_status']}")

    print(f"\nDone. {len(SYNTHETIC_CASES)} cases inserted.")
    print("Run `python app.py` to start the application.")


# Only runs when this file is executed directly (python seed_data.py)
# Importing this file from another module will NOT trigger seeding
if __name__ == '__main__':
    seed()