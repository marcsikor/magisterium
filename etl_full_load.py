import os
import traceback
from datetime import date, datetime, timedelta, timezone
from typing import TypedDict
import psycopg2
from psycopg2.extras import RealDictCursor, RealDictRow
from dotenv import load_dotenv

# loading .env file
if not load_dotenv():
    print("błąd przy ładowaniu pliku .env, używane zmienne systemowe")

# typing connection dictionaries
class DbConn(TypedDict):
    host: str | None
    port: int
    dbname: str | None
    user: str | None
    password: str | None

# ============================================================
# KONFIGURACJA
# ============================================================

SOURCE_DB: DbConn = {
    "host": os.getenv("SOURCE_DB_HOST"),
    "port": int(os.getenv("SOURCE_DB_PORT") or 0), # COALESCE() equivalent
    "dbname": os.getenv("SOURCE_DB_NAME"),
    "user": os.getenv("SOURCE_DB_USER"),
    "password": os.getenv("SOURCE_DB_PASSWORD"),
}

TARGET_DB: DbConn = {
    "host": os.getenv("TARGET_DB_HOST"),
    "port": int(os.getenv("TARGET_DB_PORT") or 0),
    "dbname": os.getenv("TARGET_DB_NAME"),
    "user": os.getenv("TARGET_DB_USER"),
    "password": os.getenv("TARGET_DB_PASSWORD"),
}


# ============================================================
# POŁĄCZENIA
# ============================================================

def connect_source() -> "psycopg2.extensions.connection":
    ''' source db connection '''
    return psycopg2.connect(**SOURCE_DB)


def connect_target() -> "psycopg2.extensions.connection":
    ''' target db connection '''
    return psycopg2.connect(**TARGET_DB)


# ============================================================
# ETL LOGGING & WATERMARK HELPERS
# ============================================================

def log_etl_start(target_conn: "psycopg2.extensions.connection", process_name: str) -> int:
    ''' Tworzy wpis początkowy w etl_log i zwraca wygenerowane etl_log_id '''
    with target_conn.cursor() as cur:
        cur.execute("""
            INSERT INTO etl_log (process_name, start_time, status)
            VALUES (%s, CURRENT_TIMESTAMP, 'RUNNING')
            RETURNING etl_log_id;
        """, (process_name,))
        response: tuple[int, ...] | None = cur.fetchone()
        if response is None:
            raise ValueError('Response NULL.')
        log_id = response[0]
    target_conn.commit()
    return log_id


def log_etl_end(
    target_conn: "psycopg2.extensions.connection", 
    log_id: int, 
    status: str, 
    rows_processed: int = 0, 
    error_message: str | None = None
) -> None:
    ''' Aktualizuje status oraz metryki w tabeli etl_log '''
    with target_conn.cursor() as cur:
        cur.execute("""
            UPDATE etl_log
            SET end_time = CURRENT_TIMESTAMP,
                status = %s,
                rows_processed = %s,
                error_message = %s
            WHERE etl_log_id = %s;
        """, (status, rows_processed, error_message, log_id))
    target_conn.commit()


def update_watermark(target_conn: "psycopg2.extensions.connection", process_name: str, last_success_time: datetime) -> None:
    ''' Aktualizuje lub tworzy wpis w etl_watermark '''
    with target_conn.cursor() as cur:
        cur.execute("""
            INSERT INTO etl_watermark (process_name, last_successful_run)
            VALUES (%s, %s)
            ON CONFLICT (process_name) 
            DO UPDATE SET last_successful_run = EXCLUDED.last_successful_run;
        """, (process_name, last_success_time))
    target_conn.commit()


# ============================================================
# CZYSZCZENIE DWH
# ============================================================

def clear_dwh(target_conn: "psycopg2.extensions.connection") -> None:
    ''' prawdopodobnie niepotrzebna metoda do truncowania wszystkich tabel '''
    
    print("Czyszczenie bazy analitycznej...")

    with target_conn.cursor() as cur:
        cur.execute("""
            TRUNCATE TABLE
                fact_operacja,
                dim_dokument,
                dim_konto,
                dim_kontrahent,
                dim_czas
            RESTART IDENTITY CASCADE;
        """)

    target_conn.commit()

    print("Baza analityczna wyczyszczona.")


