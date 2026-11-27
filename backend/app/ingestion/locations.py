"""Registry of Indian cities that LUVIA ingests live weather for.

Each entry ties together the identifiers that different sources use:

* latitude / longitude  - Open-Meteo grid lookup (approximate city centre)
* imd_district          - district name exactly as spelled in the IMD
                          district-warning feed (used to match official alerts)
* metar_icao            - nearest airport reporting METAR observations, or None.
                          Only codes confirmed to return data on aviationweather.gov
                          are listed; a city without one is covered by Open-Meteo only.
* imd_station_id        - IMD current-weather station ID (filled in once the IMD
                          API is whitelisted for this server; None for now)
"""

INDIAN_LOCATIONS = [
    # --- Metros -------------------------------------------------------------
    {"location_name": "New Delhi", "state": "Delhi", "latitude": 28.6139, "longitude": 77.2090, "imd_district": "NEW DELHI", "metar_icao": "VIDP"},
    {"location_name": "Mumbai", "state": "Maharashtra", "latitude": 19.0760, "longitude": 72.8777, "imd_district": "MUMBAI CITY", "metar_icao": "VABB"},
    {"location_name": "Kolkata", "state": "West Bengal", "latitude": 22.5726, "longitude": 88.3639, "imd_district": "KOLKATA", "metar_icao": "VECC"},
    {"location_name": "Chennai", "state": "Tamil Nadu", "latitude": 13.0827, "longitude": 80.2707, "imd_district": "CHENNAI", "metar_icao": "VOMM"},
    {"location_name": "Bengaluru", "state": "Karnataka", "latitude": 12.9716, "longitude": 77.5946, "imd_district": "BANGLORE URBAN", "metar_icao": "VOBL"},
    {"location_name": "Hyderabad", "state": "Telangana", "latitude": 17.3850, "longitude": 78.4867, "imd_district": "HYDERABAD", "metar_icao": "VOHS"},
    {"location_name": "Ahmedabad", "state": "Gujarat", "latitude": 23.0225, "longitude": 72.5714, "imd_district": "AHMADABAD", "metar_icao": "VAAH"},
    {"location_name": "Pune", "state": "Maharashtra", "latitude": 18.5204, "longitude": 73.8567, "imd_district": "PUNE", "metar_icao": None},
    {"location_name": "Gurugram", "state": "Haryana", "latitude": 28.4595, "longitude": 77.0266, "imd_district": "GURGAON", "metar_icao": None},
    {"location_name": "Thane", "state": "Maharashtra", "latitude": 19.2183, "longitude": 72.9781, "imd_district": "THANE", "metar_icao": None},

    # --- State and UT capitals ---------------------------------------------
    {"location_name": "Jaipur", "state": "Rajasthan", "latitude": 26.9124, "longitude": 75.7873, "imd_district": "JAIPUR", "metar_icao": "VIJP"},
    {"location_name": "Lucknow", "state": "Uttar Pradesh", "latitude": 26.8467, "longitude": 80.9462, "imd_district": "LUCKNOW", "metar_icao": "VILK"},
    {"location_name": "Bhopal", "state": "Madhya Pradesh", "latitude": 23.2599, "longitude": 77.4126, "imd_district": "BHOPAL", "metar_icao": "VABP"},
    {"location_name": "Guwahati", "state": "Assam", "latitude": 26.1445, "longitude": 91.7362, "imd_district": "KAMRUP", "metar_icao": "VEGT"},
    {"location_name": "Srinagar", "state": "Jammu and Kashmir", "latitude": 34.0837, "longitude": 74.7973, "imd_district": "SRINAGAR", "metar_icao": "VISR"},
    {"location_name": "Jammu", "state": "Jammu and Kashmir", "latitude": 32.7266, "longitude": 74.8570, "imd_district": "JAMMU", "metar_icao": "VIJU"},
    {"location_name": "Leh", "state": "Ladakh", "latitude": 34.1526, "longitude": 77.5771, "imd_district": "LEH", "metar_icao": "VILH"},
    {"location_name": "Bhubaneswar", "state": "Odisha", "latitude": 20.2961, "longitude": 85.8245, "imd_district": "KHORDHA", "metar_icao": "VEBS"},
    {"location_name": "Dehradun", "state": "Uttarakhand", "latitude": 30.3165, "longitude": 78.0322, "imd_district": "DEHRADUN", "metar_icao": None},
    {"location_name": "Patna", "state": "Bihar", "latitude": 25.5941, "longitude": 85.1376, "imd_district": "PATNA", "metar_icao": "VEPT"},
    {"location_name": "Thiruvananthapuram", "state": "Kerala", "latitude": 8.5241, "longitude": 76.9366, "imd_district": "THIRUVANANTHAPURAM", "metar_icao": "VOTV"},
    {"location_name": "Raipur", "state": "Chhattisgarh", "latitude": 21.2514, "longitude": 81.6296, "imd_district": "RAIPUR", "metar_icao": "VERP"},
    {"location_name": "Ranchi", "state": "Jharkhand", "latitude": 23.3441, "longitude": 85.3096, "imd_district": "RANCHI", "metar_icao": "VERC"},
    {"location_name": "Chandigarh", "state": "Chandigarh", "latitude": 30.7333, "longitude": 76.7794, "imd_district": "CHANDIGARH", "metar_icao": "VICG"},
    {"location_name": "Shimla", "state": "Himachal Pradesh", "latitude": 31.1048, "longitude": 77.1734, "imd_district": "SHIMLA", "metar_icao": None},
    {"location_name": "Panaji", "state": "Goa", "latitude": 15.4909, "longitude": 73.8278, "imd_district": "NORTH GOA", "metar_icao": "VOGO"},
    {"location_name": "Gandhinagar", "state": "Gujarat", "latitude": 23.2156, "longitude": 72.6369, "imd_district": "GANDHINAGAR", "metar_icao": None},
    {"location_name": "Amaravati", "state": "Andhra Pradesh", "latitude": 16.5131, "longitude": 80.5165, "imd_district": "GUNTUR", "metar_icao": None},
    {"location_name": "Imphal", "state": "Manipur", "latitude": 24.8170, "longitude": 93.9368, "imd_district": "IMPHAL WEST", "metar_icao": None},
    {"location_name": "Agartala", "state": "Tripura", "latitude": 23.8315, "longitude": 91.2868, "imd_district": "WEST TRIPURA", "metar_icao": None},
    {"location_name": "Shillong", "state": "Meghalaya", "latitude": 25.5788, "longitude": 91.8933, "imd_district": "EAST KHASI HILLS", "metar_icao": None},
    {"location_name": "Aizawl", "state": "Mizoram", "latitude": 23.7271, "longitude": 92.7176, "imd_district": "AIZAWL", "metar_icao": None},
    {"location_name": "Kohima", "state": "Nagaland", "latitude": 25.6751, "longitude": 94.1086, "imd_district": "KOHIMA", "metar_icao": None},
    {"location_name": "Itanagar", "state": "Arunachal Pradesh", "latitude": 27.0844, "longitude": 93.6053, "imd_district": "PAPUM PARE", "metar_icao": None},
    {"location_name": "Gangtok", "state": "Sikkim", "latitude": 27.3389, "longitude": 88.6065, "imd_district": "GANGTOK", "metar_icao": None},
    {"location_name": "Port Blair", "state": "Andaman and Nicobar Islands", "latitude": 11.6234, "longitude": 92.7265, "imd_district": "SOUTH ANDAMAN", "metar_icao": None},
    {"location_name": "Puducherry", "state": "Puducherry", "latitude": 11.9416, "longitude": 79.8083, "imd_district": "PUDUCHERRY", "metar_icao": None},

    # --- Other major cities -------------------------------------------------
    {"location_name": "Nagpur", "state": "Maharashtra", "latitude": 21.1458, "longitude": 79.0882, "imd_district": "NAGPUR", "metar_icao": "VANP"},
    {"location_name": "Indore", "state": "Madhya Pradesh", "latitude": 22.7196, "longitude": 75.8577, "imd_district": "INDORE", "metar_icao": "VAID"},
    {"location_name": "Kochi", "state": "Kerala", "latitude": 9.9312, "longitude": 76.2673, "imd_district": "ERNAKULAM", "metar_icao": "VOCI"},
    {"location_name": "Kozhikode", "state": "Kerala", "latitude": 11.2588, "longitude": 75.7804, "imd_district": "KOZHIKODE", "metar_icao": "VOCL"},
    {"location_name": "Coimbatore", "state": "Tamil Nadu", "latitude": 11.0168, "longitude": 76.9558, "imd_district": "COIMBATORE", "metar_icao": "VOCB"},
    {"location_name": "Madurai", "state": "Tamil Nadu", "latitude": 9.9252, "longitude": 78.1198, "imd_district": "MADURAI", "metar_icao": "VOMD"},
    {"location_name": "Tiruchirappalli", "state": "Tamil Nadu", "latitude": 10.7905, "longitude": 78.7047, "imd_district": "THIRUCHIRAPALLI", "metar_icao": "VOTR"},
    {"location_name": "Mangaluru", "state": "Karnataka", "latitude": 12.9141, "longitude": 74.8560, "imd_district": "DAKSHIN KANNADA", "metar_icao": "VOML"},
    {"location_name": "Visakhapatnam", "state": "Andhra Pradesh", "latitude": 17.6868, "longitude": 83.2185, "imd_district": "VISHAKHAPATNAM", "metar_icao": "VOVZ"},
    {"location_name": "Vijayawada", "state": "Andhra Pradesh", "latitude": 16.5062, "longitude": 80.6480, "imd_district": "NTR", "metar_icao": "VOBZ"},
    {"location_name": "Surat", "state": "Gujarat", "latitude": 21.1702, "longitude": 72.8311, "imd_district": "SURAT", "metar_icao": "VASU"},
    {"location_name": "Vadodara", "state": "Gujarat", "latitude": 22.3072, "longitude": 73.1812, "imd_district": "VADODARA", "metar_icao": "VABO"},
    {"location_name": "Varanasi", "state": "Uttar Pradesh", "latitude": 25.3176, "longitude": 82.9739, "imd_district": "VARANASI", "metar_icao": "VEBN"},
    {"location_name": "Agra", "state": "Uttar Pradesh", "latitude": 27.1767, "longitude": 78.0081, "imd_district": "AGRA", "metar_icao": "VIAG"},
    {"location_name": "Kanpur", "state": "Uttar Pradesh", "latitude": 26.4499, "longitude": 80.3319, "imd_district": "KANPUR", "metar_icao": None},
    {"location_name": "Prayagraj", "state": "Uttar Pradesh", "latitude": 25.4358, "longitude": 81.8463, "imd_district": "PRAYAGRAJ", "metar_icao": None},
    {"location_name": "Amritsar", "state": "Punjab", "latitude": 31.6340, "longitude": 74.8723, "imd_district": "AMRITSAR", "metar_icao": "VIAR"},
    {"location_name": "Jodhpur", "state": "Rajasthan", "latitude": 26.2389, "longitude": 73.0243, "imd_district": "JODHPUR", "metar_icao": None},
    {"location_name": "Udaipur", "state": "Rajasthan", "latitude": 24.5854, "longitude": 73.7125, "imd_district": "UDAIPUR", "metar_icao": None},
    {"location_name": "Siliguri", "state": "West Bengal", "latitude": 26.7271, "longitude": 88.3953, "imd_district": "DARJEELING", "metar_icao": "VEBD"},
    {"location_name": "Gaya", "state": "Bihar", "latitude": 24.7914, "longitude": 85.0002, "imd_district": "GAYA", "metar_icao": "VEGY"},
]

for _location in INDIAN_LOCATIONS:
    _location.setdefault("imd_station_id", None)


def find_location(name: str) -> dict | None:
    """Return the registry entry for a city name (case-insensitive)."""
    key = (name or "").strip().casefold()
    return next(
        (loc for loc in INDIAN_LOCATIONS if loc["location_name"].casefold() == key),
        None,
    )
