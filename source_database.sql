--
-- PostgreSQL database dump
--

\restrict HelSmCUAMN0JYijm4bn7dnay8D7Ae5hRXxjC778hDfMznaqmbugH73uz5rm961j

-- Dumped from database version 18.4 (Debian 18.4-1.pgdg13+1)
-- Dumped by pg_dump version 18.4 (Debian 18.4-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: aktualizuj_date_modyfikacji(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.aktualizuj_date_modyfikacji() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.DataModyfikacji = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.aktualizuj_date_modyfikacji() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: dokumentksiegowy; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.dokumentksiegowy (
    dokumentid integer NOT NULL,
    numerdokumentu character varying(50) NOT NULL,
    datawystawienia date NOT NULL,
    dataksiegowania date NOT NULL,
    opis character varying(500),
    kontrahentid integer NOT NULL,
    okresid integer NOT NULL,
    datautworzenia timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    datamodyfikacji timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.dokumentksiegowy OWNER TO postgres;

--
-- Name: dokumentksiegowy_dokumentid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.dokumentksiegowy_dokumentid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.dokumentksiegowy_dokumentid_seq OWNER TO postgres;

--
-- Name: dokumentksiegowy_dokumentid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.dokumentksiegowy_dokumentid_seq OWNED BY public.dokumentksiegowy.dokumentid;


--
-- Name: kontoksiegowe; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.kontoksiegowe (
    kontoid integer NOT NULL,
    numerkonta character varying(20) NOT NULL,
    nazwakonta character varying(200) NOT NULL,
    typkonta character varying(50),
    datautworzenia timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    datamodyfikacji timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.kontoksiegowe OWNER TO postgres;

--
-- Name: kontoksiegowe_kontoid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.kontoksiegowe_kontoid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.kontoksiegowe_kontoid_seq OWNER TO postgres;

--
-- Name: kontoksiegowe_kontoid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.kontoksiegowe_kontoid_seq OWNED BY public.kontoksiegowe.kontoid;


--
-- Name: kontrahent; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.kontrahent (
    kontrahentid integer NOT NULL,
    nazwa character varying(200) NOT NULL,
    nip character varying(20),
    adres character varying(300),
    typkontrahenta character varying(50),
    datautworzenia timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    datamodyfikacji timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.kontrahent OWNER TO postgres;

--
-- Name: kontrahent_kontrahentid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.kontrahent_kontrahentid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.kontrahent_kontrahentid_seq OWNER TO postgres;

--
-- Name: kontrahent_kontrahentid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.kontrahent_kontrahentid_seq OWNED BY public.kontrahent.kontrahentid;


--
-- Name: okresksiegowy; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.okresksiegowy (
    okresid integer NOT NULL,
    rok integer NOT NULL,
    miesiac integer NOT NULL,
    datarozpoczecia date NOT NULL,
    datazakonczenia date NOT NULL,
    datautworzenia timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    datamodyfikacji timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_miesiac CHECK (((miesiac >= 1) AND (miesiac <= 12)))
);


ALTER TABLE public.okresksiegowy OWNER TO postgres;

--
-- Name: okresksiegowy_okresid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.okresksiegowy_okresid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.okresksiegowy_okresid_seq OWNER TO postgres;

--
-- Name: okresksiegowy_okresid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.okresksiegowy_okresid_seq OWNED BY public.okresksiegowy.okresid;


--
-- Name: pozycjadokumentu; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.pozycjadokumentu (
    pozycjaid integer NOT NULL,
    dokumentid integer NOT NULL,
    kontoid integer NOT NULL,
    kwota numeric(12,2) NOT NULL,
    strona character varying(10) NOT NULL,
    opis character varying(300),
    datautworzenia timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    datamodyfikacji timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_strona CHECK (((strona)::text = ANY ((ARRAY['WN'::character varying, 'MA'::character varying])::text[])))
);


ALTER TABLE public.pozycjadokumentu OWNER TO postgres;

--
-- Name: pozycjadokumentu_pozycjaid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.pozycjadokumentu_pozycjaid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pozycjadokumentu_pozycjaid_seq OWNER TO postgres;

--
-- Name: pozycjadokumentu_pozycjaid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.pozycjadokumentu_pozycjaid_seq OWNED BY public.pozycjadokumentu.pozycjaid;


--
-- Name: dokumentksiegowy dokumentid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dokumentksiegowy ALTER COLUMN dokumentid SET DEFAULT nextval('public.dokumentksiegowy_dokumentid_seq'::regclass);


--
-- Name: kontoksiegowe kontoid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kontoksiegowe ALTER COLUMN kontoid SET DEFAULT nextval('public.kontoksiegowe_kontoid_seq'::regclass);


--
-- Name: kontrahent kontrahentid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kontrahent ALTER COLUMN kontrahentid SET DEFAULT nextval('public.kontrahent_kontrahentid_seq'::regclass);


--
-- Name: okresksiegowy okresid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.okresksiegowy ALTER COLUMN okresid SET DEFAULT nextval('public.okresksiegowy_okresid_seq'::regclass);


--
-- Name: pozycjadokumentu pozycjaid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pozycjadokumentu ALTER COLUMN pozycjaid SET DEFAULT nextval('public.pozycjadokumentu_pozycjaid_seq'::regclass);


--
-- Name: dokumentksiegowy dokumentksiegowy_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dokumentksiegowy
    ADD CONSTRAINT dokumentksiegowy_pkey PRIMARY KEY (dokumentid);


--
-- Name: kontoksiegowe kontoksiegowe_numerkonta_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kontoksiegowe
    ADD CONSTRAINT kontoksiegowe_numerkonta_key UNIQUE (numerkonta);


--
-- Name: kontoksiegowe kontoksiegowe_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kontoksiegowe
    ADD CONSTRAINT kontoksiegowe_pkey PRIMARY KEY (kontoid);


--
-- Name: kontrahent kontrahent_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kontrahent
    ADD CONSTRAINT kontrahent_pkey PRIMARY KEY (kontrahentid);


--
-- Name: okresksiegowy okresksiegowy_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.okresksiegowy
    ADD CONSTRAINT okresksiegowy_pkey PRIMARY KEY (okresid);


--
-- Name: pozycjadokumentu pozycjadokumentu_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pozycjadokumentu
    ADD CONSTRAINT pozycjadokumentu_pkey PRIMARY KEY (pozycjaid);


--
-- Name: dokumentksiegowy trg_dokument_modyfikacja; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_dokument_modyfikacja BEFORE UPDATE ON public.dokumentksiegowy FOR EACH ROW EXECUTE FUNCTION public.aktualizuj_date_modyfikacji();


--
-- Name: kontoksiegowe trg_konto_modyfikacja; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_konto_modyfikacja BEFORE UPDATE ON public.kontoksiegowe FOR EACH ROW EXECUTE FUNCTION public.aktualizuj_date_modyfikacji();


--
-- Name: kontrahent trg_kontrahent_modyfikacja; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_kontrahent_modyfikacja BEFORE UPDATE ON public.kontrahent FOR EACH ROW EXECUTE FUNCTION public.aktualizuj_date_modyfikacji();


--
-- Name: okresksiegowy trg_okres_modyfikacja; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_okres_modyfikacja BEFORE UPDATE ON public.okresksiegowy FOR EACH ROW EXECUTE FUNCTION public.aktualizuj_date_modyfikacji();


--
-- Name: pozycjadokumentu trg_pozycja_modyfikacja; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_pozycja_modyfikacja BEFORE UPDATE ON public.pozycjadokumentu FOR EACH ROW EXECUTE FUNCTION public.aktualizuj_date_modyfikacji();


--
-- Name: dokumentksiegowy fk_dokument_kontrahent; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dokumentksiegowy
    ADD CONSTRAINT fk_dokument_kontrahent FOREIGN KEY (kontrahentid) REFERENCES public.kontrahent(kontrahentid);


--
-- Name: dokumentksiegowy fk_dokument_okres; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dokumentksiegowy
    ADD CONSTRAINT fk_dokument_okres FOREIGN KEY (okresid) REFERENCES public.okresksiegowy(okresid);


--
-- Name: pozycjadokumentu fk_pozycja_dokument; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pozycjadokumentu
    ADD CONSTRAINT fk_pozycja_dokument FOREIGN KEY (dokumentid) REFERENCES public.dokumentksiegowy(dokumentid);


--
-- Name: pozycjadokumentu fk_pozycja_konto; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pozycjadokumentu
    ADD CONSTRAINT fk_pozycja_konto FOREIGN KEY (kontoid) REFERENCES public.kontoksiegowe(kontoid);


--
-- PostgreSQL database dump complete
--

\unrestrict HelSmCUAMN0JYijm4bn7dnay8D7Ae5hRXxjC778hDfMznaqmbugH73uz5rm961j

