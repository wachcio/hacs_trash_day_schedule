# Karty Lovelace dla integracji TrashDay

Ten katalog zawiera przykładowe karty Lovelace, które możesz użyć do wyświetlenia informacji o harmonogramie wywozu śmieci w interfejsie Home Assistant.

## Jak używać kart

1. Wybierz jedną z dostępnych kart i skopiuj jej zawartość
2. W interfejsie Home Assistant przejdź do wybranego dashboardu
3. Kliknij przycisk edycji (trzy kropki w prawym górnym rogu) i wybierz "Edytuj Dashboard"
4. Kliknij przycisk "+" aby dodać nową kartę
5. Wybierz "Ręczny" lub "YAML" (zależnie od wersji Home Assistant)
6. Wklej skopiowaną zawartość karty
7. **Ważne**: Zastąp `your_street` w `sensor.next_waste_collection_your_street` i innych encjach nazwą Twojej ulicy

## Dostępne karty

### `cards.yaml`

Standardowa karta używająca tylko wbudowanych komponentów Home Assistant. Pokazuje najbliższy wywóz, listę sensorów dla różnych typów odpadów i tabelę nadchodzących odbiorów.

### `cards_with_auto_entities.yaml`

Bardziej zaawansowana karta wykorzystująca niestandardową kartę `auto-entities`. **Uwaga**: Wymaga wcześniejszej instalacji [auto-entities](https://github.com/thomasloven/lovelace-auto-entities) przez HACS.

### `minimal_card.yaml`

Minimalistyczna karta pokazująca tylko najbliższy wywóz śmieci.

### `calendar_view.yaml`

Karta z widokiem kalendarza, pokazująca wywozy śmieci w formacie kalendarza.

## Instalacja dodatkowych komponentów

Niektóre karty mogą wymagać dodatkowych komponentów:

### Auto-entities

Instalacja przez HACS:

1. Przejdź do HACS -> Frontend
2. Kliknij "+" i wyszukaj "auto-entities"
3. Zainstaluj komponent

### Atomic Calendar Revive

Instalacja przez HACS:

1. Przejdź do HACS -> Frontend
2. Kliknij "+" i wyszukaj "atomic calendar revive"
3. Zainstaluj komponent

## Dostosowywanie kart

Możesz dostosować karty do swoich potrzeb:

- Zmień ikony i kolory
- Dodaj lub usuń sekcje
- Dostosuj układ i styl
- Dodaj dodatkowe informacje z atrybutów sensorów

## Przypomnienia i automatyzacje

Te karty możesz połączyć z automatyzacjami w Home Assistant, aby otrzymywać przypomnienia o nadchodzących wywozach śmieci. Przykładowa automatyzacja jest dostępna w sekcji `automations.yaml`.
