import os
from datetime import date, datetime, timedelta, timezone
from typing import TypedDict, cast
from decimal import Decimal

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor, RealDictRow


# ============================================================
# ŁADOWANIE .env
# ============================================================

if not load_dotenv():
    print("Błąd przy ładowaniu pliku .env, używane zmienne systemowe")


# ============================================================
# TYPY
# ============================================================

class DbConn(TypedDict):
    host: str | None
    port: int
    dbname: str | None
    user: str | None
    password: str | None


class WatermarkRow(TypedDict):
    last_successful_run: datetime | None


class CountRow(TypedDict):
    count: int


# ============================================================
# KONFIGURACJA
# ============================================================

SOURCE_DB: DbConn = {
    "host": os.getenv("SOURCE_DB_HOST"),
    "port": int(os.getenv("SOURCE_DB_PORT") or 0),
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

def connect_source() -> psycopg2.extensions.connection:
    """Połączenie ze źródłową bazą danych."""
    return psycopg2.connect(**SOURCE_DB)


def connect_target() -> psycopg2.extensions.connection:
    """Połączenie z docelową bazą analityczną."""
    return psycopg2.connect(**TARGET_DB)


# ============================================================
# ETL WATERMARK
# ============================================================

def get_watermark(
    target_conn: psycopg2.extensions.connection,
) -> datetime | None:
    """
    Pobiera czas ostatniego poprawnego uruchomienia ETL.

    Jeżeli watermark nie istnieje, zwracane jest None.
    """

    with target_conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT last_successful_run
            FROM etl_watermark
            WHERE process_name = %s;
            """,
            ("main_etl",),
        )

        row: RealDictRow | None = cur.fetchone()

    if row is None:
        return None

    last_successful_run: datetime | None = cast(
        datetime | None,
        row["last_successful_run"],
    )

    return last_successful_run


def update_watermark(
    target_conn: psycopg2.extensions.connection,
    successful_run: datetime,
) -> None:
    """Aktualizuje czas ostatniego poprawnego uruchomienia ETL."""

    with target_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO etl_watermark (
                process_name,
                last_successful_run
            )
            VALUES (%s, %s)
            ON CONFLICT (process_name)
            DO UPDATE SET
                last_successful_run = EXCLUDED.last_successful_run;
            """,
            ("main_etl", successful_run),
        )

    target_conn.commit()


# ============================================================
# ETL LOG
# ============================================================