# ============================================================
# DIM_KONTRAHENT
# ============================================================

def load_dim_kontrahent(source_conn: "psycopg2.extensions.connection", target_conn: "psycopg2.extensions.connection") -> int:
    print("Ładowanie dim_kontrahent...")

    # query source
    with source_conn.cursor(cursor_factory=RealDictCursor) as src:
        src.execute("""
            SELECT
                kontrahentid,
                nazwa,
                nip,
                adres,
                typkontrahenta
            FROM kontrahent
            ORDER BY kontrahentid;
        """)

        rows: list[RealDictRow] = src.fetchall()

    # dml on target
    with target_conn.cursor() as tgt:
        for row in rows:
            tgt.execute("""
                INSERT INTO dim_kontrahent (
                    kontrahent_id,
                    nazwa,
                    nip,
                    adres,
                    typkontrahenta,
                    datautworzenia,
                    datamodyfikacji
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                );
            """, (
                row["kontrahentid"],
                row["nazwa"],
                row["nip"],
                row["adres"],
                row["typkontrahenta"],
            ))

    target_conn.commit()

    print(f"dim_kontrahent: {len(rows)} rekordów.")
    return len(rows)


# ============================================================
# DIM_KONTO
# ============================================================

def load_dim_konto(source_conn: "psycopg2.extensions.connection", target_conn: "psycopg2.extensions.connection") -> int:
    print("Ładowanie dim_konto...")

    with source_conn.cursor(cursor_factory=RealDictCursor) as src:
        src.execute("""
            SELECT
                kontoid,
                numerkonta,
                nazwakonta,
                typkonta
            FROM kontoksiegowe
            ORDER BY kontoid;
        """)

        rows = src.fetchall()

    with target_conn.cursor() as tgt:
        for row in rows:
            tgt.execute("""
                INSERT INTO dim_konto (
                    konto_id,
                    numerkonta,
                    nazwakonta,
                    typkonta,
                    datautworzenia,
                    datamodyfikacji
                )
                VALUES (
                    %s, %s, %s, %s,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                );
            """, (
                row["kontoid"],
                row["numerkonta"],
                row["nazwakonta"],
                row["typkonta"],
            ))

    target_conn.commit()

    print(f"dim_konto: {len(rows)} rekordów.")
    return len(rows)


# ============================================================
# DIM_DOKUMENT
# ============================================================

def load_dim_dokument(source_conn: "psycopg2.extensions.connection", target_conn: "psycopg2.extensions.connection") -> int:
    print("Ładowanie dim_dokument...")

    with source_conn.cursor(cursor_factory=RealDictCursor) as src:
        src.execute("""
            SELECT
                dokumentid,
                numerdokumentu,
                datawystawienia,
                dataksiegowania,
                opis
            FROM dokumentksiegowy
            ORDER BY dokumentid;
        """)

        rows = src.fetchall()

    with target_conn.cursor() as tgt:
        for row in rows:
            tgt.execute("""
                INSERT INTO dim_dokument (
                    dokument_id,
                    numerdokumentu,
                    data_wystawienia,
                    data_ksiegowania,
                    opis,
                    datautworzenia,
                    datamodyfikacji
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                );
            """, (
                row["dokumentid"],
                row["numerdokumentu"],
                row["datawystawienia"],
                row["dataksiegowania"],
                row["opis"],
            ))

    target_conn.commit()

    print(f"dim_dokument: {len(rows)} rekordów.")
    return len(rows)


# ============================================================
# DIM_CZAS
# ============================================================

