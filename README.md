# TrashDay - Integracja harmonogramów wywozu śmieci dla Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/wachcio/hacs_trash_day_schedule.svg)](https://github.com/wachcio/hacs_trash_day_schedule/releases)

Integracja Home Assistant pobierająca i wyświetlająca harmonogramy wywozu śmieci z serwisu [kiedysmieci.info](https://kiedysmieci.info/).

## Funkcje

- Automatyczne pobieranie listy gmin i ulic obsługiwanych przez serwis
- Wyświetlanie nadchodzących wywozów śmieci różnego typu (bio, zmieszane, plastik, papier, szkło, popiół)
- Regularne aktualizacje harmonogramów
- Gotowe karty do dashboardu Home Assistant
- Przykładowe automatyzacje do powiadomień o nadchodzących wywozach

## Instalacja

### Przez HACS (zalecane)

1. Upewnij się, że masz zainstalowany [HACS](https://hacs.xyz/)
2. Dodaj to repozytorium jako niestandardowe repozytorium w HACS:
   - Przejdź do HACS -> Integracje
   - Kliknij menu (trzy kropki w prawym górnym rogu)
   - Wybierz "Niestandardowe repozytoria"
   - Dodaj URL: `https://github.com/wachcio/hacs_trash_day_schedule`
   - Kategoria: Integracja
3. Kliknij na "Explore & Download Repositories" i wyszukaj "TrashDay"
4. Kliknij "Pobierz"
5. Uruchom ponownie Home Assistant

### Ręcznie

1. Pobierz najnowszą wersję z [strony Releases](https://github.com/wachcio/hacs_trash_day_schedule/releases)
2. Rozpakuj zawartość do katalogu `custom_components` w twoim Home Assistant
   - Upewnij się, że katalog ma nazwę `trash_day` (nie `hacs_trash_day_schedule-main` itp.)
3. Uruchom ponownie Home Assistant

## Konfiguracja

1. Przejdź do Ustawienia -> Urządzenia i usługi
2. Kliknij przycisk "+ Dodaj integrację" w prawym dolnym rogu
3. Wyszukaj "TrashDay" lub "Wywóz śmieci"
4. Postępuj zgodnie z instrukcjami:
   - Wybierz swoją gminę z listy
   - Wybierz swoją ulicę
   - Opcjonalnie: skonfiguruj częstotliwość aktualizacji (domyślnie 12 godzin)

## Dostępne encje

Po skonfigurowaniu integracji dostępne będą następujące encje:

- `sensor.next_waste_collection_[NAZWA_ULICY]` - informuje o najbliższym wywozie
- `sensor.biodegradable_collection_[NAZWA_ULICY]` - wywóz odpadów biodegradowalnych
- `sensor.mixed_collection_[NAZWA_ULICY]` - wywóz odpadów zmieszanych
- `sensor.plastic_and_metal_collection_[NAZWA_ULICY]` - wywóz plastiku i metali
- `sensor.paper_collection_[NAZWA_ULICY]` - wywóz papieru
- `sensor.glass_collection_[NAZWA_ULICY]` - wywóz szkła
- `sensor.ash_collection_[NAZWA_ULICY]` - wywóz popiołu

Każda encja
