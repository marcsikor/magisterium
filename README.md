# ETL – Full Load and Incremental Load

Projekt stanowi część pracy magisterskiej i przedstawia implementację procesu **ETL (Extract, Transform, Load)** służącego do ładowania danych ze źródłowej bazy danych do docelowego hurtowego modelu danych (**Data Warehouse**).

Projekt obejmuje dwa scenariusze ładowania danych:

* **Full Load** – pełne załadowanie danych ze źródłowej bazy danych do hurtowni danych,
* **Incremental Load** – przyrostowe ładowanie danych, obejmujące jedynie dane, które zostały dodane lub zmodyfikowane od czasu poprzedniego uruchomienia procesu.

## Struktura projektu

```text
.
├── etl_full_load.py
├── etl_incremental_load.py
├── source_database.sql
├── target_data_warehouse.sql
├── .env.example
├── requirements.txt
├── .gitignore
└── README.md
```

### Opis plików

| Plik                        | Opis                                                                    |
| --------------------------- | ----------------------------------------------------------------------- |
| `etl_full_load.py`          | Implementacja pełnego procesu ETL (Full Load).                          |
| `etl_incremental_load.py`   | Implementacja przyrostowego procesu ETL (Incremental Load).             |
| `source_database.sql`       | Schemat źródłowej bazy danych.                                          |
| `target_data_warehouse.sql` | Schemat docelowej hurtowni danych.                                      |
| `.env.example`              | Przykładowowy plik zmiennych środowiskowych wymaganych przez aplikację. |
| `requirements.txt`          | Lista wymaganych bibliotek Python.                                      |
| `.gitignore`                | Pliki i katalogi wykluczone z repozytorium Git.                         |

## Wymagania

Do uruchomienia projektu wymagane są:

* Python 3.x
* PostgreSQL
* `pip`
* dostęp do źródłowej bazy danych,
* dostęp do docelowej bazy danych.

W zależności od konfiguracji środowiska PostgreSQL może być uruchomiony lokalnie lub za pomocą Dockera.

## Instalacja

Sklonuj repozytorium:

```bash
git clone <URL_REPOZYTORIUM>
cd <NAZWA_REPOZYTORIUM>
```

Następnie utwórz środowisko wirtualne:

```bash
python -m venv .venv
```

Aktywacja środowiska:

### Linux / macOS

```bash
source .venv/bin/activate
```

### Windows

```powershell
.venv\Scripts\activate
```

Zainstaluj wymagane zależności:

```bash
pip install -r requirements.txt
```

## Konfiguracja

Projekt wykorzystuje zmienne środowiskowe do konfiguracji połączeń z bazami danych.

Skopiuj plik `.env.example` do `.env`:

```bash
cp .env.example .env
```

Na systemie Windows można wykonać to polecenie w PowerShell:

```powershell
Copy-Item .env.example .env
```

Następnie uzupełnij plik `.env` odpowiednimi wartościami.

Przykładowa konfiguracja:

```env
SOURCE_DB_HOST=localhost
SOURCE_DB_PORT=5432
SOURCE_DB_NAME=source_database
SOURCE_DB_USER=postgres
SOURCE_DB_PASSWORD=your_password

TARGET_DB_HOST=localhost
TARGET_DB_PORT=5432
TARGET_DB_NAME=target_data_warehouse
TARGET_DB_USER=postgres
TARGET_DB_PASSWORD=your_password
```

> **Uwaga:** plik `.env` zawierający rzeczywiste dane dostępowe nie powinien być dodawany do repozytorium. Powinien znajdować się w `.gitignore`. Do repozytorium należy dodawać jedynie `.env.example`.

## Przygotowanie baz danych

Przed uruchomieniem procesów ETL należy utworzyć i skonfigurować obie bazy danych:

1. źródłową bazę danych,
2. docelową hurtownię danych.

Schemat źródłowej bazy znajduje się w:

```text
source_database.sql
```

Schemat docelowej hurtowni danych znajduje się w:

```text
target_data_warehouse.sql
```

Przykładowe utworzenie schematu bazy za pomocą `psql`:

```bash
psql -h localhost -p 5432 -U postgres -d source_database -f source_database.sql
```

oraz dla hurtowni danych:

