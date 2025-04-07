# System Harmonogramów Wywozu Śmieci / Waste Collection Schedule System

## Polski

### Opis

Zestaw skryptów do pobierania i przetwarzania danych harmonogramów wywozu śmieci z serwisu https://kiedysmieci.info/

Zestaw składa się z trzech skryptów:

1. `municipalities.py` - pobiera listę gmin dostępnych w systemie
2. `streets.py` - pobiera listę ulic dla wybranej gminy
3. `schedule.py` - pobiera harmonogram wywozu śmieci dla wybranej gminy i ulicy

### Wymagania

Skrypty wymagają Pythona 3.6+ oraz następujących bibliotek:

- requests
- beautifulsoup4

Możesz zainstalować wymagane biblioteki komendą:

```bash
pip install requests beautifulsoup4
```

### Sposób użycia

#### 1. Pobieranie listy gmin

```bash
python municipalities.py
```

Skrypt pobierze listę wszystkich dostępnych gmin i zapisze ją do pliku `municipalities.json`.

#### 2. Pobieranie listy ulic dla wybranej gminy

```bash
# Sposób 1: Skrypt zapyta o ID gminy
python streets.py

# Sposób 2: Podaj ID gminy jako argument
python streets.py 309474

# Sposób 3: Podaj ID gminy i nazwę pliku wyjściowego
python streets.py 309474 kudowa_zdroj_streets.json
```

Skrypt pobierze listę ulic dla wybranej gminy i zapisze ją do pliku JSON.

#### 3. Pobieranie harmonogramu wywozu śmieci

```bash
# Sposób 1: Skrypt zapyta o ID gminy i nazwę ulicy
python schedule.py

# Sposób 2: Podaj ID gminy i nazwę ulicy jako argumenty
python schedule.py 309707 "Cicha"

# Sposób 3: Podaj ID gminy, nazwę ulicy i nazwę pliku wyjściowego
python schedule.py 309707 "Cicha" moj_harmonogram.json
```

Skrypt pobierze harmonogram wywozu śmieci dla wybranej gminy i ulicy i zapisze go do pliku JSON.

### Struktura danych

#### Plik municipalities.json

```json
[
    {
        "id": "309503",
        "province": "dolnośląskie",
        "district": "górowski",
        "municipality": "Niechlów",
        "full_name": "woj.: dolnośląskie powiat: górowski gmina: Niechlów"
    },
    ...
]
```

#### Plik streets_municipality_XXX.json

```json
{
    "municipality_id": "309474",
    "municipality_name": "Kudowa-Zdrój",
    "streets": [
        "1 Maja",
        "Adama Mickiewicza",
        ...
    ],
    "total_streets": 58
}
```

#### Plik schedule_municipality_XXX_YYY.json

```json
{
    "municipality_id": "309707",
    "street": "Cicha",
    "retrieval_date": "2025-04-07 12:34:56",
    "schedule": [
        {
            "date": "2025-04-09",
            "weekday": "środa",
            "waste_type": "biodegradowalne",
            "waste_id": "B",
            "color": "#9F703B"
        },
        ...
    ],
    "waste_types": {
        "B": {
            "name": "biodegradowalne",
            "dates": [
                {
                    "date": "2025-04-09",
                    "weekday": "środa"
                },
                ...
            ]
        },
        ...
    },
    "total_dates": 32
}
```

## English

### Description

A set of scripts for fetching and processing waste collection schedules from https://kiedysmieci.info/

The set consists of three scripts:

1. `municipalities.py` - fetches the list of municipalities available in the system
2. `streets.py` - fetches the list of streets for a selected municipality
3. `schedule.py` - fetches the waste collection schedule for a selected municipality and street

### Requirements

The scripts require Python 3.6+ and the following libraries:

- requests
- beautifulsoup4

You can install the required libraries with the command:

```bash
pip install requests beautifulsoup4
```

### Usage

#### 1. Fetching the list of municipalities

```bash
python municipalities.py
```

The script will fetch the list of all available municipalities and save it to the `municipalities.json` file.

#### 2. Fetching the list of streets for a selected municipality

```bash
# Method 1: The script will ask for the municipality ID
python streets.py

# Method 2: Provide the municipality ID as an argument
python streets.py 309474

# Method 3: Provide the municipality ID and the output filename
python streets.py 309474 kudowa_zdroj_streets.json
```

The script will fetch the list of streets for the selected municipality and save it to a JSON file.

#### 3. Fetching the waste collection schedule

```bash
# Method 1: The script will ask for the municipality ID and street name
python schedule.py

# Method 2: Provide the municipality ID and street name as arguments
python schedule.py 309707 "Cicha"

# Method 3: Provide the municipality ID, street name, and output filename
python schedule.py 309707 "Cicha" my_schedule.json
```

The script will fetch the waste collection schedule for the selected municipality and street and save it to a JSON file.

### Data Structure

#### municipalities.json file

```json
[
    {
        "id": "309503",
        "province": "dolnośląskie",
        "district": "górowski",
        "municipality": "Niechlów",
        "full_name": "woj.: dolnośląskie powiat: górowski gmina: Niechlów"
    },
    ...
]
```

#### streets_municipality_XXX.json file

```json
{
    "municipality_id": "309474",
    "municipality_name": "Kudowa-Zdrój",
    "streets": [
        "1 Maja",
        "Adama Mickiewicza",
        ...
    ],
    "total_streets": 58
}
```

#### schedule_municipality_XXX_YYY.json file

```json
{
    "municipality_id": "309707",
    "street": "Cicha",
    "retrieval_date": "2025-04-07 12:34:56",
    "schedule": [
        {
            "date": "2025-04-09",
            "weekday": "środa",
            "waste_type": "biodegradowalne",
            "waste_id": "B",
            "color": "#9F703B"
        },
        ...
    ],
    "waste_types": {
        "B": {
            "name": "biodegradowalne",
            "dates": [
                {
                    "date": "2025-04-09",
                    "weekday": "środa"
                },
                ...
            ]
        },
        ...
    },
    "total_dates": 32
}
```

### Legend for waste types

- B - biodegradable waste (biodegradowalne)
- PO - ash (popiół)
- PL - metals and plastics (metale i tworzywa sztuczne)
- PA - paper and cardboard (papier i tektura)
- SZ - glass (szkło)
- ZM - mixed waste (zmieszane)
