import googlemaps
import math
import pandas as pd
import requests

df = pd.read_csv("zillow_housing_data.csv")
API_KEY = "AIzaSyCPP2s2UW6u5A3W8wsu_3qRFnYTf6m-t-A"
gmaps = googlemaps.Client(key=API_KEY)
UCSD = "9450 Gilman Drive, La Jolla, CA 92093"

SD_BEACHES = [(32.7495, -117.2553), # Ocean Beach
(32.7686, -117.2514), # Mission Beach
(32.7936, -117.2547), # Pacific Beach
(32.8300, -117.2800), # Windansea Beach
(32.8503, -117.2725), # La Jolla Cove
(32.8590, -117.2568), # La Jolla Shores
(32.8885, -117.2528), # Black's Beach
(32.9218, -117.2618), # Torrey Pines State Beach
(32.9550, -117.2650), # Del Mar City Beach
(32.9911, -117.2736), # Fletcher Cove
(33.0180, -117.2810), # Cardiff State Beach
(33.0350, -117.2917) # Swami's Beach
]

def haversine_km(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def coast_dist_km(lat, lng):
    return min(haversine_km(lat, lng, blat, blng) for blat, blng in SD_BEACHES)

def nearest_place_new(lat, lng, keyword, radius=5000):
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.location"
    }
    body = {
        "includedTypes": [keyword],
        "maxResultCount": 1,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": float(radius)
            }
        }
    }
    response = requests.post(url, headers=headers, json=body)
    data = response.json()
    places = data.get("places", [])
    if not places:
        return None, None
    place = places[0]
    loc = place["location"]
    name = place["displayName"]["text"]
    return (loc["latitude"], loc["longitude"]), name

def distance_matrix(origin, destination, mode):
    result = gmaps.distance_matrix(origin, destination, mode=mode)
    element = result["rows"][0]["elements"][0]
    if element["status"] != "OK":
        return None, None
    return element["distance"]["text"], element["duration"]["text"]

def geocode_address(address):
    result = gmaps.geocode(address)
    if not result:
        return None, None
    loc = result[0]["geometry"]["location"]
    return float(loc["lat"]), float(loc["lng"])

rows = []
for _, row in df.iterrows():
    lat, lng = row["latitude"], row["longitude"]

    if pd.isna(lat) or pd.isna(lng):
        lat, lng = geocode_address(row["address"])
        if lat is None:
            print(f"Skipping row — could not geocode: {row['address']}")
            continue

    lat, lng = float(lat), float(lng)
    origin = (lat, lng)


    transit_loc, transit_name = nearest_place_new(lat, lng, "transit_station")
    transit_dist, transit_walk_time = distance_matrix(origin, transit_loc, "walking") if transit_loc else (None, None)

    ucsd_car_dist, ucsd_car_time = distance_matrix(origin, UCSD, "driving")

    ucsd_transit_dist, ucsd_transit_time = distance_matrix(origin, UCSD, "transit")

    grocery_loc, grocery_name = nearest_place_new(lat, lng, "supermarket")
    grocery_dist, grocery_time = distance_matrix(origin, grocery_loc, "driving") if grocery_loc else (None, None)

    rows.append({
        "latitude": lat, "longitude": lng,
        "nearest_transit": transit_name,
        "transit_walk_dist": transit_dist,
        "transit_walk_time": transit_walk_time,
        "ucsd_car_dist": ucsd_car_dist,
        "ucsd_car_time": ucsd_car_time,
        "ucsd_transit_dist": ucsd_transit_dist,
        "ucsd_transit_time": ucsd_transit_time,
        "nearest_grocery": grocery_name,
        "grocery_car_dist": grocery_dist,
        "grocery_car_time": grocery_time,
        "coast_dist_km": coast_dist_km(lat, lng)
    })

gmaps_df = pd.DataFrame(rows)
zillow_gmaps_df = pd.merge(df, gmaps_df, on=["latitude", "longitude"])
zillow_gmaps_df.to_csv("zillow_gmaps_features.csv", index=False)
print(zillow_gmaps_df)