def start_etl_log(
    target_conn: psycopg2.extensions.connection,
    started_at: datetime,
) -> int:
    """Tworzy wpis logu rozpoczęcia procesu ETL."""

    with target_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO etl_log (
                process_name,
                start_time,
                status
            )
            VALUES (%s, %s, %s)
            RETURNING etl_log_id;
            """,
            (
                "main_etl",
                started_at,
                "RUNNING",
            ),
        )

        result = cur.fetchone()

    if result is None:
        raise RuntimeError("Nie udało się utworzyć wpisu w etl_log.")

    etl_log_id: int = cast(int, result[0])

    target_conn.commit()

    return etl_log_id


def finish_etl_log(
    target_conn: psycopg2.extensions.connection,
    etl_log_id: int,
    status: str,
    rows_processed: int,
    error_message: str | None = None,
) -> None:
    """Aktualizuje wpis logu po zakończeniu procesu ETL."""

    finished_at = datetime.now(timezone.utc)

    with target_conn.cursor() as cur:
        cur.execute(
            """
            UPDATE etl_log
            SET
                end_time = %s,
                status = %s,
                rows_processed = %s,
                error_message = %s
            WHERE etl_log_id = %s;
            """,
            (
                finished_at,
                status,
                rows_processed,
                error_message,
                etl_log_id,
            ),
        )

    target_conn.commit()


# ============================================================
# DIM_KONTRAHENT
# ============================================================

def load_dim_kontrahent(
    source_conn: psycopg2.extensions.connection,
    target_conn: psycopg2.extensions.connection,
    watermark: datetime | None,
) -> int:
    """Przyrostowe zasilanie dim_kontrahent."""

    print("Ładowanie dim_kontrahent...")

    with source_conn.cursor(cursor_factory=RealDictCursor) as src:
        if watermark is None:
            src.execute(
                """
                SELECT
                    kontrahentid,
                    nazwa,
                    nip,
                    adres,
                    typkontrahenta,
                    datautworzenia,
                    datamodyfikacji
                FROM kontrahent
                ORDER BY kontrahentid;
                """
            )
        else:
            src.execute(
                """
                SELECT
                    kontrahentid,
                    nazwa,
                    nip,
                    adres,
                    typkontrahenta,
                    datautworzenia,
                    datamodyfikacji
                FROM kontrahent
                WHERE datamodyfikacji > %s
                ORDER BY kontrahentid;
                """,
                (watermark,),
            )

        rows: list[RealDictRow] = src.fetchall()

    with target_conn.cursor() as tgt:
        for row in rows:
            kontrahent_id = cast(int, row["kontrahentid"])
            nazwa = cast(str | None, row["nazwa"])
            nip = cast(str | None, row["nip"])
            adres = cast(str | None, row["adres"])
            typ_kontrahenta = cast(
                str | None,
                row["typkontrahenta"],
            )

            tgt.execute(
                """
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
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (kontrahent_id)
                DO UPDATE SET
                    nazwa = EXCLUDED.nazwa,
                    nip = EXCLUDED.nip,
                    adres = EXCLUDED.adres,
                    typkontrahenta = EXCLUDED.typkontrahenta,
                    datamodyfikacji = CURRENT_TIMESTAMP;
                """,
                (
                    kontrahent_id,
                    nazwa,
                    nip,
                    adres,
                    typ_kontrahenta,
                ),
            )

    target_conn.commit()

    print(
        f"dim_kontrahent: przetworzono {len(rows)} rekordów."
    )

    return len(rows)


# ============================================================
# DIM_KONTO
# ============================================================

def load_dim_konto(
    source_conn: psycopg2.extensions.connection,
    target_conn: psycopg2.extensions.connection,
    watermark: datetime | None,
) -> int:
    """Przyrostowe zasilanie dim_konto."""

    print("Ładowanie dim_konto...")

    with source_conn.cursor(cursor_factory=RealDictCursor) as src:
        if watermark is None:
            src.execute(
                """
                SELECT
                    kontoid,
                    numerkonta,
                    nazwakonta,
                    typkonta,
                    datautworzenia,
                    datamodyfikacji
                FROM kontoksiegowe
                ORDER BY kontoid;
                """
            )
        else:
            src.execute(
                """
                SELECT
                    kontoid,
                    numerkonta,
                    nazwakonta,
                    typkonta,
                    datautworzenia,
                    datamodyfikacji
                FROM kontoksiegowe
                WHERE datamodyfikacji > %s
                ORDER BY kontoid;
                """,
                (watermark,),
            )

        rows: list[RealDictRow] = src.fetchall()

    with target_conn.cursor() as tgt:
        for row in rows:
            konto_id = cast(int, row["kontoid"])
            numer_konta = cast(str, row["numerkonta"])
            nazwa_konta = cast(str, row["nazwakonta"])
            typ_konta = cast(str, row["typkonta"])

            tgt.execute(
                """
                INSERT INTO dim_konto (
                    konto_id,
                    numerkonta,
                    nazwakonta,
                    typkonta,
                    datautworzenia,
                    datamodyfikacji
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (konto_id)
                DO UPDATE SET
                    numerkonta = EXCLUDED.numerkonta,
                    nazwakonta = EXCLUDED.nazwakonta,
                    typkonta = EXCLUDED.typkonta,
                    datamodyfikacji = CURRENT_TIMESTAMP;
                """,
                (
                    konto_id,
                    numer_konta,
                    nazwa_konta,
                    typ_konta,
                ),
            )

    target_conn.commit()

    print(
        f"dim_konto: przetworzono {len(rows)} rekordów."
    )

    return len(rows)


# ============================================================
# DIM_DOKUMENT
# ============================================================

def load_dim_dokument(
    source_conn: psycopg2.extensions.connection,
    target_conn: psycopg2.extensions.connection,
    watermark: datetime | None,
) -> int:
    """Przyrostowe zasilanie dim_dokument."""

    print("Ładowanie dim_dokument...")

    with source_conn.cursor(cursor_factory=RealDictCursor) as src:
        if watermark is None:
            src.execute(
                """
                SELECT
                    dokumentid,
                    numerdokumentu,
                    datawystawienia,
                    dataksiegowania,
                    opis,
                    datautworzenia,
                    datamodyfikacji
                FROM dokumentksiegowy
                ORDER BY dokumentid;
                """
            )
        else:
            src.execute(
                """
                SELECT
                    dokumentid,
                    numerdokumentu,
                    datawystawienia,
                    dataksiegowania,
                    opis,
                    datautworzenia,
                    datamodyfikacji
                FROM dokumentksiegowy
                WHERE datamodyfikacji > %s
                ORDER BY dokumentid;
                """,
                (watermark,),
            )

        rows: list[RealDictRow] = src.fetchall()

    with target_conn.cursor() as tgt:
        for row in rows:
            dokument_id = cast(int, row["dokumentid"])
            numer_dokumentu = cast(
                str,
                row["numerdokumentu"],
            )
            data_wystawienia = cast(
                date | None,
                row["datawystawienia"],
            )
            data_ksiegowania = cast(
                date | None,
                row["dataksiegowania"],
            )
            opis = cast(str | None, row["opis"])

            tgt.execute(
                """
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
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (dokument_id)
                DO UPDATE SET
                    numerdokumentu = EXCLUDED.numerdokumentu,
                    data_wystawienia = EXCLUDED.data_wystawienia,
                    data_ksiegowania = EXCLUDED.data_ksiegowania,
                    opis = EXCLUDED.opis,
                    datamodyfikacji = CURRENT_TIMESTAMP;
                """,
                (
                    dokument_id,
                    numer_dokumentu,
                    data_wystawienia,
                    data_ksiegowania,
                    opis,
                ),
            )

    target_conn.commit()

    print(
        f"dim_dokument: przetworzono {len(rows)} rekordów."
    )

    return len(rows)


# ============================================================
# DIM_CZAS
# ============================================================

def load_dim_czas(
    source_conn: psycopg2.extensions.connection,
    target_conn: psycopg2.extensions.connection,
) -> int:
    """Uzupełnia dim_czas o brakujące daty."""

    print("Ładowanie dim_czas...")

    with source_conn.cursor() as src:
        src.execute(
            """
            SELECT datawystawienia
            FROM dokumentksiegowy
            WHERE datawystawienia IS NOT NULL

            UNION

            SELECT dataksiegowania
            FROM dokumentksiegowy
            WHERE dataksiegowania IS NOT NULL

            ORDER BY 1;
            """
        )

        rows: list[tuple[date]] = src.fetchall()

    dates: list[date] = [row[0] for row in rows]

    if not dates:
        print("dim_czas: brak dat do załadowania.")
        return 0

    min_date = min(dates)
    max_date = max(dates)

    month_names: dict[int, str] = {
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

    inserted = 0
    current_date = min_date

    with target_conn.cursor() as tgt:
        while current_date <= max_date:
            month = current_date.month
            quarter = ((month - 1) // 3) + 1

            tgt.execute(
                """
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
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (data)
                DO NOTHING;
                """,
                (
                    current_date,
                    current_date.day,
                    month,
                    month_names[month],
                    quarter,
                    current_date.year,
                ),
            )

            # Zliczamy tylko faktycznie dodane rekordy do bazy
            if tgt.rowcount > 0:
                inserted += 1

            current_date += timedelta(days=1)

    target_conn.commit()

    print(
        f"dim_czas: sprawdzono zakres {min_date} - {max_date}, " +
        f"wstawiono {inserted} nowych dat."
    )

    return inserted


# ============================================================
# FACT_OPERACJA
# ============================================================

def load_fact_operacja(
    source_conn: psycopg2.extensions.connection,
    target_conn: psycopg2.extensions.connection,
    watermark: datetime | None,
) -> int:
    """Przyrostowe zasilanie fact_operacja."""

    print("Ładowanie fact_operacja...")

    with source_conn.cursor(cursor_factory=RealDictCursor) as src:
        if watermark is None:
            src.execute(
                """
                SELECT
                    p.pozycjaid,
                    p.dokumentid,
                    p.kontoid,
                    p.kwota,
                    p.strona,
                    p.opis,
                    p.datautworzenia,
                    p.datamodyfikacji,
                    d.kontrahentid,
                    d.datawystawienia,
                    d.dataksiegowania
                FROM pozycjadokumentu p
                JOIN dokumentksiegowy d
                    ON d.dokumentid = p.dokumentid
                ORDER BY p.pozycjaid;
                """
            )
        else:
            src.execute(
                """
                SELECT
                    p.pozycjaid,
                    p.dokumentid,
                    p.kontoid,
                    p.kwota,
                    p.strona,
                    p.opis,
                    p.datautworzenia,
                    p.datamodyfikacji,
                    d.kontrahentid,
                    d.datawystawienia,
                    d.dataksiegowania
                FROM pozycjadokumentu p
                JOIN dokumentksiegowy d
                    ON d.dokumentid = p.dokumentid
                WHERE p.datamodyfikacji > %s
                   OR d.datamodyfikacji > %s
                ORDER BY p.pozycjaid;
                """,
                (
                    watermark,
                    watermark,
                ),
            )

        rows: list[RealDictRow] = src.fetchall()

    with target_conn.cursor(cursor_factory=RealDictCursor) as tgt:
        tgt.execute(
            """
            SELECT
                kontrahent_key,
                kontrahent_id
            FROM dim_kontrahent;
            """
        )

        kontrahent_map: dict[int, int] = {
            cast(int, row["kontrahent_id"]): cast(
                int,
                row["kontrahent_key"],
            )
            for row in tgt.fetchall()
        }

        tgt.execute(
            """
            SELECT
                konto_key,
                konto_id
            FROM dim_konto;
            """
        )

        konto_map: dict[int, int] = {
            cast(int, row["konto_id"]): cast(
                int,
                row["konto_key"],
            )
            for row in tgt.fetchall()
        }

        tgt.execute(
            """
            SELECT
                dokument_key,
                dokument_id
            FROM dim_dokument;
            """
        )

        dokument_map: dict[int, int] = {
            cast(int, row["dokument_id"]): cast(
                int,
                row["dokument_key"],
            )
            for row in tgt.fetchall()
        }

        tgt.execute(
            """
            SELECT
                czas_key,
                data
            FROM dim_czas;
            """
        )

        czas_map: dict[date, int] = {
            cast(date, row["data"]): cast(
                int,
                row["czas_key"],
            )
            for row in tgt.fetchall()
        }

    inserted = 0
    skipped = 0

    with target_conn.cursor() as tgt:
        for row in rows:

            # === MIEJSCE TESTU BŁĘDNYCH DANYCH ===
            # Sztucznie uszkadzamy pierwszy pobrany rekord
            # row["kontrahentid"] = 999999 
            # ======================================

            # === MIEJSCE TESTU BŁĘDU PROGRAMU ===
            # Wywołanie błędu
            # raise ValueError("BŁĄD TESTOWY: Wykryto niepoprawne dane w strumieniu danych wejściowych!")
            # ======================================

            dokument_id = cast(int, row["dokumentid"])
            konto_id = cast(int, row["kontoid"])
            kontrahent_id = cast(int, row["kontrahentid"])
            pozycja_id = cast(int, row["pozycjaid"])

            dokument_key = dokument_map.get(dokument_id)
            konto_key = konto_map.get(konto_id)
            kontrahent_key = kontrahent_map.get(kontrahent_id)

            data_ksiegowania = cast(
                date | None,
                row["dataksiegowania"],
            )

            czas_key = (
                czas_map.get(data_ksiegowania)
                if data_ksiegowania is not None
                else None
            )

            if dokument_key is None:
                print(
                    f"UWAGA: brak dokument_key " +
                    f"dla dokumentid={dokument_id}"
                )
                skipped += 1
                continue

            if konto_key is None:
                print(
                    f"UWAGA: brak konto_key " +
                    f"dla kontoid={konto_id}"
                )
                skipped += 1
                continue

            if kontrahent_key is None:
                print(
                    f"UWAGA: brak kontrahent_key " +
                    f"dla kontrahentid={kontrahent_id}"
                )
                skipped += 1
                continue

            if czas_key is None:
                print(
                    f"UWAGA: brak czas_key " +
                    f"dla daty={data_ksiegowania}"
                )
                skipped += 1
                continue

            kwota: Decimal = cast(Decimal, row["kwota"])
            strona = cast(str, row["strona"])
            opis = cast(str | None, row["opis"])

            tgt.execute(
                """
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
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (pozycja_id)
                DO UPDATE SET
                    czas_key = EXCLUDED.czas_key,
                    kontrahent_key = EXCLUDED.kontrahent_key,
                    konto_key = EXCLUDED.konto_key,
                    dokument_key = EXCLUDED.dokument_key,
                    kwota = EXCLUDED.kwota,
                    strona = EXCLUDED.strona,
                    opis = EXCLUDED.opis,
                    datamodyfikacji = CURRENT_TIMESTAMP;
                """,
                (
                    czas_key,
                    kontrahent_key,
                    konto_key,
                    dokument_key,
                    pozycja_id,
                    kwota,
                    strona,
                    opis,
                ),
            )

            inserted += 1

    target_conn.commit()

    print(
        f"fact_operacja: przetworzono {inserted} rekordów."
    )
    print(
        f"Pominięto: {skipped} rekordów."
    )

    return inserted


# ============================================================
# GŁÓWNY ETL
# ============================================================

def main() -> None:
    """Uruchamia proces incremental ETL."""

    print("=" * 60)
    print("START INCREMENTAL ETL")
    print("=" * 60)

    source_conn: psycopg2.extensions.connection | None = None
    target_conn: psycopg2.extensions.connection | None = None

    etl_log_id: int | None = None

    started_at = datetime.now(timezone.utc)

    try:
        print("Łączenie ze źródłową bazą...")
        source_conn = connect_source()
        print("Połączono ze źródłem.")

        print("Łączenie z bazą analityczną...")
        target_conn = connect_target()
        print("Połączono z targetem.")

        etl_log_id = start_etl_log(
            target_conn,
            started_at,
        )

        watermark = get_watermark(target_conn)

        if watermark is None:
            print(
                "Brak watermarku - wykonywane jest " +
                "pierwsze pełne zasilenie."
            )
        else:
            print(
                f"Watermark: {watermark}"
            )

        # # Pobieramy statystyki wymiarów osobno do informacji w konsoli
        # dim_knt_cnt = load_dim_kontrahent(
        #     source_conn,
        #     target_conn,
        #     watermark,
        # )

        # dim_konto_cnt = load_dim_konto(
        #     source_conn,
        #     target_conn,
        #     watermark,
        # )

        # dim_doc_cnt = load_dim_dokument(
        #     source_conn,
        #     target_conn,
        #     watermark,
        # )

        # dim_czas_cnt = load_dim_czas(
        #     source_conn,
        #     target_conn,
        # )

        # Do głównej miary przetwarzania (rows_processed) zliczamy wyłącznie fakty biznesowe
        total_processed = load_fact_operacja(
            source_conn,
            target_conn,
            watermark,
        )

        successful_run = datetime.now(timezone.utc)

        update_watermark(
            target_conn,
            successful_run,
        )

        finish_etl_log(
            target_conn,
            etl_log_id,
            "SUCCESS",
            total_processed,
        )

        print("=" * 60)
        print("INCREMENTAL ETL ZAKOŃCZONY POMYŚLNIE")
        # print(f"Statystyki wymiarów - Kontrahenci: {dim_knt_cnt}, Konta: {dim_konto_cnt}, Dokumenty: {dim_doc_cnt}, Czas: {dim_czas_cnt}")
        # print(f"Przetworzone fakty biznesowe (zapisane do etl_log): {total_processed}")
        print("=" * 60)

    except Exception as exc:
        print("=" * 60)
        print("BŁĄD INCREMENTAL ETL")
        print("=" * 60)
        print(str(exc))

        if target_conn is not None:
            target_conn.rollback()

            if etl_log_id is not None:
                try:
                    finish_etl_log(
                        target_conn,
                        etl_log_id,
                        "FAILED",
                        0,
                        str(exc),
                    )
                except Exception:
                    target_conn.rollback()

        raise

    finally:
        if source_conn is not None:
            source_conn.close()

        if target_conn is not None:
            target_conn.close()


if __name__ == "__main__":
    main()