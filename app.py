
from flask import Flask, request, jsonify
import pandas as pd

app = Flask(__name__)

# Load CSV files
tax_rates_df = pd.read_csv("tax_jurisdiction_rates-2025Q3.csv")

# Load and combine both address range CSVs
part1 = pd.read_csv("TX-County-FIPS-453.csv")
part2 = pd.read_csv("TX-County-FIPS-491.csv")
county_fips_df = pd.concat([part1, part2], ignore_index=True)

# Clean column headers
tax_rates_df.columns = tax_rates_df.columns.str.strip()

# Suffix normalization dictionary
suffix_abbreviations = {
    "ALLEY": "Aly",
    "AVENUE": "Ave",
    "BOULEVARD": "Blvd",
    "CIRCLE": "Cir",
    "COURT": "Ct",
    "DRIVE": "Dr",
    "EXPRESSWAY": "Expy",
    "HIGHWAY": "Hwy",
    "LANE": "Ln",
    "PARKWAY": "Pkwy",
    "PLACE": "Pl",
    "ROAD": "Rd",
    "SQUARE": "Sq",
    "STREET": "St",
    "TERRACE": "Ter",
    "TRAIL": "Trl",
    "WAY": "Way",
    "LOOP": "Loop"
}

@app.route('/')
def home():
    return "Tax Lookup API is live. POST to /lookup"

@app.route('/test')
def test():
    return "This is the latest deployed code."

@app.route('/lookup', methods=['POST'])
def lookup_tax_rate():
    data = request.json

    building_number = int(data.get('building_number'))
    street = data.get('street', '').lower()
    suffix = data.get('suffix', '').lower()
    state = data.get('state', '').upper()
    zip_code = str(data.get('zip'))

    # Normalize suffix
    normalized_suffix = suffix_abbreviations.get(suffix.upper(), suffix)

    fips_filtered = county_fips_df[
        (county_fips_df['Street'].str.lower().str.contains(street, na=False)) &
        (county_fips_df['Suffix'].str.lower().str.contains(normalized_suffix.lower(), na=False)) &
        (county_fips_df['St'].str.upper() == state) &
        (county_fips_df['Zip'].astype(str) == zip_code)
    ]

    try:
        fips_filtered = fips_filtered[
            (fips_filtered['From'].astype(float) <= building_number) &
            (fips_filtered['To'].astype(float) >= building_number)
        ]
    except:
        return jsonify({"error": "Address number range mismatch or bad data in CSV"}), 400

    if fips_filtered.empty:
        return jsonify({"result": "No jurisdiction match found for this address."}), 404

    taid_columns = [
        'County TAID', 'City TAID', 'Transit Authority 1 TAID 1',
        'Transit Authority 2 TAID 2', 'Special Purpose District 1 TAID 1',
        'Special Purpose District 2 TAID 2', 'Special Purpose District 3 TAID 3',
        'Special Purpose District 4 TAID 4', 'Unique Authority TAID'
    ]

    taids = pd.unique(fips_filtered[taid_columns].values.ravel())
    taids = [int(taid) for taid in taids if pd.notnull(taid)]

    result_df = tax_rates_df[tax_rates_df['TAID'].isin(taids)][['Name', 'TAID', 'Tax Rate']]
    results = result_df.to_dict(orient='records')

    return jsonify({"jurisdictions": results})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