```bash
psql -h localhost -p 5432 -U postgres -d target_data_warehouse -f target_data_warehouse.sql
```

Parametry połączenia należy dostosować do lokalnej konfiguracji PostgreSQL.

## Full Load

Proces **Full Load** służy do pełnego załadowania danych ze źródłowej bazy danych do docelowej hurtowni danych.

Uruchomienie:

```bash
python etl_full_load.py
```

Proces obejmuje trzy podstawowe etapy:

```text
Source Database
       │
       ▼
    Extract
       │
       ▼
   Transform
       │
       ▼
      Load
       │
       ▼
Target Data Warehouse
```

W ramach procesu dane są pobierane ze źródła, poddawane wymaganym transformacjom, a następnie ładowane do odpowiednich struktur docelowej hurtowni danych.

## Incremental Load

Proces **Incremental Load** służy do przyrostowego ładowania danych.

W przeciwieństwie do pełnego ładowania proces nie przetwarza każdorazowo całego zbioru danych, lecz identyfikuje dane wymagające załadowania lub aktualizacji na podstawie mechanizmu przyjętego w implementacji.

Uruchomienie:

```bash
python etl_incremental_load.py
```

Ogólny przebieg:

```text
Source Database
       │
       ▼
 Identify new/changed data
       │
       ▼
    Extract
       │
       ▼
   Transform
       │
       ▼
      Load
       │
       ▼
Target Data Warehouse
```

Takie podejście pozwala ograniczyć ilość danych przetwarzanych podczas kolejnych uruchomień procesu ETL.

## Schemat rozwiązania

Projekt można przedstawić w uproszczeniu jako następujący przepływ:

```text
┌──────────────────────┐
│   Source Database    │
│                      │
│ source_database.sql  │
└──────────┬───────────┘
           │
           │ Extract
           ▼
┌──────────────────────┐
│         ETL          │
│                      │
│  Transform / Load    │
└──────────┬───────────┘
           │
           │ Load
           ▼
┌──────────────────────────┐
│   Target Data Warehouse  │
│                          │
│ target_data_warehouse.sql│
└──────────────────────────┘
```

W projekcie zaimplementowano dwa warianty procesu:

```text
                 ┌─── Full Load ────────► Data Warehouse
                 │
Source Database ─┤
                 │
                 └─── Incremental Load ─► Data Warehouse
```

## Technologie

Projekt wykorzystuje następujące technologie:

* **Python** – implementacja procesów ETL,
* **PostgreSQL** – źródłowa baza danych oraz docelowa hurtownia danych,
* **SQL** – definicja struktur baz danych,
* **python-dotenv** – obsługa zmiennych środowiskowych,
* **Git** – kontrola wersji.

Pełna lista zależności znajduje się w pliku:

```text
requirements.txt
```

## Bezpieczeństwo

Dane uwierzytelniające oraz inne informacje konfiguracyjne związane ze środowiskiem uruchomieniowym nie są przechowywane bezpośrednio w kodzie źródłowym.

Do konfiguracji wykorzystywany jest plik `.env`, który nie powinien być wersjonowany.

W repozytorium znajduje się natomiast:

```text
.env.example
```

zawierający przykład wymaganych zmiennych środowiskowych bez rzeczywistych danych uwierzytelniających.

## Reprodukowalność eksperymentu

Projekt został przygotowany w sposób umożliwiający odtworzenie procesu ETL w innym środowisku.

W celu odtworzenia eksperymentu należy:

1. zainstalować wymagane oprogramowanie,
2. zainstalować zależności Python z `requirements.txt`,
3. utworzyć źródłową bazę danych,
4. utworzyć docelową hurtownię danych,
5. skonfigurować zmienne środowiskowe w pliku `.env`,
6. uruchomić proces `Full Load`,
7. uruchomić proces `Incremental Load`,
8. porównać wyniki oraz charakterystykę obu sposobów ładowania danych.

## Cel projektu

Głównym celem projektu jest implementacja i porównanie dwóch sposobów ładowania danych do hurtowni danych:

* pełnego ładowania (**Full Load**),
* przyrostowego ładowania (**Incremental Load**).

Rozwiązanie stanowi element praktycznej części pracy magisterskiej poświęconej procesom ETL oraz efektywnemu przetwarzaniu danych w środowisku hurtowni danych.