def load_dim_czas(source_conn: "psycopg2.extensions.connection", target_conn: "psycopg2.extensions.connection") -> int:
    print("Ładowanie dim_czas...")

    # Pobieramy wszystkie daty występujące w dokumentach.
    with source_conn.cursor() as src:
        src.execute("""
            SELECT datawystawienia
            FROM dokumentksiegowy

            UNION

            SELECT dataksiegowania
            FROM dokumentksiegowy

            ORDER BY 1;
        """)

        rows: list[tuple[date | None]] = src.fetchall()

    dates: list[date] = [row[0] for row in rows if row[0] is not None]

    # Jeżeli nie ma żadnych dat, nic nie robimy.
    if not dates:
        print("dim_czas: brak dat do załadowania.")
        return 0

    min_date: date = min(dates)
    max_date: date = max(dates)

    current_date = min_date
    inserted = 0

    month_names = {
        1: "Styczeń",
        2: "Luty",
        3: "Marzec",
        4: "Kwiecień",
        5: "Maj",
        6: "Czerwiec",
        7: "Lipiec",
        8: "Sierpień",
        9: "Wrzesień",
        10: "Październik",
        11: "Listopad",
        12: "Grudzień",
    }

    with target_conn.cursor() as tgt:
        while current_date <= max_date:

            month = current_date.month
            quarter = ((month - 1) // 3) + 1

            tgt.execute("""
                INSERT INTO dim_czas (
                    data,
                    dzien,
                    miesiac,
                    nazwa_miesiaca,
                    kwartal,
                    rok,
                    datautworzenia,
                    datamodyfikacji
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                );
            """, (
                current_date,
                current_date.day,
                month,
                month_names[month],
                quarter,
                current_date.year,
            ))

            inserted += 1
            current_date += timedelta(days=1)

    target_conn.commit()

    print(
        f"dim_czas: {inserted} rekordów " +
        f"({min_date} - {max_date})."
    )
    return inserted


# ============================================================
# FACT_OPERACJA
# ============================================================

def load_fact_operacja(source_conn: "psycopg2.extensions.connection", target_conn: "psycopg2.extensions.connection") -> int:
    print("Ładowanie fact_operacja...")

    # --------------------------------------------------------
    # Pobranie danych źródłowych
    # --------------------------------------------------------

    with source_conn.cursor(cursor_factory=RealDictCursor) as src:
        src.execute("""
            SELECT
                p.pozycjaid,
                p.dokumentid,
                p.kontoid,
                p.kwota,
                p.strona,
                p.opis,

                d.kontrahentid,
                d.datawystawienia,
                d.dataksiegowania

            FROM pozycjadokumentu p
            JOIN dokumentksiegowy d
                ON d.dokumentid = p.dokumentid

            ORDER BY p.pozycjaid;
        """)

        rows = src.fetchall()

    # --------------------------------------------------------
    # Pobranie map kluczy zastępczych z wymiarów
    # --------------------------------------------------------

    with target_conn.cursor(cursor_factory=RealDictCursor) as tgt:

        tgt.execute("""
            SELECT
                kontrahent_key,
                kontrahent_id
            FROM dim_kontrahent;
        """)
        kontrahent_map = {
            row["kontrahent_id"]: row["kontrahent_key"]
            for row in tgt.fetchall()
        }

        tgt.execute("""
            SELECT
                konto_key,
                konto_id
            FROM dim_konto;
        """)
        konto_map = {
            row["konto_id"]: row["konto_key"]
            for row in tgt.fetchall()
        }

        tgt.execute("""
            SELECT
                dokument_key,
                dokument_id
            FROM dim_dokument;
        """)
        dokument_map = {
            row["dokument_id"]: row["dokument_key"]
            for row in tgt.fetchall()
        }

        tgt.execute("""
            SELECT
                czas_key,
                data
            FROM dim_czas;
        """)
        czas_map = {
            row["data"]: row["czas_key"]
            for row in tgt.fetchall()
        }

    # --------------------------------------------------------
    # Ładowanie faktów
    # --------------------------------------------------------

    inserted = 0
    skipped = 0

    with target_conn.cursor() as tgt:

        for row in rows:

            dokument_key = dokument_map.get(row["dokumentid"])
            konto_key = konto_map.get(row["kontoid"])
            kontrahent_key = kontrahent_map.get(row["kontrahentid"])

            # Do faktu wykorzystujemy datę księgowania.
            czas_key = czas_map.get(row["dataksiegowania"])

            # Jeżeli któregoś klucza brakuje, pomijamy rekord.
            if dokument_key is None:
                print(
                    f"UWAGA: brak dokument_key dla " +
                    f"dokumentid={row['dokumentid']}"
                )
                skipped += 1
                continue

            if konto_key is None:
                print(
                    f"UWAGA: brak konto_key dla " +
                    f"kontoid={row['kontoid']}"
                )
                skipped += 1
                continue

            if kontrahent_key is None:
                print(
                    f"UWAGA: brak kontrahent_key dla " +
                    f"kontrahentid={row['kontrahentid']}"
                )
                skipped += 1
                continue

            if czas_key is None:
                print(
                    f"UWAGA: brak czas_key dla " +
                    f"daty={row['dataksiegowania']}"
                )
                skipped += 1
                continue

            tgt.execute("""
                INSERT INTO fact_operacja (
                    czas_key,
                    kontrahent_key,
                    konto_key,
                    dokument_key,
                    pozycja_id,
                    kwota,
                    strona,
                    opis,
                    datautworzenia,
                    datamodyfikacji
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                );
            """, (
                czas_key,
                kontrahent_key,
                konto_key,
                dokument_key,
                row["pozycjaid"],
                row["kwota"],
                row["strona"],
                row["opis"],
            ))

            inserted += 1

    target_conn.commit()

    print(f"fact_operacja: {inserted} rekordów.")
    print(f"Pominięto: {skipped} rekordów.")

    return inserted


# ============================================================
# GŁÓWNY ETL
# ============================================================

def main():

    process_name = "main_etl"

    print("=" * 60)
    print("START ETL")
    print("=" * 60)

    source_conn = None
    target_conn = None
    log_id = None
    total_rows_processed = 0

    try:

        # ----------------------------------------------------
        # Połączenie
        # ----------------------------------------------------

        print("Łączenie ze źródłową bazą...")
        source_conn = connect_source()
        print("Połączono ze źródłem.")

        print("Łączenie z bazą analityczną...")
        target_conn = connect_target()
        print("Połączono z targetem.")

        # ----------------------------------------------------
        # Rozpoczęcie logowania
        # ----------------------------------------------------

        log_id = log_etl_start(target_conn, process_name)

        # ----------------------------------------------------
        # Czyszczenie
        # ----------------------------------------------------

        clear_dwh(target_conn)

        # ----------------------------------------------------
        # Wymiary
        # ----------------------------------------------------

        total_rows_processed += load_dim_kontrahent(
            source_conn,
            target_conn
        )

        total_rows_processed += load_dim_konto(
            source_conn,
            target_conn
        )

        total_rows_processed += load_dim_dokument(
            source_conn,
            target_conn
        )

        total_rows_processed += load_dim_czas(
            source_conn,
            target_conn
        )

        # ----------------------------------------------------
        # Fakt
        # ----------------------------------------------------

        total_rows_processed += load_fact_operacja(
            source_conn,
            target_conn
        )

        # ----------------------------------------------------
        # Zakończenie logowania i watermark
        # ----------------------------------------------------

        run_timestamp = datetime.now(timezone.utc)

        log_etl_end(
            target_conn=target_conn,
            log_id=log_id,
            status="SUCCESS",
            rows_processed=total_rows_processed,
            error_message=None
        )

        update_watermark(
            target_conn=target_conn,
            process_name=process_name,
            last_success_time=run_timestamp
        )

        print("=" * 60)
        print("ETL ZAKOŃCZONY POMYŚLNIE")
        print("=" * 60)

    except Exception as e:

        print("=" * 60)
        print("BŁĄD ETL")
        print("=" * 60)

        err_msg = str(e)
        print(err_msg)

        if target_conn:
            target_conn.rollback()

            if log_id is not None:
                log_etl_end(
                    target_conn=target_conn,
                    log_id=log_id,
                    status="FAILED",
                    rows_processed=total_rows_processed,
                    error_message=traceback.format_exc()
                )

        raise

    finally:

        if source_conn:
            source_conn.close()

        if target_conn:
            target_conn.close()


if __name__ == "__main__":
    main()