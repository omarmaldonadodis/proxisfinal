--
-- PostgreSQL database dump
--

\restrict HQ8kUV8GaK0AsBeeXCdebhMq5xSn9jQcwIaY7nPFnT51r3J6MCYbi81Ec9mOJT9

-- Dumped from database version 15.17
-- Dumped by pg_dump version 17.9 (Debian 17.9-0+deb13u1)

-- Started on 2026-04-14 23:33:13 UTC

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
-- TOC entry 866 (class 1247 OID 16386)
-- Name: computerstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.computerstatus AS ENUM (
    'ONLINE',
    'OFFLINE',
    'MAINTENANCE',
    'ERROR'
);


--
-- TOC entry 875 (class 1247 OID 16414)
-- Name: devicetype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.devicetype AS ENUM (
    'DESKTOP',
    'MOBILE',
    'TABLET'
);


--
-- TOC entry 878 (class 1247 OID 16422)
-- Name: profilestatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.profilestatus AS ENUM (
    'CREATING',
    'READY',
    'WARMING',
    'ACTIVE',
    'BUSY',
    'ERROR',
    'DELETED'
);


--
-- TOC entry 872 (class 1247 OID 16404)
-- Name: proxystatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.proxystatus AS ENUM (
    'ACTIVE',
    'INACTIVE',
    'CHECKING',
    'FAILED'
);


--
-- TOC entry 869 (class 1247 OID 16396)
-- Name: proxytype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.proxytype AS ENUM (
    'MOBILE',
    'RESIDENTIAL',
    'DATACENTER'
);


--
-- TOC entry 881 (class 1247 OID 16438)
-- Name: rotationtrigger; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.rotationtrigger AS ENUM (
    'MANUAL',
    'SCHEDULED',
    'HEALTH_FAIL'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 239 (class 1259 OID 16656)
-- Name: agent_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_sessions (
    id integer NOT NULL,
    computer_id integer NOT NULL,
    agent_name character varying(255),
    profile_id integer,
    adspower_profile_id character varying(255),
    target_url text,
    last_url text,
    status character varying(50),
    requested_at timestamp with time zone DEFAULT now(),
    opened_at timestamp with time zone,
    closed_at timestamp with time zone,
    duration_seconds integer,
    pages_visited integer,
    total_data_mb double precision,
    browser_health character varying(50),
    memory_mb double precision,
    denial_reason text,
    error_detail text,
    events json,
    assignment_id integer,
    data_sent_mb double precision,
    data_received_mb double precision,
    last_url_at timestamp with time zone,
    avg_response_time_ms double precision,
    browser_pid integer,
    local_cpu_percent double precision,
    local_ram_mb double precision,
    authorized_by character varying(255)
);


--
-- TOC entry 238 (class 1259 OID 16655)
-- Name: agent_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.agent_sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 3656 (class 0 OID 0)
-- Dependencies: 238
-- Name: agent_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.agent_sessions_id_seq OWNED BY public.agent_sessions.id;


--
-- TOC entry 219 (class 1259 OID 16474)
-- Name: agent_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_tokens (
    id integer NOT NULL,
    agent_name character varying(255) NOT NULL,
    token character varying(64) NOT NULL,
    is_active boolean,
    notes text,
    created_at timestamp with time zone DEFAULT now(),
    last_used_at timestamp with time zone
);


--
-- TOC entry 218 (class 1259 OID 16473)
-- Name: agent_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.agent_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 3657 (class 0 OID 0)
-- Dependencies: 218
-- Name: agent_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.agent_tokens_id_seq OWNED BY public.agent_tokens.id;


--
-- TOC entry 221 (class 1259 OID 16487)
-- Name: alerts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alerts (
    id integer NOT NULL,
    title character varying(255) NOT NULL,
    message text,
    severity character varying(50) NOT NULL,
    status character varying(50) NOT NULL,
    source character varying(100),
    source_id integer,
    acknowledged_by character varying(255),
    acknowledged_at timestamp with time zone,
    silenced_until timestamp with time zone,
    resolved_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- TOC entry 220 (class 1259 OID 16486)
-- Name: alerts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.alerts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 3658 (class 0 OID 0)
-- Dependencies: 220
-- Name: alerts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.alerts_id_seq OWNED BY public.alerts.id;


--
-- TOC entry 243 (class 1259 OID 16710)
-- Name: browser_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.browser_events (
    id integer NOT NULL,
    session_id integer NOT NULL,
    event_type character varying(50) NOT NULL,
    url text,
    details json,
    "timestamp" timestamp with time zone DEFAULT now()
);


--
-- TOC entry 242 (class 1259 OID 16709)
-- Name: browser_events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.browser_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 3659 (class 0 OID 0)
-- Dependencies: 242
-- Name: browser_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.browser_events_id_seq OWNED BY public.browser_events.id;


--
-- TOC entry 223 (class 1259 OID 16501)
-- Name: computer_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.computer_tokens (
    id integer NOT NULL,
    computer_id integer NOT NULL,
    token text NOT NULL,
    is_active boolean,
    created_at timestamp with time zone DEFAULT now(),
    last_used_at timestamp with time zone
);


--
-- TOC entry 222 (class 1259 OID 16500)
-- Name: computer_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.computer_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 3660 (class 0 OID 0)
-- Dependencies: 222
-- Name: computer_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.computer_tokens_id_seq OWNED BY public.computer_tokens.id;


--
-- TOC entry 215 (class 1259 OID 16446)
-- Name: computers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.computers (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    hostname character varying(255),
    ip_address character varying(45),
    adspower_api_url character varying(512) NOT NULL,
    adspower_api_key character varying(512) NOT NULL,
    status public.computerstatus,
    is_active boolean,
    max_profiles integer,
    current_profiles integer,
    cpu_cores integer,
    ram_gb integer,
    os_info character varying(255),
    tags json,
    meta_data json,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone,
    last_seen_at timestamp with time zone
);


--
-- TOC entry 214 (class 1259 OID 16445)
-- Name: computers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.computers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 3661 (class 0 OID 0)
-- Dependencies: 214
-- Name: computers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.computers_id_seq OWNED BY public.computers.id;


--
-- TOC entry 227 (class 1259 OID 16542)
-- Name: health_checks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.health_checks (
    id integer NOT NULL,
    computer_id integer NOT NULL,
    is_healthy boolean,
    response_time_ms double precision,
    adspower_status character varying(20),
    database_status character varying(20),
    redis_status character varying(20),
    cpu_usage double precision,
    memory_usage double precision,
    disk_usage double precision,
    active_profiles integer,
    checks_details json,
    errors json,
    checked_at timestamp with time zone DEFAULT now()
);


--
-- TOC entry 226 (class 1259 OID 16541)
-- Name: health_checks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.health_checks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 3662 (class 0 OID 0)
-- Dependencies: 226
-- Name: health_checks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.health_checks_id_seq OWNED BY public.health_checks.id;


--
-- TOC entry 237 (class 1259 OID 16634)
-- Name: profile_assignments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.profile_assignments (
    id integer NOT NULL,
    profile_id integer NOT NULL,
    agent_id integer NOT NULL,
    target_url character varying(1024),
    assignment_name character varying(255),
    is_active boolean,
    requires_auth boolean,
    notes text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone
);


--
-- TOC entry 236 (class 1259 OID 16633)
-- Name: profile_assignments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.profile_assignments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 3663 (class 0 OID 0)
-- Dependencies: 236
-- Name: profile_assignments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.profile_assignments_id_seq OWNED BY public.profile_assignments.id;


--
-- TOC entry 235 (class 1259 OID 16610)
-- Name: profile_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.profile_metrics (
    id integer NOT NULL,
    profile_id integer NOT NULL,
    proxy_id integer,
    proxy_latency_ms double precision,
    proxy_country character varying(2),
    proxy_city character varying(255),
    proxy_session_id character varying(255),
    creation_duration_seconds double precision,
    creation_success integer,
    device_type character varying(20),
    device_brand character varying(50),
    device_os character varying(50),
    adspower_response_time_ms double precision,
    cookies_count integer,
    created_at timestamp with time zone DEFAULT now()
);


--
-- TOC entry 234 (class 1259 OID 16609)
-- Name: profile_metrics_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.profile_metrics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 3664 (class 0 OID 0)
-- Dependencies: 234
-- Name: profile_metrics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.profile_metrics_id_seq OWNED BY public.profile_metrics.id;


--
-- TOC entry 225 (class 1259 OID 16520)
-- Name: profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.profiles (
    id integer NOT NULL,
    adspower_id character varying(255) NOT NULL,
    proxy_id integer,
    name character varying(255) NOT NULL,
    age integer,
    gender character varying(10),
    country character varying(10),
    city character varying(255),
    timezone character varying(100),
    language character varying(10),
    device_type public.devicetype,
    device_name character varying(255),
    os character varying(50),
    user_agent text,
    screen_resolution character varying(50),
    viewport character varying(50),
    pixel_ratio character varying(10),
    hardware_concurrency integer,
    device_memory integer,
    platform character varying(50),
    owner character varying(255),
    bookie character varying(100),
    sport character varying(50),
    rotation_minutes integer,
    browser_score double precision,
    fingerprint_score double precision,
    cookie_status character varying(20),
    health_score double precision,
    trust_score double precision,
    last_action character varying(50),
    memory_mb double precision,
    warmup_urls json,
    interests json,
    browsing_history json,
    status public.profilestatus,
    is_warmed boolean,
    warmup_completed_at timestamp with time zone,
    last_opened_at timestamp with time zone,
    total_sessions integer,
    total_duration_seconds integer,
    tags json,
    meta_data json,
    notes text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone
);


--
-- TOC entry 224 (class 1259 OID 16519)
-- Name: profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.profiles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 3665 (class 0 OID 0)
-- Dependencies: 224
-- Name: profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.profiles_id_seq OWNED BY public.profiles.id;


--
-- TOC entry 217 (class 1259 OID 16458)
-- Name: proxies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proxies (
    id integer NOT NULL,
    proxy_type public.proxytype NOT NULL,
    host character varying(255) NOT NULL,
    port integer NOT NULL,
    username character varying(512),
    password character varying(512),
    country character varying(2),
    region character varying(255),
    city character varying(255),
    session_id character varying(255),
    session_lifetime integer,
    sticky_session boolean,
    status public.proxystatus,
    is_available boolean,
    last_check_at timestamp with time zone,
    last_success_at timestamp with time zone,
    success_rate double precision,
    avg_response_time double precision,
    total_checks integer,
    failed_checks integer,
    detected_ip character varying(45),
    detected_country character varying(2),
    detected_city character varying(255),
    detected_isp character varying(255),
    profiles_count integer,
    last_used_at timestamp with time zone,
    tags json,
    meta_data json,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone
);


--
-- TOC entry 216 (class 1259 OID 16457)
-- Name: proxies_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.proxies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 3666 (class 0 OID 0)
-- Dependencies: 216
-- Name: proxies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.proxies_id_seq OWNED BY public.proxies.id;


--
-- TOC entry 229 (class 1259 OID 16560)
-- Name: proxy_health_checks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proxy_health_checks (
    id integer NOT NULL,
    proxy_id integer NOT NULL,
    status character varying(20) NOT NULL,
    check_type character varying(50) NOT NULL,
    latency_ms double precision,
    download_speed_mbps double precision,
    upload_speed_mbps double precision,
    detected_ip character varying(45),
    detected_country character varying(2),
    detected_city character varying(255),
    detected_isp character varying(255),
    geo_match boolean,
    is_available boolean,
    response_code integer,
    error_message text,
    session_id character varying(255),
    session_test_result json,
    test_urls json,
    raw_response json,
    checked_at timestamp with time zone DEFAULT now()
);


--
-- TOC entry 228 (class 1259 OID 16559)
-- Name: proxy_health_checks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.proxy_health_checks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 3667 (class 0 OID 0)
-- Dependencies: 228
-- Name: proxy_health_checks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.proxy_health_checks_id_seq OWNED BY public.proxy_health_checks.id;


--
-- TOC entry 241 (class 1259 OID 16682)
-- Name: proxy_rotation_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proxy_rotation_logs (
    id integer NOT NULL,
    proxy_id integer,
    profile_id integer,
    computer_id integer,
    old_proxy_display character varying(255),
    new_proxy_display character varying(255),
    trigger public.rotationtrigger NOT NULL,
    success boolean NOT NULL,
    error_message text,
    latency_ms double precision,
    ip_address character varying(100),
    created_at timestamp with time zone DEFAULT now()
);


--
-- TOC entry 240 (class 1259 OID 16681)
-- Name: proxy_rotation_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.proxy_rotation_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 3668 (class 0 OID 0)
-- Dependencies: 240
-- Name: proxy_rotation_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.proxy_rotation_logs_id_seq OWNED BY public.proxy_rotation_logs.id;


--
-- TOC entry 231 (class 1259 OID 16579)
-- Name: proxy_scores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proxy_scores (
    id integer NOT NULL,
    proxy_id integer NOT NULL,
    overall_score double precision,
    speed_score double precision,
    availability_score double precision,
    geo_accuracy_score double precision,
    stability_score double precision,
    total_checks integer,
    successful_checks integer,
    failed_checks integer,
    timeout_checks integer,
    avg_latency double precision,
    min_latency double precision,
    max_latency double precision,
    uptime_percentage double precision,
    geo_mismatch_count integer,
    is_blacklisted boolean,
    blacklist_reason text,
    blacklisted_at timestamp with time zone,
    consecutive_failures integer,
    last_recovery_attempt timestamp with time zone,
    last_check_at timestamp with time zone,
    score_updated_at timestamp with time zone DEFAULT now()
);


--
-- TOC entry 230 (class 1259 OID 16578)
-- Name: proxy_scores_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.proxy_scores_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 3669 (class 0 OID 0)
-- Dependencies: 230
-- Name: proxy_scores_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.proxy_scores_id_seq OWNED BY public.proxy_scores.id;


--
-- TOC entry 233 (class 1259 OID 16597)
-- Name: proxy_usage_stats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proxy_usage_stats (
    id integer NOT NULL,
    proxy_id integer NOT NULL,
    total_profiles_created integer,
    total_sessions integer,
    avg_latency_ms double precision,
    min_latency_ms double precision,
    max_latency_ms double precision,
    success_rate double precision,
    total_rotations integer,
    last_rotation_at timestamp with time zone,
    estimated_data_usage_gb double precision,
    first_used_at timestamp with time zone,
    last_used_at timestamp with time zone,
    updated_at timestamp with time zone
);


--
-- TOC entry 232 (class 1259 OID 16596)
-- Name: proxy_usage_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.proxy_usage_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 3670 (class 0 OID 0)
-- Dependencies: 232
-- Name: proxy_usage_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.proxy_usage_stats_id_seq OWNED BY public.proxy_usage_stats.id;


--
-- TOC entry 3372 (class 2604 OID 16659)
-- Name: agent_sessions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_sessions ALTER COLUMN id SET DEFAULT nextval('public.agent_sessions_id_seq'::regclass);


--
-- TOC entry 3352 (class 2604 OID 16477)
-- Name: agent_tokens id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_tokens ALTER COLUMN id SET DEFAULT nextval('public.agent_tokens_id_seq'::regclass);


--
-- TOC entry 3354 (class 2604 OID 16490)
-- Name: alerts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts ALTER COLUMN id SET DEFAULT nextval('public.alerts_id_seq'::regclass);


--
-- TOC entry 3376 (class 2604 OID 16713)
-- Name: browser_events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.browser_events ALTER COLUMN id SET DEFAULT nextval('public.browser_events_id_seq'::regclass);


--
-- TOC entry 3357 (class 2604 OID 16504)
-- Name: computer_tokens id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.computer_tokens ALTER COLUMN id SET DEFAULT nextval('public.computer_tokens_id_seq'::regclass);


--
-- TOC entry 3348 (class 2604 OID 16449)
-- Name: computers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.computers ALTER COLUMN id SET DEFAULT nextval('public.computers_id_seq'::regclass);


--
-- TOC entry 3361 (class 2604 OID 16545)
-- Name: health_checks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.health_checks ALTER COLUMN id SET DEFAULT nextval('public.health_checks_id_seq'::regclass);


--
-- TOC entry 3370 (class 2604 OID 16637)
-- Name: profile_assignments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.profile_assignments ALTER COLUMN id SET DEFAULT nextval('public.profile_assignments_id_seq'::regclass);


--
-- TOC entry 3368 (class 2604 OID 16613)
-- Name: profile_metrics id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.profile_metrics ALTER COLUMN id SET DEFAULT nextval('public.profile_metrics_id_seq'::regclass);


--
-- TOC entry 3359 (class 2604 OID 16523)
-- Name: profiles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.profiles ALTER COLUMN id SET DEFAULT nextval('public.profiles_id_seq'::regclass);


--
-- TOC entry 3350 (class 2604 OID 16461)
-- Name: proxies id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxies ALTER COLUMN id SET DEFAULT nextval('public.proxies_id_seq'::regclass);


--
-- TOC entry 3363 (class 2604 OID 16563)
-- Name: proxy_health_checks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxy_health_checks ALTER COLUMN id SET DEFAULT nextval('public.proxy_health_checks_id_seq'::regclass);


--
-- TOC entry 3374 (class 2604 OID 16685)
-- Name: proxy_rotation_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxy_rotation_logs ALTER COLUMN id SET DEFAULT nextval('public.proxy_rotation_logs_id_seq'::regclass);


--
-- TOC entry 3365 (class 2604 OID 16582)
-- Name: proxy_scores id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxy_scores ALTER COLUMN id SET DEFAULT nextval('public.proxy_scores_id_seq'::regclass);


--
-- TOC entry 3367 (class 2604 OID 16600)
-- Name: proxy_usage_stats id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxy_usage_stats ALTER COLUMN id SET DEFAULT nextval('public.proxy_usage_stats_id_seq'::regclass);


--
-- TOC entry 3646 (class 0 OID 16656)
-- Dependencies: 239
-- Data for Name: agent_sessions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_sessions (id, computer_id, agent_name, profile_id, adspower_profile_id, target_url, last_url, status, requested_at, opened_at, closed_at, duration_seconds, pages_visited, total_data_mb, browser_health, memory_mb, denial_reason, error_detail, events, assignment_id, data_sent_mb, data_received_mb, last_url_at, avg_response_time_ms, browser_pid, local_cpu_percent, local_ram_mb, authorized_by) FROM stdin;
1	1	admin-panel	2	k1ay9smc	https://www.betfair.com	\N	crashed	2026-03-30 14:15:28.191473+00	\N	2026-03-30 14:15:28.233413+00	\N	0	0	\N	0	\N	AdsPower no está disponible — abre la aplicación	[]	\N	\N	\N	\N	\N	\N	\N	\N	\N
2	1	admin-panel	1	k1ay9rb9	https://www.google.com	https://www.google.com/	closed	2026-03-30 14:17:25.101122+00	2026-03-30 14:17:55.01973+00	2026-03-30 14:18:06.927366+00	11	1	1.287	crashed	0	\N	\N	[]	\N	\N	\N	\N	\N	\N	\N	\N	\N
3	1	admin-panel	2	k1ay9smc	https://www.google.com	https://www.facebook.com/?locale=es_LA	closed	2026-03-30 14:55:10.176753+00	2026-03-30 14:55:16.519846+00	2026-03-30 14:57:06.290471+00	109	6	7.852	crashed	0	\N	\N	[]	\N	\N	\N	\N	\N	\N	\N	\N	\N
\.


--
-- TOC entry 3626 (class 0 OID 16474)
-- Dependencies: 219
-- Data for Name: agent_tokens; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_tokens (id, agent_name, token, is_active, notes, created_at, last_used_at) FROM stdin;
\.


--
-- TOC entry 3628 (class 0 OID 16487)
-- Dependencies: 221
-- Data for Name: alerts; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.alerts (id, title, message, severity, status, source, source_id, acknowledged_by, acknowledged_at, silenced_until, resolved_at, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 3650 (class 0 OID 16710)
-- Dependencies: 243
-- Data for Name: browser_events; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.browser_events (id, session_id, event_type, url, details, "timestamp") FROM stdin;
1	2	page_visit	https://www.google.com/	{"title": "Google"}	2026-03-30 14:17:55.050786+00
2	3	page_visit	https://www.google.com/	{"title": "google.com"}	2026-03-30 14:55:21.126931+00
3	3	page_visit	https://www.google.com/search?q=facebook&oq=facebook&gs_lcrp=EgZjaHJvbWUyBggAEEUYOTINCAEQABiDARixAxiABDINCAIQABiDARixAxiABDIKCAMQABixAxiABDINCAQQABiDARixAxiABDIKCAUQABixAxiABDINCAYQABiDARixAxiABDIHCAcQABiABNIBCDE2MTBqMGo0qAIAsAIB&sourceid=chrome&ie=UTF-8	{"title": "Google"}	2026-03-30 14:55:27.256181+00
4	3	page_visit	https://www.google.com/sorry/index?continue=https://www.google.com/search%3Fq%3Dfacebook%26oq%3Dfacebook%26gs_lcrp%3DEgZjaHJvbWUyBggAEEUYOTINCAEQABiDARixAxiABDINCAIQABiDARixAxiABDIKCAMQABixAxiABDINCAQQABiDARixAxiABDIKCAUQABixAxiABDINCAYQABiDARixAxiABDIHCAcQABiABNIBCDE2MTBqMGo0qAIAsAIB%26sourceid%3Dchrome%26ie%3DUTF-8%26sei%3D347KaeHoELaCwbkPoLSWsA4&q=EgQt5DRqGOCdqs4GIjBysys6fpvPtU0yiB0A6MBH72EtOpwZK2t1M4qkVV3SWsbAWh0wZNbKn7Q5mAESu9QyAVJaAUM	{"title": "https://www.google.com/search?q=facebook&amp;oq=facebook&amp;gs_lcrp=EgZjaHJvbWUyBggAEEUYOTINCAEQABiDARixAxiABDINCAIQABiDARixAxiABDIKCAMQABixAxiABDINCAQQABiDARixAxiABDIKCAUQABixAxiABDINCAYQABiDARixAxiABDIHCAcQABiABNIBCDE2MTBqMGo0qAIAsAIB&amp;sourceid=chrome&amp;ie=UTF-8&amp;sei=347KaeHoELaCwbkPoLSWsA4"}	2026-03-30 14:55:29.30415+00
5	3	page_visit	https://www.google.com/search?q=facebook&oq=facebook&gs_lcrp=EgZjaHJvbWUyBggAEEUYOTINCAEQABiDARixAxiABDINCAIQABiDARixAxiABDIKCAMQABixAxiABDINCAQQABiDARixAxiABDIKCAUQABixAxiABDINCAYQABiDARixAxiABDIHCAcQABiABNIBCDE2MTBqMGo0qAIAsAIB&sourceid=chrome&ie=UTF-8&sei=347KaeHoELaCwbkPoLSWsA4&google_abuse=GOOGLE_ABUSE_EXEMPTION%3DID%3D6d6155bfbd50baec:TM%3D1774882528:C%3DR:IP%3D45.228.52.106-:S%3DBk9jbBV_ITszW82IhqXT7tA%3B+path%3D/%3B+domain%3Dgoogle.com%3B+expires%3DMon,+30-Mar-2026+17:55:28+GMT	{"title": "Google Search"}	2026-03-30 14:56:50.783038+00
6	3	page_visit	https://www.google.com/search?q=facebook&oq=facebook&gs_lcrp=EgZjaHJvbWUyBggAEEUYOTINCAEQABiDARixAxiABDINCAIQABiDARixAxiABDIKCAMQABixAxiABDINCAQQABiDARixAxiABDIKCAUQABixAxiABDINCAYQABiDARixAxiABDIHCAcQABiABNIBCDE2MTBqMGo0qAIAsAIB&sourceid=chrome&ie=UTF-8&sei=MI_KaZvjPO6ywt0P0qPl-Q8	{"title": "facebook - Buscar con Google"}	2026-03-30 14:56:56.887634+00
7	3	page_visit	https://www.facebook.com/?locale=es_LA	{"title": "Facebook"}	2026-03-30 14:57:01.195796+00
\.


--
-- TOC entry 3630 (class 0 OID 16501)
-- Dependencies: 223
-- Data for Name: computer_tokens; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.computer_tokens (id, computer_id, token, is_active, created_at, last_used_at) FROM stdin;
\.


--
-- TOC entry 3622 (class 0 OID 16446)
-- Dependencies: 215
-- Data for Name: computers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.computers (id, name, hostname, ip_address, adspower_api_url, adspower_api_key, status, is_active, max_profiles, current_profiles, cpu_cores, ram_gb, os_info, tags, meta_data, created_at, updated_at, last_seen_at) FROM stdin;
1	MacBook-Pro-de-Omar.local	MacBook-Pro-de-Omar.local	192.168.18.177	http://local.adspower.net:50325		OFFLINE	t	50	0	12	16	Darwin 24.6.0	[]	\N	2026-03-30 14:09:09.382322+00	2026-03-30 18:26:07.805767+00	2026-03-30 14:59:09.884063+00
\.


--
-- TOC entry 3634 (class 0 OID 16542)
-- Dependencies: 227
-- Data for Name: health_checks; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.health_checks (id, computer_id, is_healthy, response_time_ms, adspower_status, database_status, redis_status, cpu_usage, memory_usage, disk_usage, active_profiles, checks_details, errors, checked_at) FROM stdin;
1	1	t	\N	offline	\N	\N	11.7	65.3	39.1	0	{"computer_id": 1, "adspower_running": false, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 0.0, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 8.24, "download_speed_kbps": 8.29, "session_sent_mb": 0.084, "session_received_mb": 0.084, "session_total_mb": 0.168}, "system": {"cpu_percent": 11.7, "ram_percent": 65.3, "ram_used_mb": 8636.1, "ram_total_mb": 16384.0, "disk_percent": 39.1}}	[]	2026-03-30 14:09:19.81785+00
2	1	t	\N	offline	\N	\N	89.9	66.8	39.1	0	{"computer_id": 1, "adspower_running": false, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 0.0, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 3.88, "download_speed_kbps": 4.49, "session_sent_mb": 0.123, "session_received_mb": 0.129, "session_total_mb": 0.252}, "system": {"cpu_percent": 89.9, "ram_percent": 66.8, "ram_used_mb": 8761.4, "ram_total_mb": 16384.0, "disk_percent": 39.1}}	[]	2026-03-30 14:09:30.053276+00
3	1	t	\N	offline	\N	\N	21.8	68.4	39.1	0	{"computer_id": 1, "adspower_running": false, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 0.0, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 433.25, "download_speed_kbps": 473.32, "session_sent_mb": 4.44, "session_received_mb": 4.845, "session_total_mb": 9.285}, "system": {"cpu_percent": 21.8, "ram_percent": 68.4, "ram_used_mb": 8651.2, "ram_total_mb": 16384.0, "disk_percent": 39.1}}	[]	2026-03-30 14:09:40.255693+00
4	1	t	\N	offline	\N	\N	18.6	69.4	39.1	0	{"computer_id": 1, "adspower_running": false, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 0.0, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 5.1, "download_speed_kbps": 6.56, "session_sent_mb": 4.491, "session_received_mb": 4.911, "session_total_mb": 9.401}, "system": {"cpu_percent": 18.6, "ram_percent": 69.4, "ram_used_mb": 8730.7, "ram_total_mb": 16384.0, "disk_percent": 39.1}}	[]	2026-03-30 14:09:50.491125+00
5	1	t	\N	offline	\N	\N	16.8	69.7	39.1	0	{"computer_id": 1, "adspower_running": false, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 0.0, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 6.49, "download_speed_kbps": 7.87, "session_sent_mb": 4.555, "session_received_mb": 4.989, "session_total_mb": 9.544}, "system": {"cpu_percent": 16.8, "ram_percent": 69.7, "ram_used_mb": 8743.8, "ram_total_mb": 16384.0, "disk_percent": 39.1}}	[]	2026-03-30 14:10:00.692433+00
6	1	t	\N	offline	\N	\N	11.7	69.4	39.1	0	{"computer_id": 1, "adspower_running": false, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 0.0, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.74, "download_speed_kbps": 2.84, "session_sent_mb": 4.583, "session_received_mb": 5.018, "session_total_mb": 9.6}, "system": {"cpu_percent": 11.7, "ram_percent": 69.4, "ram_used_mb": 8704.1, "ram_total_mb": 16384.0, "disk_percent": 39.1}}	[]	2026-03-30 14:10:10.945098+00
7	1	t	\N	offline	\N	\N	8.7	69.2	39.1	0	{"computer_id": 1, "adspower_running": false, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 0.0, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 7.29, "download_speed_kbps": 7.62, "session_sent_mb": 4.656, "session_received_mb": 5.094, "session_total_mb": 9.749}, "system": {"cpu_percent": 8.7, "ram_percent": 69.2, "ram_used_mb": 8666.6, "ram_total_mb": 16384.0, "disk_percent": 39.1}}	[]	2026-03-30 14:10:21.182104+00
8	1	t	\N	offline	\N	\N	6.7	68.2	39.1	0	{"computer_id": 1, "adspower_running": false, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 0.0, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 6.3, "download_speed_kbps": 7.6, "session_sent_mb": 4.718, "session_received_mb": 5.17, "session_total_mb": 9.888}, "system": {"cpu_percent": 6.7, "ram_percent": 68.2, "ram_used_mb": 8712.8, "ram_total_mb": 16384.0, "disk_percent": 39.1}}	[]	2026-03-30 14:10:31.366491+00
9	1	t	\N	offline	\N	\N	8.1	68.2	39.1	0	{"computer_id": 1, "adspower_running": false, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 0.0, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 23.5, "download_speed_kbps": 19.39, "session_sent_mb": 4.952, "session_received_mb": 5.362, "session_total_mb": 10.314}, "system": {"cpu_percent": 8.1, "ram_percent": 68.2, "ram_used_mb": 8872.7, "ram_total_mb": 16384.0, "disk_percent": 39.1}}	[]	2026-03-30 14:10:41.545997+00
10	1	t	\N	offline	\N	\N	9.4	64.8	39.1	0	{"computer_id": 1, "adspower_running": false, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 0.0, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 212.3, "download_speed_kbps": 180.74, "session_sent_mb": 7.064, "session_received_mb": 7.16, "session_total_mb": 14.224}, "system": {"cpu_percent": 9.4, "ram_percent": 64.8, "ram_used_mb": 8656.1, "ram_total_mb": 16384.0, "disk_percent": 39.1}}	[]	2026-03-30 14:10:51.737045+00
11	1	t	\N	offline	\N	\N	8.1	64.8	39.1	0	{"computer_id": 1, "adspower_running": false, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 0.0, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 93.46, "download_speed_kbps": 73.53, "session_sent_mb": 7.993, "session_received_mb": 7.892, "session_total_mb": 15.885}, "system": {"cpu_percent": 8.1, "ram_percent": 64.8, "ram_used_mb": 8689.8, "ram_total_mb": 16384.0, "disk_percent": 39.1}}	[]	2026-03-30 14:11:01.917795+00
12	1	t	\N	offline	\N	\N	16.9	68.7	39.2	0	{"computer_id": 1, "adspower_running": false, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 0.0, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 118.45, "download_speed_kbps": 104.5, "session_sent_mb": 9.174, "session_received_mb": 8.933, "session_total_mb": 18.107}, "system": {"cpu_percent": 16.9, "ram_percent": 68.7, "ram_used_mb": 9224.0, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:11:12.125389+00
13	1	t	\N	offline	\N	\N	13.3	66.4	39.1	0	{"computer_id": 1, "adspower_running": false, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 0.0, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 6.63, "download_speed_kbps": 3.09, "session_sent_mb": 9.24, "session_received_mb": 8.964, "session_total_mb": 18.204}, "system": {"cpu_percent": 13.3, "ram_percent": 66.4, "ram_used_mb": 9029.3, "ram_total_mb": 16384.0, "disk_percent": 39.1}}	[]	2026-03-30 14:11:22.332945+00
14	1	t	\N	offline	\N	\N	12.6	64.9	39.1	0	{"computer_id": 1, "adspower_running": false, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 0.0, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 5.73, "download_speed_kbps": 5.76, "session_sent_mb": 9.297, "session_received_mb": 9.021, "session_total_mb": 18.318}, "system": {"cpu_percent": 12.6, "ram_percent": 64.9, "ram_used_mb": 8782.4, "ram_total_mb": 16384.0, "disk_percent": 39.1}}	[]	2026-03-30 14:11:32.524212+00
15	1	t	\N	offline	\N	\N	6.4	66.4	39.1	0	{"computer_id": 1, "adspower_running": false, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 0.0, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 0.9, "download_speed_kbps": 0.83, "session_sent_mb": 9.306, "session_received_mb": 9.029, "session_total_mb": 18.335}, "system": {"cpu_percent": 6.4, "ram_percent": 66.4, "ram_used_mb": 9024.7, "ram_total_mb": 16384.0, "disk_percent": 39.1}}	[]	2026-03-30 14:11:42.708619+00
16	1	t	\N	offline	\N	\N	53.6	66.7	39.1	0	{"computer_id": 1, "adspower_running": false, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 0.0, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 55.07, "download_speed_kbps": 50.07, "session_sent_mb": 9.857, "session_received_mb": 9.531, "session_total_mb": 19.388}, "system": {"cpu_percent": 53.6, "ram_percent": 66.7, "ram_used_mb": 9085.3, "ram_total_mb": 16384.0, "disk_percent": 39.1}}	[]	2026-03-30 14:11:52.95313+00
17	1	t	\N	offline	\N	\N	10.2	66.6	39.1	0	{"computer_id": 1, "adspower_running": false, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 0.0, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 3.22, "download_speed_kbps": 0.97, "session_sent_mb": 9.889, "session_received_mb": 9.54, "session_total_mb": 19.43}, "system": {"cpu_percent": 10.2, "ram_percent": 66.6, "ram_used_mb": 9061.8, "ram_total_mb": 16384.0, "disk_percent": 39.1}}	[]	2026-03-30 14:12:03.133446+00
26	1	t	\N	online	\N	\N	24	66.7	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 15.6, "adspower_ram_mb": 958.44, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 16.05, "download_speed_kbps": 22.01, "session_sent_mb": 10.95, "session_received_mb": 14.669, "session_total_mb": 25.619}, "system": {"cpu_percent": 24.0, "ram_percent": 66.7, "ram_used_mb": 8863.7, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:13:36.440518+00
29	1	t	\N	online	\N	\N	22.2	67.2	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 25.8, "adspower_ram_mb": 899.73, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 39.07, "download_speed_kbps": 42.65, "session_sent_mb": 11.462, "session_received_mb": 15.37, "session_total_mb": 26.832}, "system": {"cpu_percent": 22.2, "ram_percent": 67.2, "ram_used_mb": 8912.0, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:14:07.823432+00
31	1	t	\N	online	\N	\N	25.4	67.3	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 18.0, "adspower_ram_mb": 912.75, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 6.29, "download_speed_kbps": 7.01, "session_sent_mb": 11.567, "session_received_mb": 15.469, "session_total_mb": 27.036}, "system": {"cpu_percent": 25.4, "ram_percent": 67.3, "ram_used_mb": 8911.9, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:14:28.570697+00
34	1	t	\N	online	\N	\N	40.5	66.9	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 12.1, "adspower_ram_mb": 859.5, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.36, "download_speed_kbps": 2.68, "session_sent_mb": 11.676, "session_received_mb": 15.581, "session_total_mb": 27.257}, "system": {"cpu_percent": 40.5, "ram_percent": 66.9, "ram_used_mb": 8806.7, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:14:59.356734+00
35	1	t	\N	online	\N	\N	45.5	67.5	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 10.4, "adspower_ram_mb": 852.15, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 38.98, "download_speed_kbps": 38.32, "session_sent_mb": 12.066, "session_received_mb": 15.965, "session_total_mb": 28.031}, "system": {"cpu_percent": 45.5, "ram_percent": 67.5, "ram_used_mb": 8903.8, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:15:09.66759+00
36	1	t	\N	online	\N	\N	12	64.9	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 97.12, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 9.89, "download_speed_kbps": 11.32, "session_sent_mb": 12.165, "session_received_mb": 16.078, "session_total_mb": 28.243}, "system": {"cpu_percent": 12.0, "ram_percent": 64.9, "ram_used_mb": 8485.2, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:15:19.852677+00
38	1	t	\N	online	\N	\N	8.4	65.5	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 97.13, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 22.9, "download_speed_kbps": 23.08, "session_sent_mb": 12.61, "session_received_mb": 16.526, "session_total_mb": 29.136}, "system": {"cpu_percent": 8.4, "ram_percent": 65.5, "ram_used_mb": 8576.3, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:15:40.349465+00
43	1	t	\N	online	\N	\N	32.5	68.9	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 13.6, "adspower_ram_mb": 840.61, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 21.97, "download_speed_kbps": 50.45, "session_sent_mb": 13.219, "session_received_mb": 17.42, "session_total_mb": 30.639}, "system": {"cpu_percent": 32.5, "ram_percent": 68.9, "ram_used_mb": 9027.1, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:16:31.516294+00
44	1	t	\N	online	\N	\N	23.2	69	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 38.2, "adspower_ram_mb": 1016.67, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 20.79, "download_speed_kbps": 22.1, "session_sent_mb": 13.428, "session_received_mb": 17.642, "session_total_mb": 31.07}, "system": {"cpu_percent": 23.2, "ram_percent": 69.0, "ram_used_mb": 8992.7, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:16:41.798273+00
47	1	t	\N	online	\N	\N	16	67.6	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 25.8, "adspower_ram_mb": 988.43, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 62.56, "download_speed_kbps": 63.42, "session_sent_mb": 14.183, "session_received_mb": 18.45, "session_total_mb": 32.634}, "system": {"cpu_percent": 16.0, "ram_percent": 67.6, "ram_used_mb": 8698.1, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:17:13.067813+00
18	1	t	\N	online	\N	\N	77.9	66	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 595.43, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 23.36, "download_speed_kbps": 370.35, "session_sent_mb": 10.125, "session_received_mb": 13.28, "session_total_mb": 23.406}, "system": {"cpu_percent": 77.9, "ram_percent": 66.0, "ram_used_mb": 9112.3, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:12:13.474836+00
20	1	t	\N	online	\N	\N	14.5	66.3	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 16.8, "adspower_ram_mb": 978.1, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 21.14, "download_speed_kbps": 20.38, "session_sent_mb": 10.456, "session_received_mb": 13.879, "session_total_mb": 24.335}, "system": {"cpu_percent": 14.5, "ram_percent": 66.3, "ram_used_mb": 8892.6, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:12:34.08261+00
25	1	t	\N	online	\N	\N	21	66.9	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 19.5, "adspower_ram_mb": 951.57, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.95, "download_speed_kbps": 2.28, "session_sent_mb": 10.787, "session_received_mb": 14.445, "session_total_mb": 25.232}, "system": {"cpu_percent": 21.0, "ram_percent": 66.9, "ram_used_mb": 8936.3, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:13:26.034539+00
30	1	t	\N	online	\N	\N	18.4	67.4	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 22.9, "adspower_ram_mb": 899.85, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 3.99, "download_speed_kbps": 2.82, "session_sent_mb": 11.503, "session_received_mb": 15.398, "session_total_mb": 26.901}, "system": {"cpu_percent": 18.4, "ram_percent": 67.4, "ram_used_mb": 8923.8, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:14:18.217216+00
49	1	t	\N	online	\N	\N	32.8	68.1	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 33.1, "adspower_ram_mb": 1026.65, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 41.68, "download_speed_kbps": 62.67, "session_sent_mb": 14.62, "session_received_mb": 19.103, "session_total_mb": 33.723}, "system": {"cpu_percent": 32.8, "ram_percent": 68.1, "ram_used_mb": 8761.3, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:17:33.881611+00
19	1	t	\N	online	\N	\N	11.3	66.3	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 60.6, "adspower_ram_mb": 977.08, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 11.72, "download_speed_kbps": 39.07, "session_sent_mb": 10.243, "session_received_mb": 13.674, "session_total_mb": 23.917}, "system": {"cpu_percent": 11.3, "ram_percent": 66.3, "ram_used_mb": 8897.7, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:12:23.792491+00
24	1	t	\N	online	\N	\N	21.4	66.6	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 19.7, "adspower_ram_mb": 950.21, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 18.21, "download_speed_kbps": 33.41, "session_sent_mb": 10.768, "session_received_mb": 14.422, "session_total_mb": 25.189}, "system": {"cpu_percent": 21.4, "ram_percent": 66.6, "ram_used_mb": 8887.2, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:13:15.647865+00
37	1	t	\N	online	\N	\N	10.7	66	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 97.12, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 21.51, "download_speed_kbps": 21.66, "session_sent_mb": 12.38, "session_received_mb": 16.295, "session_total_mb": 28.676}, "system": {"cpu_percent": 10.7, "ram_percent": 66.0, "ram_used_mb": 8652.3, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:15:30.10689+00
45	1	t	\N	online	\N	\N	15.9	68.8	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 14.1, "adspower_ram_mb": 1020.16, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 7.1, "download_speed_kbps": 7.21, "session_sent_mb": 13.5, "session_received_mb": 17.714, "session_total_mb": 31.214}, "system": {"cpu_percent": 15.9, "ram_percent": 68.8, "ram_used_mb": 8953.5, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:16:52.150213+00
48	1	t	\N	online	\N	\N	22	67.7	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 25.0, "adspower_ram_mb": 992.18, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.19, "download_speed_kbps": 1.38, "session_sent_mb": 14.195, "session_received_mb": 18.464, "session_total_mb": 32.66}, "system": {"cpu_percent": 22.0, "ram_percent": 67.7, "ram_used_mb": 8707.2, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:17:23.449+00
51	1	t	\N	online	\N	\N	85	69.6	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 17.9, "adspower_ram_mb": 786.68, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 16.13, "download_speed_kbps": 23.96, "session_sent_mb": 14.801, "session_received_mb": 19.364, "session_total_mb": 34.165}, "system": {"cpu_percent": 85.0, "ram_percent": 69.6, "ram_used_mb": 8691.4, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:17:54.92738+00
21	1	t	\N	online	\N	\N	67.5	68.2	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 23.0, "adspower_ram_mb": 946.72, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 3.54, "download_speed_kbps": 3.74, "session_sent_mb": 10.492, "session_received_mb": 13.917, "session_total_mb": 24.408}, "system": {"cpu_percent": 67.5, "ram_percent": 68.2, "ram_used_mb": 9207.7, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:12:44.394346+00
28	1	t	\N	online	\N	\N	17.7	67	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 20.0, "adspower_ram_mb": 958.66, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 3.33, "download_speed_kbps": 17.94, "session_sent_mb": 11.062, "session_received_mb": 14.933, "session_total_mb": 25.995}, "system": {"cpu_percent": 17.7, "ram_percent": 67.0, "ram_used_mb": 8885.4, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:13:57.332004+00
32	1	t	\N	online	\N	\N	14.2	67.1	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 13.0, "adspower_ram_mb": 907.93, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.28, "download_speed_kbps": 0.94, "session_sent_mb": 11.579, "session_received_mb": 15.479, "session_total_mb": 27.058}, "system": {"cpu_percent": 14.2, "ram_percent": 67.1, "ram_used_mb": 8866.7, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:14:38.840592+00
40	1	t	\N	online	\N	\N	12.8	65.4	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 96.35, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 0.9, "download_speed_kbps": 0.77, "session_sent_mb": 12.69, "session_received_mb": 16.605, "session_total_mb": 29.296}, "system": {"cpu_percent": 12.8, "ram_percent": 65.4, "ram_used_mb": 8560.8, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:16:00.797868+00
41	1	t	\N	online	\N	\N	20.3	66.1	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 96.39, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 29.73, "download_speed_kbps": 29.66, "session_sent_mb": 12.987, "session_received_mb": 16.902, "session_total_mb": 29.889}, "system": {"cpu_percent": 20.3, "ram_percent": 66.1, "ram_used_mb": 8669.0, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:16:11.024569+00
52	1	t	\N	online	\N	\N	77.5	68.8	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 22.7, "adspower_ram_mb": 758.85, "active_browsers_count": 0, "active_sessions": [2], "network": {"upload_speed_kbps": 29.1, "download_speed_kbps": 89.51, "session_sent_mb": 0.291, "session_received_mb": 0.916, "session_total_mb": 1.207}, "system": {"cpu_percent": 77.5, "ram_percent": 68.8, "ram_used_mb": 8461.7, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:18:05.467245+00
22	1	t	\N	online	\N	\N	16.5	67.6	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 19.2, "adspower_ram_mb": 948.37, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 7.19, "download_speed_kbps": 14.32, "session_sent_mb": 10.565, "session_received_mb": 14.063, "session_total_mb": 24.628}, "system": {"cpu_percent": 16.5, "ram_percent": 67.6, "ram_used_mb": 9068.5, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:12:54.874811+00
23	1	t	\N	online	\N	\N	19.8	66.6	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 15.8, "adspower_ram_mb": 953.01, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.76, "download_speed_kbps": 1.97, "session_sent_mb": 10.583, "session_received_mb": 14.083, "session_total_mb": 24.666}, "system": {"cpu_percent": 19.8, "ram_percent": 66.6, "ram_used_mb": 8896.1, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:13:05.271276+00
42	1	t	\N	online	\N	\N	16.7	66.2	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 158.26, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.14, "download_speed_kbps": 1.17, "session_sent_mb": 12.999, "session_received_mb": 16.913, "session_total_mb": 29.912}, "system": {"cpu_percent": 16.7, "ram_percent": 66.2, "ram_used_mb": 8700.4, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:16:21.231102+00
50	1	t	\N	online	\N	\N	27.5	68.7	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 19.6, "adspower_ram_mb": 1026.88, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.28, "download_speed_kbps": 1.18, "session_sent_mb": 14.633, "session_received_mb": 19.115, "session_total_mb": 33.748}, "system": {"cpu_percent": 27.5, "ram_percent": 68.7, "ram_used_mb": 8825.3, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:17:44.246447+00
53	1	t	\N	online	\N	\N	16.7	69.4	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 21.3, "adspower_ram_mb": 760.63, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 21.41, "download_speed_kbps": 21.79, "session_sent_mb": 0.523, "session_received_mb": 1.153, "session_total_mb": 1.676}, "system": {"cpu_percent": 16.7, "ram_percent": 69.4, "ram_used_mb": 8568.2, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:18:16.252079+00
27	1	t	\N	online	\N	\N	18.2	66.8	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 15.8, "adspower_ram_mb": 959.84, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 7.66, "download_speed_kbps": 7.96, "session_sent_mb": 11.028, "session_received_mb": 14.75, "session_total_mb": 25.778}, "system": {"cpu_percent": 18.2, "ram_percent": 66.8, "ram_used_mb": 8893.0, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:13:46.883874+00
46	1	t	\N	online	\N	\N	14.6	69.8	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 57.8, "adspower_ram_mb": 982.58, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 4.0, "download_speed_kbps": 8.28, "session_sent_mb": 13.54, "session_received_mb": 17.798, "session_total_mb": 31.339}, "system": {"cpu_percent": 14.6, "ram_percent": 69.8, "ram_used_mb": 9053.0, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:17:02.54117+00
33	1	t	\N	online	\N	\N	17.5	67.1	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 10.7, "adspower_ram_mb": 889.2, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 7.25, "download_speed_kbps": 7.59, "session_sent_mb": 11.652, "session_received_mb": 15.554, "session_total_mb": 27.206}, "system": {"cpu_percent": 17.5, "ram_percent": 67.1, "ram_used_mb": 8860.7, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:14:49.083768+00
39	1	t	\N	online	\N	\N	20.2	65.1	39.2	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.6, "adspower_ram_mb": 96.32, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 7.21, "download_speed_kbps": 7.16, "session_sent_mb": 12.682, "session_received_mb": 16.598, "session_total_mb": 29.279}, "system": {"cpu_percent": 20.2, "ram_percent": 65.1, "ram_used_mb": 8507.8, "ram_total_mb": 16384.0, "disk_percent": 39.2}}	[]	2026-03-30 14:15:50.574057+00
54	1	t	\N	online	\N	\N	35	69.4	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 15.7, "adspower_ram_mb": 763.58, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.79, "download_speed_kbps": 2.15, "session_sent_mb": 0.551, "session_received_mb": 1.175, "session_total_mb": 1.726}, "system": {"cpu_percent": 35.0, "ram_percent": 69.4, "ram_used_mb": 8573.8, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:18:26.550391+00
55	1	t	\N	online	\N	\N	12.9	69	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 13.7, "adspower_ram_mb": 764.38, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 6.02, "download_speed_kbps": 6.46, "session_sent_mb": 0.611, "session_received_mb": 1.24, "session_total_mb": 1.851}, "system": {"cpu_percent": 12.9, "ram_percent": 69.0, "ram_used_mb": 8505.0, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:18:36.793923+00
56	1	t	\N	online	\N	\N	9.3	68.7	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 12.9, "adspower_ram_mb": 762.77, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 4.5, "download_speed_kbps": 3.96, "session_sent_mb": 0.656, "session_received_mb": 1.279, "session_total_mb": 1.935}, "system": {"cpu_percent": 9.3, "ram_percent": 68.7, "ram_used_mb": 8449.9, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:18:46.993015+00
57	1	t	\N	online	\N	\N	19.4	68	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 10.3, "adspower_ram_mb": 762.88, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 4.55, "download_speed_kbps": 4.81, "session_sent_mb": 0.701, "session_received_mb": 1.327, "session_total_mb": 2.028}, "system": {"cpu_percent": 19.4, "ram_percent": 68.0, "ram_used_mb": 8340.4, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:18:57.219694+00
58	1	t	\N	online	\N	\N	13.8	68	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 10.3, "adspower_ram_mb": 762.99, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 5.79, "download_speed_kbps": 7.68, "session_sent_mb": 0.759, "session_received_mb": 1.404, "session_total_mb": 2.163}, "system": {"cpu_percent": 13.8, "ram_percent": 68.0, "ram_used_mb": 8346.6, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:19:07.418494+00
59	1	t	\N	online	\N	\N	11.4	67.9	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 9.9, "adspower_ram_mb": 764.71, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 3.56, "download_speed_kbps": 3.5, "session_sent_mb": 0.794, "session_received_mb": 1.439, "session_total_mb": 2.233}, "system": {"cpu_percent": 11.4, "ram_percent": 67.9, "ram_used_mb": 8331.3, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:19:17.617793+00
60	1	t	\N	online	\N	\N	12.2	67.9	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 12.0, "adspower_ram_mb": 766.88, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 4.2, "download_speed_kbps": 4.11, "session_sent_mb": 0.836, "session_received_mb": 1.48, "session_total_mb": 2.316}, "system": {"cpu_percent": 12.2, "ram_percent": 67.9, "ram_used_mb": 8330.8, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:19:27.809973+00
61	1	t	\N	online	\N	\N	9.8	68.1	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 12.3, "adspower_ram_mb": 781.14, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 3.89, "download_speed_kbps": 4.21, "session_sent_mb": 0.875, "session_received_mb": 1.521, "session_total_mb": 2.397}, "system": {"cpu_percent": 9.8, "ram_percent": 68.1, "ram_used_mb": 8353.8, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:19:38.000583+00
62	1	t	\N	online	\N	\N	19.4	68.3	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 10.8, "adspower_ram_mb": 793.42, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 4.61, "download_speed_kbps": 4.64, "session_sent_mb": 0.921, "session_received_mb": 1.568, "session_total_mb": 2.489}, "system": {"cpu_percent": 19.4, "ram_percent": 68.3, "ram_used_mb": 8403.3, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:19:48.197072+00
63	1	t	\N	online	\N	\N	13.6	68.1	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 10.2, "adspower_ram_mb": 793.5, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 4.55, "download_speed_kbps": 4.75, "session_sent_mb": 0.966, "session_received_mb": 1.615, "session_total_mb": 2.581}, "system": {"cpu_percent": 13.6, "ram_percent": 68.1, "ram_used_mb": 8380.7, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:19:58.393399+00
64	1	t	\N	online	\N	\N	9.7	68.1	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 11.8, "adspower_ram_mb": 791.6, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 4.29, "download_speed_kbps": 4.82, "session_sent_mb": 1.009, "session_received_mb": 1.663, "session_total_mb": 2.672}, "system": {"cpu_percent": 9.7, "ram_percent": 68.1, "ram_used_mb": 8385.9, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:20:08.591784+00
65	1	t	\N	online	\N	\N	12	68.2	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 11.9, "adspower_ram_mb": 792.14, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 4.67, "download_speed_kbps": 4.82, "session_sent_mb": 1.055, "session_received_mb": 1.711, "session_total_mb": 2.767}, "system": {"cpu_percent": 12.0, "ram_percent": 68.2, "ram_used_mb": 8395.3, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:20:18.78422+00
66	1	t	\N	online	\N	\N	11.9	67.9	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 11.6, "adspower_ram_mb": 792.25, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 3.93, "download_speed_kbps": 3.96, "session_sent_mb": 1.095, "session_received_mb": 1.751, "session_total_mb": 2.845}, "system": {"cpu_percent": 11.9, "ram_percent": 67.9, "ram_used_mb": 8363.4, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:20:28.977124+00
67	1	t	\N	online	\N	\N	12.5	67.8	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 10.4, "adspower_ram_mb": 791.87, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 3.68, "download_speed_kbps": 3.59, "session_sent_mb": 1.131, "session_received_mb": 1.786, "session_total_mb": 2.917}, "system": {"cpu_percent": 12.5, "ram_percent": 67.8, "ram_used_mb": 8345.1, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:20:39.167013+00
77	1	t	\N	online	\N	\N	32.3	59.7	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 757.55, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 11.96, "download_speed_kbps": 16.46, "session_sent_mb": 2.12, "session_received_mb": 3.592, "session_total_mb": 5.712}, "system": {"cpu_percent": 32.3, "ram_percent": 59.7, "ram_used_mb": 6670.7, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:22:21.018768+00
90	1	t	\N	online	\N	\N	4.1	60.2	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.4, "adspower_ram_mb": 695.99, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.12, "download_speed_kbps": 2.05, "session_sent_mb": 2.647, "session_received_mb": 4.778, "session_total_mb": 7.425}, "system": {"cpu_percent": 4.1, "ram_percent": 60.2, "ram_used_mb": 6695.8, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:24:33.424087+00
94	1	t	\N	online	\N	\N	7.4	60.2	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 696.9, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.11, "download_speed_kbps": 2.32, "session_sent_mb": 2.714, "session_received_mb": 4.842, "session_total_mb": 7.556}, "system": {"cpu_percent": 7.4, "ram_percent": 60.2, "ram_used_mb": 6698.3, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:25:14.155788+00
111	1	t	\N	online	\N	\N	6.7	61.3	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 709.89, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 3.08, "download_speed_kbps": 11.33, "session_sent_mb": 3.138, "session_received_mb": 5.471, "session_total_mb": 8.608}, "system": {"cpu_percent": 6.7, "ram_percent": 61.3, "ram_used_mb": 6876.1, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:28:07.271479+00
68	1	t	\N	online	\N	\N	12.9	67.2	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 11.3, "adspower_ram_mb": 792.2, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 6.22, "download_speed_kbps": 10.22, "session_sent_mb": 1.193, "session_received_mb": 1.888, "session_total_mb": 3.081}, "system": {"cpu_percent": 12.9, "ram_percent": 67.2, "ram_used_mb": 8233.5, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:20:49.359365+00
83	1	t	\N	online	\N	\N	4.7	60	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 694.24, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.37, "download_speed_kbps": 2.32, "session_sent_mb": 2.506, "session_received_mb": 4.478, "session_total_mb": 6.984}, "system": {"cpu_percent": 4.7, "ram_percent": 60.0, "ram_used_mb": 6677.6, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:23:22.123946+00
96	1	t	\N	online	\N	\N	3.3	60.3	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 697.23, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.67, "download_speed_kbps": 1.67, "session_sent_mb": 2.749, "session_received_mb": 4.881, "session_total_mb": 7.63}, "system": {"cpu_percent": 3.3, "ram_percent": 60.3, "ram_used_mb": 6710.8, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:25:34.525323+00
104	1	t	\N	online	\N	\N	5.4	61.1	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.4, "adspower_ram_mb": 710.19, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.75, "download_speed_kbps": 2.41, "session_sent_mb": 2.961, "session_received_mb": 5.212, "session_total_mb": 8.172}, "system": {"cpu_percent": 5.4, "ram_percent": 61.1, "ram_used_mb": 6837.0, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:26:55.955237+00
69	1	t	\N	online	\N	\N	7	67.1	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 8.8, "adspower_ram_mb": 792.27, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 12.98, "download_speed_kbps": 29.32, "session_sent_mb": 1.322, "session_received_mb": 2.18, "session_total_mb": 3.502}, "system": {"cpu_percent": 7.0, "ram_percent": 67.1, "ram_used_mb": 8221.7, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:20:59.548238+00
70	1	t	\N	online	\N	\N	22.7	68	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 7.5, "adspower_ram_mb": 775.55, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 14.2, "download_speed_kbps": 23.58, "session_sent_mb": 1.464, "session_received_mb": 2.415, "session_total_mb": 3.878}, "system": {"cpu_percent": 22.7, "ram_percent": 68.0, "ram_used_mb": 8103.7, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:21:09.74433+00
72	1	t	\N	online	\N	\N	5.6	62.9	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 2.2, "adspower_ram_mb": 761.87, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 10.91, "download_speed_kbps": 27.37, "session_sent_mb": 1.639, "session_received_mb": 2.785, "session_total_mb": 4.424}, "system": {"cpu_percent": 5.6, "ram_percent": 62.9, "ram_used_mb": 7186.7, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:21:30.109379+00
76	1	t	\N	online	\N	\N	8.2	59.5	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.4, "adspower_ram_mb": 757.13, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 9.45, "download_speed_kbps": 13.65, "session_sent_mb": 2.001, "session_received_mb": 3.429, "session_total_mb": 5.43}, "system": {"cpu_percent": 8.2, "ram_percent": 59.5, "ram_used_mb": 6647.6, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:22:10.8375+00
78	1	t	\N	online	\N	\N	6.2	59.7	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 758.05, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 9.19, "download_speed_kbps": 14.57, "session_sent_mb": 2.211, "session_received_mb": 3.737, "session_total_mb": 5.949}, "system": {"cpu_percent": 6.2, "ram_percent": 59.7, "ram_used_mb": 6671.2, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:22:31.208885+00
82	1	t	\N	online	\N	\N	4.2	60	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 693.92, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 8.03, "download_speed_kbps": 13.7, "session_sent_mb": 2.492, "session_received_mb": 4.455, "session_total_mb": 6.947}, "system": {"cpu_percent": 4.2, "ram_percent": 60.0, "ram_used_mb": 6673.1, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:23:11.940638+00
89	1	t	\N	online	\N	\N	11.1	60.2	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 695.24, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.42, "download_speed_kbps": 1.51, "session_sent_mb": 2.626, "session_received_mb": 4.757, "session_total_mb": 7.383}, "system": {"cpu_percent": 11.1, "ram_percent": 60.2, "ram_used_mb": 6696.4, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:24:23.243438+00
95	1	t	\N	online	\N	\N	5.6	60.2	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.1, "adspower_ram_mb": 697.07, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.85, "download_speed_kbps": 2.25, "session_sent_mb": 2.732, "session_received_mb": 4.865, "session_total_mb": 7.597}, "system": {"cpu_percent": 5.6, "ram_percent": 60.2, "ram_used_mb": 6698.1, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:25:24.34061+00
103	1	t	\N	online	\N	\N	8.5	61.1	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 714.49, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.99, "download_speed_kbps": 2.49, "session_sent_mb": 2.943, "session_received_mb": 5.188, "session_total_mb": 8.131}, "system": {"cpu_percent": 8.5, "ram_percent": 61.1, "ram_used_mb": 6838.5, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:26:45.770858+00
110	1	t	\N	online	\N	\N	5.5	61.2	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 709.79, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 6.05, "download_speed_kbps": 6.04, "session_sent_mb": 3.107, "session_received_mb": 5.358, "session_total_mb": 8.465}, "system": {"cpu_percent": 5.5, "ram_percent": 61.2, "ram_used_mb": 6862.0, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:27:57.082782+00
71	1	t	\N	online	\N	\N	11.1	62.9	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 4.5, "adspower_ram_mb": 760.76, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 6.71, "download_speed_kbps": 9.87, "session_sent_mb": 1.53, "session_received_mb": 2.513, "session_total_mb": 4.043}, "system": {"cpu_percent": 11.1, "ram_percent": 62.9, "ram_used_mb": 7186.5, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:21:19.922347+00
84	1	t	\N	online	\N	\N	5.4	60.1	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 693.03, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.25, "download_speed_kbps": 3.09, "session_sent_mb": 2.528, "session_received_mb": 4.508, "session_total_mb": 7.037}, "system": {"cpu_percent": 5.4, "ram_percent": 60.1, "ram_used_mb": 6689.6, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:23:32.315412+00
88	1	t	\N	online	\N	\N	4.1	60.1	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 694.82, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.5, "download_speed_kbps": 5.2, "session_sent_mb": 2.612, "session_received_mb": 4.742, "session_total_mb": 7.354}, "system": {"cpu_percent": 4.1, "ram_percent": 60.1, "ram_used_mb": 6675.0, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:24:13.058191+00
105	1	t	\N	online	\N	\N	5.3	61.1	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 710.27, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.24, "download_speed_kbps": 1.53, "session_sent_mb": 2.973, "session_received_mb": 5.227, "session_total_mb": 8.2}, "system": {"cpu_percent": 5.3, "ram_percent": 61.1, "ram_used_mb": 6838.4, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:27:06.143317+00
109	1	t	\N	online	\N	\N	6.9	61.2	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 709.68, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.19, "download_speed_kbps": 2.06, "session_sent_mb": 3.047, "session_received_mb": 5.298, "session_total_mb": 8.344}, "system": {"cpu_percent": 6.9, "ram_percent": 61.2, "ram_used_mb": 6851.8, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:27:46.898382+00
73	1	t	\N	online	\N	\N	4.6	62.8	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.8, "adspower_ram_mb": 762.98, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 8.86, "download_speed_kbps": 21.34, "session_sent_mb": 1.727, "session_received_mb": 2.997, "session_total_mb": 4.724}, "system": {"cpu_percent": 4.6, "ram_percent": 62.8, "ram_used_mb": 7163.5, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:21:40.296774+00
86	1	t	\N	online	\N	\N	3.8	60	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 693.83, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.51, "download_speed_kbps": 3.1, "session_sent_mb": 2.569, "session_received_mb": 4.556, "session_total_mb": 7.125}, "system": {"cpu_percent": 3.8, "ram_percent": 60.0, "ram_used_mb": 6667.2, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:23:52.68936+00
99	1	t	\N	online	\N	\N	6.3	60.7	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 698.04, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.21, "download_speed_kbps": 1.2, "session_sent_mb": 2.826, "session_received_mb": 4.946, "session_total_mb": 7.772}, "system": {"cpu_percent": 6.3, "ram_percent": 60.7, "ram_used_mb": 6765.7, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:26:05.056304+00
107	1	t	\N	online	\N	\N	6.2	61	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 709.52, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.31, "download_speed_kbps": 1.51, "session_sent_mb": 3.007, "session_received_mb": 5.26, "session_total_mb": 8.267}, "system": {"cpu_percent": 6.2, "ram_percent": 61.0, "ram_used_mb": 6827.2, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:27:26.512668+00
74	1	t	\N	online	\N	\N	7.1	62.3	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 1.1, "adspower_ram_mb": 758.67, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 10.42, "download_speed_kbps": 17.35, "session_sent_mb": 1.831, "session_received_mb": 3.17, "session_total_mb": 5.0}, "system": {"cpu_percent": 7.1, "ram_percent": 62.3, "ram_used_mb": 7100.5, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:21:50.47514+00
75	1	t	\N	online	\N	\N	5.4	59.5	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 759.03, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 7.68, "download_speed_kbps": 12.41, "session_sent_mb": 1.907, "session_received_mb": 3.293, "session_total_mb": 5.2}, "system": {"cpu_percent": 5.4, "ram_percent": 59.5, "ram_used_mb": 6650.3, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:22:00.653828+00
79	1	t	\N	online	\N	\N	11.5	59	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 3.9, "adspower_ram_mb": 696.84, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 5.97, "download_speed_kbps": 12.44, "session_sent_mb": 2.271, "session_received_mb": 3.861, "session_total_mb": 6.131}, "system": {"cpu_percent": 11.5, "ram_percent": 59.0, "ram_used_mb": 6567.1, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:22:41.380723+00
87	1	t	\N	online	\N	\N	3.1	60	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 694.65, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.86, "download_speed_kbps": 13.49, "session_sent_mb": 2.587, "session_received_mb": 4.69, "session_total_mb": 7.278}, "system": {"cpu_percent": 3.1, "ram_percent": 60.0, "ram_used_mb": 6677.0, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:24:02.874836+00
91	1	t	\N	online	\N	\N	3.8	60.1	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 696.18, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.47, "download_speed_kbps": 1.47, "session_sent_mb": 2.662, "session_received_mb": 4.792, "session_total_mb": 7.454}, "system": {"cpu_percent": 3.8, "ram_percent": 60.1, "ram_used_mb": 6684.1, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:24:43.614898+00
92	1	t	\N	online	\N	\N	8.1	60.3	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 696.48, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.9, "download_speed_kbps": 1.64, "session_sent_mb": 2.681, "session_received_mb": 4.808, "session_total_mb": 7.489}, "system": {"cpu_percent": 8.1, "ram_percent": 60.3, "ram_used_mb": 6701.2, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:24:53.799051+00
100	1	t	\N	online	\N	\N	5.5	61	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 698.34, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 4.21, "download_speed_kbps": 16.2, "session_sent_mb": 2.868, "session_received_mb": 5.107, "session_total_mb": 7.975}, "system": {"cpu_percent": 5.5, "ram_percent": 61.0, "ram_used_mb": 6816.8, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:26:15.240847+00
108	1	t	\N	online	\N	\N	7.5	61.1	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.4, "adspower_ram_mb": 709.58, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.8, "download_speed_kbps": 1.7, "session_sent_mb": 3.025, "session_received_mb": 5.277, "session_total_mb": 8.302}, "system": {"cpu_percent": 7.5, "ram_percent": 61.1, "ram_used_mb": 6835.7, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:27:36.705185+00
112	1	t	\N	online	\N	\N	14.6	61.6	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 709.93, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 3.22, "download_speed_kbps": 3.75, "session_sent_mb": 3.17, "session_received_mb": 5.508, "session_total_mb": 8.678}, "system": {"cpu_percent": 14.6, "ram_percent": 61.6, "ram_used_mb": 6917.3, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:28:17.463765+00
80	1	t	\N	online	\N	\N	10.7	59.6	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.1, "adspower_ram_mb": 693.12, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 6.23, "download_speed_kbps": 18.52, "session_sent_mb": 2.332, "session_received_mb": 4.045, "session_total_mb": 6.378}, "system": {"cpu_percent": 10.7, "ram_percent": 59.6, "ram_used_mb": 6614.1, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:22:51.573236+00
93	1	t	\N	online	\N	\N	3.2	60.3	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 696.71, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.18, "download_speed_kbps": 1.08, "session_sent_mb": 2.693, "session_received_mb": 4.819, "session_total_mb": 7.512}, "system": {"cpu_percent": 3.2, "ram_percent": 60.3, "ram_used_mb": 6710.8, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:25:03.982425+00
97	1	t	\N	online	\N	\N	47.3	60.7	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 697.61, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 3.42, "download_speed_kbps": 2.88, "session_sent_mb": 2.783, "session_received_mb": 4.91, "session_total_mb": 7.693}, "system": {"cpu_percent": 47.3, "ram_percent": 60.7, "ram_used_mb": 6771.8, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:25:44.701875+00
101	1	t	\N	online	\N	\N	6.1	61.1	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 698.79, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.62, "download_speed_kbps": 2.05, "session_sent_mb": 2.884, "session_received_mb": 5.127, "session_total_mb": 8.012}, "system": {"cpu_percent": 6.1, "ram_percent": 61.1, "ram_used_mb": 6838.2, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:26:25.425696+00
81	1	t	\N	online	\N	\N	5.5	60	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 693.38, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 8.05, "download_speed_kbps": 27.45, "session_sent_mb": 2.413, "session_received_mb": 4.318, "session_total_mb": 6.731}, "system": {"cpu_percent": 5.5, "ram_percent": 60.0, "ram_used_mb": 6681.1, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:23:01.759105+00
85	1	t	\N	online	\N	\N	7.8	59.9	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 693.55, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.57, "download_speed_kbps": 1.69, "session_sent_mb": 2.544, "session_received_mb": 4.525, "session_total_mb": 7.069}, "system": {"cpu_percent": 7.8, "ram_percent": 59.9, "ram_used_mb": 6657.1, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:23:42.501576+00
98	1	t	\N	online	\N	\N	10.4	60.7	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.4, "adspower_ram_mb": 697.87, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.17, "download_speed_kbps": 2.43, "session_sent_mb": 2.804, "session_received_mb": 4.934, "session_total_mb": 7.738}, "system": {"cpu_percent": 10.4, "ram_percent": 60.7, "ram_used_mb": 6776.5, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:25:54.872043+00
102	1	t	\N	online	\N	\N	4.7	61.2	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 2.7, "adspower_ram_mb": 714.17, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 3.92, "download_speed_kbps": 3.56, "session_sent_mb": 2.923, "session_received_mb": 5.163, "session_total_mb": 8.086}, "system": {"cpu_percent": 4.7, "ram_percent": 61.2, "ram_used_mb": 6857.7, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:26:35.61272+00
106	1	t	\N	online	\N	\N	4.7	61	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 709.33, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.12, "download_speed_kbps": 1.86, "session_sent_mb": 2.994, "session_received_mb": 5.245, "session_total_mb": 8.239}, "system": {"cpu_percent": 4.7, "ram_percent": 61.0, "ram_used_mb": 6825.4, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:27:16.32938+00
113	1	t	\N	online	\N	\N	15.3	61.6	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 709.97, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.76, "download_speed_kbps": 3.54, "session_sent_mb": 3.197, "session_received_mb": 5.543, "session_total_mb": 8.74}, "system": {"cpu_percent": 15.3, "ram_percent": 61.6, "ram_used_mb": 6922.8, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:28:27.648989+00
114	1	t	\N	online	\N	\N	3.1	61.5	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 710.01, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.62, "download_speed_kbps": 3.05, "session_sent_mb": 3.223, "session_received_mb": 5.573, "session_total_mb": 8.797}, "system": {"cpu_percent": 3.1, "ram_percent": 61.5, "ram_used_mb": 6912.6, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:28:37.834242+00
115	1	t	\N	online	\N	\N	3.3	61.6	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.4, "adspower_ram_mb": 710.48, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.46, "download_speed_kbps": 2.41, "session_sent_mb": 3.248, "session_received_mb": 5.597, "session_total_mb": 8.845}, "system": {"cpu_percent": 3.3, "ram_percent": 61.6, "ram_used_mb": 6913.0, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:28:48.014835+00
116	1	t	\N	online	\N	\N	5.3	61.5	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 710.53, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.57, "download_speed_kbps": 2.37, "session_sent_mb": 3.273, "session_received_mb": 5.621, "session_total_mb": 8.894}, "system": {"cpu_percent": 5.3, "ram_percent": 61.5, "ram_used_mb": 6897.6, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:28:58.20184+00
117	1	t	\N	online	\N	\N	5.6	61.5	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 710.6, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 3.32, "download_speed_kbps": 5.97, "session_sent_mb": 3.306, "session_received_mb": 5.68, "session_total_mb": 8.987}, "system": {"cpu_percent": 5.6, "ram_percent": 61.5, "ram_used_mb": 6898.4, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:29:08.381945+00
118	1	t	\N	online	\N	\N	9.1	61.6	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 710.64, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.7, "download_speed_kbps": 2.37, "session_sent_mb": 3.333, "session_received_mb": 5.704, "session_total_mb": 9.037}, "system": {"cpu_percent": 9.1, "ram_percent": 61.6, "ram_used_mb": 6913.6, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:29:18.563691+00
119	1	t	\N	online	\N	\N	13.1	61.6	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 710.79, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.54, "download_speed_kbps": 2.69, "session_sent_mb": 3.358, "session_received_mb": 5.731, "session_total_mb": 9.089}, "system": {"cpu_percent": 13.1, "ram_percent": 61.6, "ram_used_mb": 6912.0, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:29:28.747923+00
120	1	t	\N	online	\N	\N	4.7	61.8	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.4, "adspower_ram_mb": 710.88, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.61, "download_speed_kbps": 2.58, "session_sent_mb": 3.384, "session_received_mb": 5.756, "session_total_mb": 9.141}, "system": {"cpu_percent": 4.7, "ram_percent": 61.8, "ram_used_mb": 6929.6, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:29:38.932524+00
121	1	t	\N	online	\N	\N	4.7	61.8	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 711.07, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.77, "download_speed_kbps": 3.17, "session_sent_mb": 3.412, "session_received_mb": 5.788, "session_total_mb": 9.2}, "system": {"cpu_percent": 4.7, "ram_percent": 61.8, "ram_used_mb": 6923.0, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:29:49.116134+00
122	1	t	\N	online	\N	\N	4.1	61.7	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 711.11, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.59, "download_speed_kbps": 2.41, "session_sent_mb": 3.438, "session_received_mb": 5.812, "session_total_mb": 9.249}, "system": {"cpu_percent": 4.1, "ram_percent": 61.7, "ram_used_mb": 6919.8, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:29:59.295269+00
123	1	t	\N	online	\N	\N	14.3	61.8	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 711.34, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.19, "download_speed_kbps": 1.28, "session_sent_mb": 3.449, "session_received_mb": 5.825, "session_total_mb": 9.274}, "system": {"cpu_percent": 14.3, "ram_percent": 61.8, "ram_used_mb": 6930.1, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:30:09.471855+00
127	1	t	\N	online	\N	\N	5	62	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.4, "adspower_ram_mb": 711.93, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.39, "download_speed_kbps": 1.34, "session_sent_mb": 3.522, "session_received_mb": 5.901, "session_total_mb": 9.423}, "system": {"cpu_percent": 5.0, "ram_percent": 62.0, "ram_used_mb": 6951.9, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:30:50.191866+00
131	1	t	\N	online	\N	\N	4.6	61.8	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 2.2, "adspower_ram_mb": 704.43, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.73, "download_speed_kbps": 2.51, "session_sent_mb": 3.592, "session_received_mb": 5.968, "session_total_mb": 9.56}, "system": {"cpu_percent": 4.6, "ram_percent": 61.8, "ram_used_mb": 6928.9, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:31:30.932462+00
135	1	t	\N	online	\N	\N	3.9	61.9	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 704.88, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.35, "download_speed_kbps": 1.32, "session_sent_mb": 3.66, "session_received_mb": 6.038, "session_total_mb": 9.698}, "system": {"cpu_percent": 3.9, "ram_percent": 61.9, "ram_used_mb": 6935.7, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:32:11.668022+00
148	1	t	\N	online	\N	\N	5.4	62.7	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 705.52, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.69, "download_speed_kbps": 1.58, "session_sent_mb": 3.882, "session_received_mb": 6.355, "session_total_mb": 10.237}, "system": {"cpu_percent": 5.4, "ram_percent": 62.7, "ram_used_mb": 7129.9, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:34:24.067848+00
169	1	t	\N	online	\N	\N	11.8	62.8	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 707.32, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.03, "download_speed_kbps": 3.03, "session_sent_mb": 4.26, "session_received_mb": 6.767, "session_total_mb": 11.027}, "system": {"cpu_percent": 11.8, "ram_percent": 62.8, "ram_used_mb": 7141.6, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:37:57.943332+00
124	1	t	\N	online	\N	\N	7.3	61.9	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 711.41, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.87, "download_speed_kbps": 3.38, "session_sent_mb": 3.478, "session_received_mb": 5.858, "session_total_mb": 9.336}, "system": {"cpu_percent": 7.3, "ram_percent": 61.9, "ram_used_mb": 6952.3, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:30:19.656933+00
125	1	t	\N	online	\N	\N	3.2	62	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.4, "adspower_ram_mb": 711.56, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.38, "download_speed_kbps": 1.56, "session_sent_mb": 3.492, "session_received_mb": 5.874, "session_total_mb": 9.365}, "system": {"cpu_percent": 3.2, "ram_percent": 62.0, "ram_used_mb": 6952.6, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:30:29.832877+00
129	1	t	\N	online	\N	\N	8.7	61.9	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.1, "adspower_ram_mb": 712.33, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.34, "download_speed_kbps": 1.23, "session_sent_mb": 3.549, "session_received_mb": 5.925, "session_total_mb": 9.475}, "system": {"cpu_percent": 8.7, "ram_percent": 61.9, "ram_used_mb": 6934.5, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:31:10.56382+00
132	1	t	\N	online	\N	\N	3.4	61.8	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.4, "adspower_ram_mb": 704.5, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.78, "download_speed_kbps": 1.64, "session_sent_mb": 3.61, "session_received_mb": 5.985, "session_total_mb": 9.594}, "system": {"cpu_percent": 3.4, "ram_percent": 61.8, "ram_used_mb": 6932.8, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:31:41.113161+00
133	1	t	\N	online	\N	\N	3.9	62	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 704.77, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.28, "download_speed_kbps": 2.43, "session_sent_mb": 3.632, "session_received_mb": 6.009, "session_total_mb": 9.641}, "system": {"cpu_percent": 3.9, "ram_percent": 62.0, "ram_used_mb": 6950.8, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:31:51.301127+00
145	1	t	\N	online	\N	\N	6.3	62.2	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 705.35, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.59, "download_speed_kbps": 1.61, "session_sent_mb": 3.828, "session_received_mb": 6.284, "session_total_mb": 10.112}, "system": {"cpu_percent": 6.3, "ram_percent": 62.2, "ram_used_mb": 7049.1, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:33:53.511079+00
146	1	t	\N	online	\N	\N	3.9	62.2	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 705.37, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.57, "download_speed_kbps": 1.22, "session_sent_mb": 3.843, "session_received_mb": 6.296, "session_total_mb": 10.139}, "system": {"cpu_percent": 3.9, "ram_percent": 62.2, "ram_used_mb": 7049.4, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:34:03.697934+00
150	1	t	\N	online	\N	\N	3.2	62.6	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.4, "adspower_ram_mb": 705.54, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.65, "download_speed_kbps": 1.43, "session_sent_mb": 3.912, "session_received_mb": 6.383, "session_total_mb": 10.295}, "system": {"cpu_percent": 3.2, "ram_percent": 62.6, "ram_used_mb": 7114.5, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:34:44.436205+00
158	1	t	\N	online	\N	\N	5.7	62.6	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 705.81, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.53, "download_speed_kbps": 1.26, "session_sent_mb": 4.051, "session_received_mb": 6.531, "session_total_mb": 10.582}, "system": {"cpu_percent": 5.7, "ram_percent": 62.6, "ram_used_mb": 7110.7, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:36:05.911129+00
166	1	t	\N	online	\N	\N	3.3	62.7	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 706.98, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.68, "download_speed_kbps": 2.45, "session_sent_mb": 4.202, "session_received_mb": 6.694, "session_total_mb": 10.896}, "system": {"cpu_percent": 3.3, "ram_percent": 62.7, "ram_used_mb": 7123.4, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:37:27.380589+00
167	1	t	\N	online	\N	\N	3.2	62.7	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 707.1, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.27, "download_speed_kbps": 1.44, "session_sent_mb": 4.214, "session_received_mb": 6.708, "session_total_mb": 10.923}, "system": {"cpu_percent": 3.2, "ram_percent": 62.7, "ram_used_mb": 7123.9, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:37:37.562927+00
171	1	t	\N	online	\N	\N	5.7	62.9	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 707.51, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.57, "download_speed_kbps": 1.79, "session_sent_mb": 4.299, "session_received_mb": 6.87, "session_total_mb": 11.169}, "system": {"cpu_percent": 5.7, "ram_percent": 62.9, "ram_used_mb": 7159.7, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:38:18.308285+00
126	1	t	\N	online	\N	\N	4	61.9	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.4, "adspower_ram_mb": 711.72, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.65, "download_speed_kbps": 1.41, "session_sent_mb": 3.508, "session_received_mb": 5.888, "session_total_mb": 9.396}, "system": {"cpu_percent": 4.0, "ram_percent": 61.9, "ram_used_mb": 6935.2, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:30:40.016042+00
130	1	t	\N	online	\N	\N	6.2	61.9	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 712.37, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.56, "download_speed_kbps": 1.83, "session_sent_mb": 3.565, "session_received_mb": 5.943, "session_total_mb": 9.508}, "system": {"cpu_percent": 6.2, "ram_percent": 61.9, "ram_used_mb": 6935.9, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:31:20.746913+00
143	1	t	\N	online	\N	\N	4	62.2	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 705.2, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.46, "download_speed_kbps": 1.48, "session_sent_mb": 3.796, "session_received_mb": 6.254, "session_total_mb": 10.049}, "system": {"cpu_percent": 4.0, "ram_percent": 62.2, "ram_used_mb": 7047.9, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:33:33.145154+00
147	1	t	\N	online	\N	\N	4	62.3	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 705.47, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.14, "download_speed_kbps": 4.41, "session_sent_mb": 3.865, "session_received_mb": 6.34, "session_total_mb": 10.204}, "system": {"cpu_percent": 4.0, "ram_percent": 62.3, "ram_used_mb": 7051.0, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:34:13.878254+00
164	1	t	\N	online	\N	\N	3.4	62.7	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 706.9, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.61, "download_speed_kbps": 1.72, "session_sent_mb": 4.166, "session_received_mb": 6.65, "session_total_mb": 10.816}, "system": {"cpu_percent": 3.4, "ram_percent": 62.7, "ram_used_mb": 7126.5, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:37:07.012339+00
168	1	t	\N	online	\N	\N	12.1	62.5	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 707.3, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.56, "download_speed_kbps": 2.86, "session_sent_mb": 4.24, "session_received_mb": 6.737, "session_total_mb": 10.977}, "system": {"cpu_percent": 12.1, "ram_percent": 62.5, "ram_used_mb": 7094.6, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:37:47.755272+00
128	1	t	\N	online	\N	\N	3.8	62	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 712.29, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.42, "download_speed_kbps": 1.18, "session_sent_mb": 3.536, "session_received_mb": 5.913, "session_total_mb": 9.449}, "system": {"cpu_percent": 3.8, "ram_percent": 62.0, "ram_used_mb": 6952.5, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:31:00.37892+00
136	1	t	\N	online	\N	\N	5.6	62	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 704.9, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.21, "download_speed_kbps": 1.9, "session_sent_mb": 3.682, "session_received_mb": 6.057, "session_total_mb": 9.739}, "system": {"cpu_percent": 5.6, "ram_percent": 62.0, "ram_used_mb": 6952.4, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:32:21.852423+00
149	1	t	\N	online	\N	\N	6.2	62.7	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 705.53, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.38, "download_speed_kbps": 1.39, "session_sent_mb": 3.895, "session_received_mb": 6.369, "session_total_mb": 10.265}, "system": {"cpu_percent": 6.2, "ram_percent": 62.7, "ram_used_mb": 7129.8, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:34:34.251935+00
153	1	t	\N	online	\N	\N	33.8	62.5	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 705.68, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.21, "download_speed_kbps": 2.51, "session_sent_mb": 3.967, "session_received_mb": 6.442, "session_total_mb": 10.409}, "system": {"cpu_percent": 33.8, "ram_percent": 62.5, "ram_used_mb": 7104.0, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:35:14.997426+00
170	1	t	\N	online	\N	\N	4.6	62.8	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.4, "adspower_ram_mb": 707.4, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.36, "download_speed_kbps": 8.57, "session_sent_mb": 4.284, "session_received_mb": 6.852, "session_total_mb": 11.136}, "system": {"cpu_percent": 4.6, "ram_percent": 62.8, "ram_used_mb": 7141.4, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:38:08.129229+00
174	1	t	\N	online	\N	\N	24	63.2	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 707.71, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.73, "download_speed_kbps": 1.5, "session_sent_mb": 4.344, "session_received_mb": 6.913, "session_total_mb": 11.257}, "system": {"cpu_percent": 24.0, "ram_percent": 63.2, "ram_used_mb": 7216.1, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:38:48.863717+00
134	1	t	\N	online	\N	\N	9.1	62	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 704.84, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.46, "download_speed_kbps": 1.64, "session_sent_mb": 3.647, "session_received_mb": 6.025, "session_total_mb": 9.672}, "system": {"cpu_percent": 9.1, "ram_percent": 62.0, "ram_used_mb": 6952.5, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:32:01.48863+00
138	1	t	\N	online	\N	\N	6.2	61.9	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 704.95, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.7, "download_speed_kbps": 1.52, "session_sent_mb": 3.713, "session_received_mb": 6.091, "session_total_mb": 9.804}, "system": {"cpu_percent": 6.2, "ram_percent": 61.9, "ram_used_mb": 6938.3, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:32:42.215037+00
151	1	t	\N	online	\N	\N	5.3	62.7	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 705.63, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.74, "download_speed_kbps": 1.61, "session_sent_mb": 3.929, "session_received_mb": 6.399, "session_total_mb": 10.329}, "system": {"cpu_percent": 5.3, "ram_percent": 62.7, "ram_used_mb": 7131.3, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:34:54.623241+00
159	1	t	\N	online	\N	\N	9.1	62.6	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 705.85, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.39, "download_speed_kbps": 1.36, "session_sent_mb": 4.065, "session_received_mb": 6.544, "session_total_mb": 10.609}, "system": {"cpu_percent": 9.1, "ram_percent": 62.6, "ram_used_mb": 7115.2, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:36:16.094441+00
172	1	t	\N	online	\N	\N	4.6	62.7	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 707.57, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.53, "download_speed_kbps": 1.75, "session_sent_mb": 4.314, "session_received_mb": 6.887, "session_total_mb": 11.202}, "system": {"cpu_percent": 4.6, "ram_percent": 62.7, "ram_used_mb": 7123.2, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:38:28.497255+00
137	1	t	\N	online	\N	\N	2.5	62	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 704.93, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.4, "download_speed_kbps": 1.9, "session_sent_mb": 3.696, "session_received_mb": 6.076, "session_total_mb": 9.772}, "system": {"cpu_percent": 2.5, "ram_percent": 62.0, "ram_used_mb": 6952.7, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:32:32.034358+00
141	1	t	\N	online	\N	\N	7.6	62.2	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 705.15, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.41, "download_speed_kbps": 1.51, "session_sent_mb": 3.766, "session_received_mb": 6.223, "session_total_mb": 9.988}, "system": {"cpu_percent": 7.6, "ram_percent": 62.2, "ram_used_mb": 7046.7, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:33:12.775809+00
154	1	t	\N	online	\N	\N	4.6	62.5	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 705.7, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.55, "download_speed_kbps": 1.48, "session_sent_mb": 3.982, "session_received_mb": 6.457, "session_total_mb": 10.439}, "system": {"cpu_percent": 4.6, "ram_percent": 62.5, "ram_used_mb": 7106.0, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:35:25.177219+00
162	1	t	\N	online	\N	\N	4.2	62.8	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.4, "adspower_ram_mb": 706.87, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.0, "download_speed_kbps": 1.69, "session_sent_mb": 4.138, "session_received_mb": 6.621, "session_total_mb": 10.759}, "system": {"cpu_percent": 4.2, "ram_percent": 62.8, "ram_used_mb": 7140.4, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:36:46.649284+00
175	1	t	\N	online	\N	\N	3.9	63	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 707.73, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.32, "download_speed_kbps": 1.22, "session_sent_mb": 4.357, "session_received_mb": 6.925, "session_total_mb": 11.282}, "system": {"cpu_percent": 3.9, "ram_percent": 63.0, "ram_used_mb": 7182.4, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:38:59.05262+00
139	1	t	\N	online	\N	\N	3.8	62	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.1, "adspower_ram_mb": 705.03, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.74, "download_speed_kbps": 3.29, "session_sent_mb": 3.73, "session_received_mb": 6.124, "session_total_mb": 9.854}, "system": {"cpu_percent": 3.8, "ram_percent": 62.0, "ram_used_mb": 6965.6, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:32:52.40294+00
152	1	t	\N	online	\N	\N	4.9	62.4	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 705.66, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.56, "download_speed_kbps": 1.82, "session_sent_mb": 3.945, "session_received_mb": 6.417, "session_total_mb": 10.362}, "system": {"cpu_percent": 4.9, "ram_percent": 62.4, "ram_used_mb": 7087.1, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:35:04.802628+00
156	1	t	\N	online	\N	\N	4	62.7	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 705.79, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.62, "download_speed_kbps": 2.71, "session_sent_mb": 4.022, "session_received_mb": 6.497, "session_total_mb": 10.519}, "system": {"cpu_percent": 4.0, "ram_percent": 62.7, "ram_used_mb": 7126.0, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:35:45.544479+00
160	1	t	\N	online	\N	\N	6.5	62.9	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 705.9, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.75, "download_speed_kbps": 1.99, "session_sent_mb": 4.082, "session_received_mb": 6.564, "session_total_mb": 10.647}, "system": {"cpu_percent": 6.5, "ram_percent": 62.9, "ram_used_mb": 7158.8, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:36:26.275923+00
173	1	t	\N	online	\N	\N	2.5	62.6	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.1, "adspower_ram_mb": 707.6, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.21, "download_speed_kbps": 1.12, "session_sent_mb": 4.326, "session_received_mb": 6.898, "session_total_mb": 11.225}, "system": {"cpu_percent": 2.5, "ram_percent": 62.6, "ram_used_mb": 7107.5, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:38:38.678553+00
177	1	t	\N	online	\N	\N	4.8	62.9	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 707.98, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.35, "download_speed_kbps": 1.26, "session_sent_mb": 4.392, "session_received_mb": 6.979, "session_total_mb": 11.371}, "system": {"cpu_percent": 4.8, "ram_percent": 62.9, "ram_used_mb": 7165.1, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:39:19.425188+00
140	1	t	\N	online	\N	\N	3.9	62.1	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 705.09, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.16, "download_speed_kbps": 8.4, "session_sent_mb": 3.752, "session_received_mb": 6.208, "session_total_mb": 9.959}, "system": {"cpu_percent": 3.9, "ram_percent": 62.1, "ram_used_mb": 6968.4, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:33:02.589968+00
144	1	t	\N	online	\N	\N	4.1	62.2	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.4, "adspower_ram_mb": 705.23, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.64, "download_speed_kbps": 1.42, "session_sent_mb": 3.812, "session_received_mb": 6.268, "session_total_mb": 10.08}, "system": {"cpu_percent": 4.1, "ram_percent": 62.2, "ram_used_mb": 7048.7, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:33:43.326416+00
157	1	t	\N	online	\N	\N	3.1	62.7	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.1, "adspower_ram_mb": 705.8, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.42, "download_speed_kbps": 2.12, "session_sent_mb": 4.036, "session_received_mb": 6.518, "session_total_mb": 10.554}, "system": {"cpu_percent": 3.1, "ram_percent": 62.7, "ram_used_mb": 7127.9, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:35:55.729524+00
161	1	t	\N	online	\N	\N	3.8	62.8	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 2.9, "adspower_ram_mb": 706.62, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 3.56, "download_speed_kbps": 4.0, "session_sent_mb": 4.118, "session_received_mb": 6.604, "session_total_mb": 10.722}, "system": {"cpu_percent": 3.8, "ram_percent": 62.8, "ram_used_mb": 7141.6, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:36:36.466894+00
165	1	t	\N	online	\N	\N	6.1	62.7	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 706.97, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.91, "download_speed_kbps": 2.01, "session_sent_mb": 4.185, "session_received_mb": 6.67, "session_total_mb": 10.855}, "system": {"cpu_percent": 6.1, "ram_percent": 62.7, "ram_used_mb": 7126.0, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:37:17.203441+00
142	1	t	\N	online	\N	\N	3.9	62.2	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 705.17, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.54, "download_speed_kbps": 1.64, "session_sent_mb": 3.781, "session_received_mb": 6.239, "session_total_mb": 10.02}, "system": {"cpu_percent": 3.9, "ram_percent": 62.2, "ram_used_mb": 7047.0, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:33:22.962016+00
155	1	t	\N	online	\N	\N	4.6	62.5	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 705.71, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.36, "download_speed_kbps": 1.32, "session_sent_mb": 3.996, "session_received_mb": 6.47, "session_total_mb": 10.466}, "system": {"cpu_percent": 4.6, "ram_percent": 62.5, "ram_used_mb": 7104.7, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:35:35.362932+00
163	1	t	\N	online	\N	\N	7.1	62.9	39.3	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.1, "adspower_ram_mb": 706.88, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.23, "download_speed_kbps": 1.19, "session_sent_mb": 4.15, "session_received_mb": 6.633, "session_total_mb": 10.783}, "system": {"cpu_percent": 7.1, "ram_percent": 62.9, "ram_used_mb": 7157.8, "ram_total_mb": 16384.0, "disk_percent": 39.3}}	[]	2026-03-30 14:36:56.834105+00
176	1	t	\N	online	\N	\N	11.9	63	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 707.94, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.23, "download_speed_kbps": 4.11, "session_sent_mb": 4.379, "session_received_mb": 6.966, "session_total_mb": 11.345}, "system": {"cpu_percent": 11.9, "ram_percent": 63.0, "ram_used_mb": 7168.0, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:39:09.237211+00
178	1	t	\N	online	\N	\N	5.6	62.6	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 708.01, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.64, "download_speed_kbps": 1.58, "session_sent_mb": 4.409, "session_received_mb": 6.995, "session_total_mb": 11.403}, "system": {"cpu_percent": 5.6, "ram_percent": 62.6, "ram_used_mb": 7107.8, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:39:29.607491+00
179	1	t	\N	online	\N	\N	4.1	62.6	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.1, "adspower_ram_mb": 708.02, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.62, "download_speed_kbps": 1.66, "session_sent_mb": 4.425, "session_received_mb": 7.011, "session_total_mb": 11.436}, "system": {"cpu_percent": 4.1, "ram_percent": 62.6, "ram_used_mb": 7115.8, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:39:39.788607+00
180	1	t	\N	online	\N	\N	6.9	62.7	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.4, "adspower_ram_mb": 708.1, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.69, "download_speed_kbps": 2.41, "session_sent_mb": 4.451, "session_received_mb": 7.035, "session_total_mb": 11.486}, "system": {"cpu_percent": 6.9, "ram_percent": 62.7, "ram_used_mb": 7130.0, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:39:49.972322+00
181	1	t	\N	online	\N	\N	6.2	62.7	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.1, "adspower_ram_mb": 708.13, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.52, "download_speed_kbps": 2.12, "session_sent_mb": 4.466, "session_received_mb": 7.056, "session_total_mb": 11.522}, "system": {"cpu_percent": 6.2, "ram_percent": 62.7, "ram_used_mb": 7131.2, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:40:00.163431+00
182	1	t	\N	online	\N	\N	6.1	62.6	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 708.14, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.47, "download_speed_kbps": 1.22, "session_sent_mb": 4.481, "session_received_mb": 7.068, "session_total_mb": 11.549}, "system": {"cpu_percent": 6.1, "ram_percent": 62.6, "ram_used_mb": 7114.9, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:40:10.349323+00
183	1	t	\N	online	\N	\N	6.3	62.8	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 708.34, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.37, "download_speed_kbps": 2.45, "session_sent_mb": 4.505, "session_received_mb": 7.093, "session_total_mb": 11.597}, "system": {"cpu_percent": 6.3, "ram_percent": 62.8, "ram_used_mb": 7135.3, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:40:20.532965+00
184	1	t	\N	online	\N	\N	7.9	62.9	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 708.36, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.69, "download_speed_kbps": 2.03, "session_sent_mb": 4.521, "session_received_mb": 7.113, "session_total_mb": 11.634}, "system": {"cpu_percent": 7.9, "ram_percent": 62.9, "ram_used_mb": 7151.9, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:40:30.716695+00
185	1	t	\N	online	\N	\N	10.5	63.1	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.1, "adspower_ram_mb": 708.4, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 7.02, "download_speed_kbps": 20.55, "session_sent_mb": 4.591, "session_received_mb": 7.317, "session_total_mb": 11.908}, "system": {"cpu_percent": 10.5, "ram_percent": 63.1, "ram_used_mb": 7193.6, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:40:40.898969+00
186	1	t	\N	online	\N	\N	4.7	63.2	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 708.48, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.89, "download_speed_kbps": 1.56, "session_sent_mb": 4.61, "session_received_mb": 7.333, "session_total_mb": 11.943}, "system": {"cpu_percent": 4.7, "ram_percent": 63.2, "ram_used_mb": 7207.2, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:40:51.087531+00
187	1	t	\N	online	\N	\N	5.7	63.2	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 708.5, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.75, "download_speed_kbps": 8.89, "session_sent_mb": 4.627, "session_received_mb": 7.421, "session_total_mb": 12.049}, "system": {"cpu_percent": 5.7, "ram_percent": 63.2, "ram_used_mb": 7211.1, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:41:01.271575+00
188	1	t	\N	online	\N	\N	7.5	63.1	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 708.7, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.59, "download_speed_kbps": 1.71, "session_sent_mb": 4.643, "session_received_mb": 7.438, "session_total_mb": 12.081}, "system": {"cpu_percent": 7.5, "ram_percent": 63.1, "ram_used_mb": 7194.6, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:41:11.461888+00
189	1	t	\N	online	\N	\N	5.5	62.9	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 708.72, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.08, "download_speed_kbps": 2.06, "session_sent_mb": 4.664, "session_received_mb": 7.459, "session_total_mb": 12.123}, "system": {"cpu_percent": 5.5, "ram_percent": 62.9, "ram_used_mb": 7150.0, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:41:21.650353+00
202	1	t	\N	online	\N	\N	3.8	63.2	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 709.79, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.63, "download_speed_kbps": 1.49, "session_sent_mb": 4.891, "session_received_mb": 7.747, "session_total_mb": 12.639}, "system": {"cpu_percent": 3.8, "ram_percent": 63.2, "ram_used_mb": 7212.1, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:43:34.059588+00
206	1	t	\N	online	\N	\N	4.9	63.1	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 709.99, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.44, "download_speed_kbps": 4.83, "session_sent_mb": 4.967, "session_received_mb": 7.853, "session_total_mb": 12.82}, "system": {"cpu_percent": 4.9, "ram_percent": 63.1, "ram_used_mb": 7186.7, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:44:14.775479+00
223	1	t	\N	online	\N	\N	20.5	63.5	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.1, "adspower_ram_mb": 710.79, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.27, "download_speed_kbps": 1.14, "session_sent_mb": 5.264, "session_received_mb": 8.158, "session_total_mb": 13.422}, "system": {"cpu_percent": 20.5, "ram_percent": 63.5, "ram_used_mb": 7245.3, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:47:07.930979+00
227	1	t	\N	online	\N	\N	5.3	63.4	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 711.02, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.86, "download_speed_kbps": 2.59, "session_sent_mb": 5.34, "session_received_mb": 8.231, "session_total_mb": 13.571}, "system": {"cpu_percent": 5.3, "ram_percent": 63.4, "ram_used_mb": 7227.5, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:47:48.681409+00
240	1	t	\N	online	\N	\N	5.7	63.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 711.47, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.52, "download_speed_kbps": 1.26, "session_sent_mb": 5.549, "session_received_mb": 8.522, "session_total_mb": 14.071}, "system": {"cpu_percent": 5.7, "ram_percent": 63.3, "ram_used_mb": 7216.3, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:50:01.09053+00
244	1	t	\N	online	\N	\N	4	63.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 711.77, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.48, "download_speed_kbps": 1.12, "session_sent_mb": 5.629, "session_received_mb": 8.603, "session_total_mb": 14.232}, "system": {"cpu_percent": 4.0, "ram_percent": 63.3, "ram_used_mb": 7216.9, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:50:41.818145+00
248	1	t	\N	online	\N	\N	3.2	63.4	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 712.14, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.6, "download_speed_kbps": 1.48, "session_sent_mb": 5.694, "session_received_mb": 9.014, "session_total_mb": 14.708}, "system": {"cpu_percent": 3.2, "ram_percent": 63.4, "ram_used_mb": 7222.4, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:51:22.544779+00
190	1	t	\N	online	\N	\N	3.9	62.8	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 2.2, "adspower_ram_mb": 708.75, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.8, "download_speed_kbps": 1.78, "session_sent_mb": 4.682, "session_received_mb": 7.476, "session_total_mb": 12.158}, "system": {"cpu_percent": 3.9, "ram_percent": 62.8, "ram_used_mb": 7147.9, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:41:31.837863+00
194	1	t	\N	online	\N	\N	4.1	62.9	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 709.09, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.54, "download_speed_kbps": 1.72, "session_sent_mb": 4.755, "session_received_mb": 7.543, "session_total_mb": 12.299}, "system": {"cpu_percent": 4.1, "ram_percent": 62.9, "ram_used_mb": 7156.7, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:42:12.575306+00
207	1	t	\N	online	\N	\N	11.5	63.2	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.1, "adspower_ram_mb": 710.02, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.37, "download_speed_kbps": 1.43, "session_sent_mb": 4.98, "session_received_mb": 7.868, "session_total_mb": 12.848}, "system": {"cpu_percent": 11.5, "ram_percent": 63.2, "ram_used_mb": 7212.6, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:44:24.958215+00
228	1	t	\N	online	\N	\N	5.4	63.4	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 711.04, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.5, "download_speed_kbps": 1.38, "session_sent_mb": 5.355, "session_received_mb": 8.245, "session_total_mb": 13.599}, "system": {"cpu_percent": 5.4, "ram_percent": 63.4, "ram_used_mb": 7231.7, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:47:58.871544+00
245	1	t	\N	online	\N	\N	4.1	63.4	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 711.88, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.51, "download_speed_kbps": 1.47, "session_sent_mb": 5.644, "session_received_mb": 8.618, "session_total_mb": 14.262}, "system": {"cpu_percent": 4.1, "ram_percent": 63.4, "ram_used_mb": 7232.6, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:50:52.00014+00
191	1	t	\N	online	\N	\N	2.4	62.8	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 708.84, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.34, "download_speed_kbps": 1.36, "session_sent_mb": 4.695, "session_received_mb": 7.49, "session_total_mb": 12.185}, "system": {"cpu_percent": 2.4, "ram_percent": 62.8, "ram_used_mb": 7148.3, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:41:42.023793+00
204	1	t	\N	online	\N	\N	4.1	63.1	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 709.94, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.67, "download_speed_kbps": 2.35, "session_sent_mb": 4.93, "session_received_mb": 7.785, "session_total_mb": 12.715}, "system": {"cpu_percent": 4.1, "ram_percent": 63.1, "ram_used_mb": 7194.3, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:43:54.409514+00
217	1	t	\N	online	\N	\N	8.7	63.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 710.48, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.19, "download_speed_kbps": 1.14, "session_sent_mb": 5.149, "session_received_mb": 8.035, "session_total_mb": 13.184}, "system": {"cpu_percent": 8.7, "ram_percent": 63.3, "ram_used_mb": 7219.8, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:46:06.814149+00
225	1	t	\N	online	\N	\N	7.9	63.2	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.0, "adspower_ram_mb": 710.9, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.32, "download_speed_kbps": 1.48, "session_sent_mb": 5.294, "session_received_mb": 8.191, "session_total_mb": 13.485}, "system": {"cpu_percent": 7.9, "ram_percent": 63.2, "ram_used_mb": 7204.5, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:47:28.30511+00
242	1	t	\N	online	\N	\N	5.7	63.4	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 711.5, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 3.17, "download_speed_kbps": 3.55, "session_sent_mb": 5.6, "session_received_mb": 8.579, "session_total_mb": 14.178}, "system": {"cpu_percent": 5.7, "ram_percent": 63.4, "ram_used_mb": 7235.4, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:50:21.446811+00
192	1	t	\N	online	\N	\N	6.5	62.9	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.5, "adspower_ram_mb": 709.03, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 3.28, "download_speed_kbps": 2.56, "session_sent_mb": 4.728, "session_received_mb": 7.515, "session_total_mb": 12.243}, "system": {"cpu_percent": 6.5, "ram_percent": 62.9, "ram_used_mb": 7156.7, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:41:52.20387+00
193	1	t	\N	online	\N	\N	5.4	62.9	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 709.09, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.22, "download_speed_kbps": 1.1, "session_sent_mb": 4.74, "session_received_mb": 7.526, "session_total_mb": 12.266}, "system": {"cpu_percent": 5.4, "ram_percent": 62.9, "ram_used_mb": 7156.1, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:42:02.393437+00
197	1	t	\N	online	\N	\N	5.4	62.9	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 709.21, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.19, "download_speed_kbps": 1.08, "session_sent_mb": 4.802, "session_received_mb": 7.587, "session_total_mb": 12.39}, "system": {"cpu_percent": 5.4, "ram_percent": 62.9, "ram_used_mb": 7157.9, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:42:43.147575+00
205	1	t	\N	online	\N	\N	5.3	63.1	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 709.97, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.25, "download_speed_kbps": 2.05, "session_sent_mb": 4.942, "session_received_mb": 7.805, "session_total_mb": 12.748}, "system": {"cpu_percent": 5.3, "ram_percent": 63.1, "ram_used_mb": 7193.0, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:44:04.59485+00
209	1	t	\N	online	\N	\N	33.1	63.4	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 710.22, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.84, "download_speed_kbps": 1.82, "session_sent_mb": 5.015, "session_received_mb": 7.9, "session_total_mb": 12.915}, "system": {"cpu_percent": 33.1, "ram_percent": 63.4, "ram_used_mb": 7241.8, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:44:45.331194+00
210	1	t	\N	online	\N	\N	6.9	63.4	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 710.24, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.78, "download_speed_kbps": 1.51, "session_sent_mb": 5.033, "session_received_mb": 7.915, "session_total_mb": 12.947}, "system": {"cpu_percent": 6.9, "ram_percent": 63.4, "ram_used_mb": 7240.9, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:44:55.50885+00
218	1	t	\N	online	\N	\N	4.7	63.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 710.51, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.62, "download_speed_kbps": 1.37, "session_sent_mb": 5.165, "session_received_mb": 8.049, "session_total_mb": 13.214}, "system": {"cpu_percent": 4.7, "ram_percent": 63.3, "ram_used_mb": 7220.0, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:46:16.991813+00
226	1	t	\N	online	\N	\N	3.8	63.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 710.92, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.71, "download_speed_kbps": 1.46, "session_sent_mb": 5.311, "session_received_mb": 8.205, "session_total_mb": 13.517}, "system": {"cpu_percent": 3.8, "ram_percent": 63.3, "ram_used_mb": 7213.8, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:47:38.492748+00
230	1	t	\N	online	\N	\N	10	63.4	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 711.18, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.89, "download_speed_kbps": 2.04, "session_sent_mb": 5.392, "session_received_mb": 8.347, "session_total_mb": 13.74}, "system": {"cpu_percent": 10.0, "ram_percent": 63.4, "ram_used_mb": 7225.5, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:48:19.246465+00
231	1	t	\N	online	\N	\N	7.8	63.4	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 711.2, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.3, "download_speed_kbps": 1.27, "session_sent_mb": 5.405, "session_received_mb": 8.36, "session_total_mb": 13.765}, "system": {"cpu_percent": 7.8, "ram_percent": 63.4, "ram_used_mb": 7227.2, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:48:29.43711+00
235	1	t	\N	online	\N	\N	5	63.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.1, "adspower_ram_mb": 711.26, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.05, "download_speed_kbps": 4.25, "session_sent_mb": 5.472, "session_received_mb": 8.449, "session_total_mb": 13.921}, "system": {"cpu_percent": 5.0, "ram_percent": 63.3, "ram_used_mb": 7214.7, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:49:10.171689+00
243	1	t	\N	online	\N	\N	5.3	63.4	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 711.75, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.41, "download_speed_kbps": 1.37, "session_sent_mb": 5.614, "session_received_mb": 8.592, "session_total_mb": 14.206}, "system": {"cpu_percent": 5.3, "ram_percent": 63.4, "ram_used_mb": 7233.3, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:50:31.637427+00
195	1	t	\N	online	\N	\N	4.5	63	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 709.11, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.91, "download_speed_kbps": 1.84, "session_sent_mb": 4.774, "session_received_mb": 7.562, "session_total_mb": 12.336}, "system": {"cpu_percent": 4.5, "ram_percent": 63.0, "ram_used_mb": 7175.8, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:42:22.781305+00
196	1	t	\N	online	\N	\N	3.8	63	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 709.19, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.63, "download_speed_kbps": 1.51, "session_sent_mb": 4.791, "session_received_mb": 7.577, "session_total_mb": 12.367}, "system": {"cpu_percent": 3.8, "ram_percent": 63.0, "ram_used_mb": 7173.2, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:42:32.966699+00
198	1	t	\N	online	\N	\N	4.7	63	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.4, "adspower_ram_mb": 709.24, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.85, "download_speed_kbps": 1.52, "session_sent_mb": 4.821, "session_received_mb": 7.603, "session_total_mb": 12.423}, "system": {"cpu_percent": 4.7, "ram_percent": 63.0, "ram_used_mb": 7173.2, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:42:53.333129+00
200	1	t	\N	online	\N	\N	8.3	62.9	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 709.37, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.04, "download_speed_kbps": 1.93, "session_sent_mb": 4.859, "session_received_mb": 7.707, "session_total_mb": 12.567}, "system": {"cpu_percent": 8.3, "ram_percent": 62.9, "ram_used_mb": 7160.6, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:43:13.688301+00
208	1	t	\N	online	\N	\N	5.2	63.2	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.4, "adspower_ram_mb": 710.2, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.65, "download_speed_kbps": 1.4, "session_sent_mb": 4.997, "session_received_mb": 7.882, "session_total_mb": 12.878}, "system": {"cpu_percent": 5.2, "ram_percent": 63.2, "ram_used_mb": 7199.1, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:44:35.1457+00
211	1	t	\N	online	\N	\N	3.2	63.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 710.25, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.2, "download_speed_kbps": 1.12, "session_sent_mb": 5.045, "session_received_mb": 7.926, "session_total_mb": 12.97}, "system": {"cpu_percent": 3.2, "ram_percent": 63.3, "ram_used_mb": 7218.1, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:45:05.693303+00
212	1	t	\N	online	\N	\N	6.8	63.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 710.27, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.48, "download_speed_kbps": 2.78, "session_sent_mb": 5.069, "session_received_mb": 7.953, "session_total_mb": 13.023}, "system": {"cpu_percent": 6.8, "ram_percent": 63.3, "ram_used_mb": 7221.8, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:45:15.880552+00
213	1	t	\N	online	\N	\N	3.9	63.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 710.28, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.29, "download_speed_kbps": 1.38, "session_sent_mb": 5.082, "session_received_mb": 7.967, "session_total_mb": 13.049}, "system": {"cpu_percent": 3.9, "ram_percent": 63.3, "ram_used_mb": 7218.7, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:45:26.066828+00
215	1	t	\N	online	\N	\N	7.2	63.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 710.35, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.23, "download_speed_kbps": 2.6, "session_sent_mb": 5.121, "session_received_mb": 8.009, "session_total_mb": 13.129}, "system": {"cpu_percent": 7.2, "ram_percent": 63.3, "ram_used_mb": 7220.0, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:45:46.436581+00
219	1	t	\N	online	\N	\N	5.3	63.4	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 710.54, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.62, "download_speed_kbps": 2.24, "session_sent_mb": 5.182, "session_received_mb": 8.071, "session_total_mb": 13.252}, "system": {"cpu_percent": 5.3, "ram_percent": 63.4, "ram_used_mb": 7239.8, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:46:27.178491+00
221	1	t	\N	online	\N	\N	9	63.6	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.5, "adspower_ram_mb": 710.61, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.45, "download_speed_kbps": 2.37, "session_sent_mb": 5.235, "session_received_mb": 8.134, "session_total_mb": 13.369}, "system": {"cpu_percent": 9.0, "ram_percent": 63.6, "ram_used_mb": 7273.8, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:46:47.553287+00
229	1	t	\N	online	\N	\N	6.3	63.2	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 711.05, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.88, "download_speed_kbps": 8.27, "session_sent_mb": 5.373, "session_received_mb": 8.327, "session_total_mb": 13.7}, "system": {"cpu_percent": 6.3, "ram_percent": 63.2, "ram_used_mb": 7206.2, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:48:09.055759+00
232	1	t	\N	online	\N	\N	7	63.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 711.21, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.6, "download_speed_kbps": 1.23, "session_sent_mb": 5.421, "session_received_mb": 8.372, "session_total_mb": 13.793}, "system": {"cpu_percent": 7.0, "ram_percent": 63.3, "ram_used_mb": 7211.4, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:48:39.621061+00
233	1	t	\N	online	\N	\N	6.3	63.4	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 711.23, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.44, "download_speed_kbps": 1.4, "session_sent_mb": 5.435, "session_received_mb": 8.386, "session_total_mb": 13.822}, "system": {"cpu_percent": 6.3, "ram_percent": 63.4, "ram_used_mb": 7227.2, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:48:49.808034+00
234	1	t	\N	online	\N	\N	5.7	63.4	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 711.25, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.62, "download_speed_kbps": 2.08, "session_sent_mb": 5.451, "session_received_mb": 8.407, "session_total_mb": 13.858}, "system": {"cpu_percent": 5.7, "ram_percent": 63.4, "ram_used_mb": 7227.8, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:48:59.992118+00
199	1	t	\N	online	\N	\N	2.4	63	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 709.3, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.84, "download_speed_kbps": 8.59, "session_sent_mb": 4.839, "session_received_mb": 7.688, "session_total_mb": 12.527}, "system": {"cpu_percent": 2.4, "ram_percent": 63.0, "ram_used_mb": 7174.8, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:43:03.515978+00
203	1	t	\N	online	\N	\N	5.7	63.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 709.89, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.21, "download_speed_kbps": 1.45, "session_sent_mb": 4.903, "session_received_mb": 7.762, "session_total_mb": 12.665}, "system": {"cpu_percent": 5.7, "ram_percent": 63.3, "ram_used_mb": 7215.2, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:43:44.234405+00
216	1	t	\N	online	\N	\N	6.2	63.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 710.36, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.68, "download_speed_kbps": 1.52, "session_sent_mb": 5.137, "session_received_mb": 8.024, "session_total_mb": 13.161}, "system": {"cpu_percent": 6.2, "ram_percent": 63.3, "ram_used_mb": 7220.1, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:45:56.622574+00
220	1	t	\N	online	\N	\N	4.8	63.4	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 2.6, "adspower_ram_mb": 710.55, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.96, "download_speed_kbps": 3.98, "session_sent_mb": 5.211, "session_received_mb": 8.11, "session_total_mb": 13.321}, "system": {"cpu_percent": 4.8, "ram_percent": 63.4, "ram_used_mb": 7239.8, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:46:37.358656+00
224	1	t	\N	online	\N	\N	16.5	63.2	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 710.88, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.67, "download_speed_kbps": 1.82, "session_sent_mb": 5.281, "session_received_mb": 8.176, "session_total_mb": 13.457}, "system": {"cpu_percent": 16.5, "ram_percent": 63.2, "ram_used_mb": 7205.9, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:47:18.122922+00
237	1	t	\N	online	\N	\N	5.3	63.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 711.41, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.47, "download_speed_kbps": 1.6, "session_sent_mb": 5.501, "session_received_mb": 8.478, "session_total_mb": 13.979}, "system": {"cpu_percent": 5.3, "ram_percent": 63.3, "ram_used_mb": 7213.0, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:49:30.550417+00
241	1	t	\N	online	\N	\N	3.2	63.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.1, "adspower_ram_mb": 711.48, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.96, "download_speed_kbps": 2.13, "session_sent_mb": 5.568, "session_received_mb": 8.543, "session_total_mb": 14.112}, "system": {"cpu_percent": 3.2, "ram_percent": 63.3, "ram_used_mb": 7215.5, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:50:11.26713+00
201	1	t	\N	online	\N	\N	3.8	63.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 709.59, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.59, "download_speed_kbps": 2.54, "session_sent_mb": 4.875, "session_received_mb": 7.732, "session_total_mb": 12.608}, "system": {"cpu_percent": 3.8, "ram_percent": 63.3, "ram_used_mb": 7214.2, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:43:23.879266+00
214	1	t	\N	online	\N	\N	5.4	63.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 710.33, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.66, "download_speed_kbps": 1.57, "session_sent_mb": 5.099, "session_received_mb": 7.983, "session_total_mb": 13.081}, "system": {"cpu_percent": 5.4, "ram_percent": 63.3, "ram_used_mb": 7219.9, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:45:36.251494+00
222	1	t	\N	online	\N	\N	3.8	63.7	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 710.76, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.65, "download_speed_kbps": 1.27, "session_sent_mb": 5.252, "session_received_mb": 8.147, "session_total_mb": 13.398}, "system": {"cpu_percent": 3.8, "ram_percent": 63.7, "ram_used_mb": 7289.9, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:46:57.745177+00
239	1	t	\N	online	\N	\N	4.8	63.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 711.45, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.77, "download_speed_kbps": 1.81, "session_sent_mb": 5.534, "session_received_mb": 8.51, "session_total_mb": 14.043}, "system": {"cpu_percent": 4.8, "ram_percent": 63.3, "ram_used_mb": 7216.3, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:49:50.915448+00
247	1	t	\N	online	\N	\N	4.8	63.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.1, "adspower_ram_mb": 711.92, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.3, "download_speed_kbps": 1.36, "session_sent_mb": 5.678, "session_received_mb": 8.999, "session_total_mb": 14.677}, "system": {"cpu_percent": 4.8, "ram_percent": 63.3, "ram_used_mb": 7220.5, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:51:12.356176+00
236	1	t	\N	online	\N	\N	4	63.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 711.29, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.5, "download_speed_kbps": 1.29, "session_sent_mb": 5.487, "session_received_mb": 8.462, "session_total_mb": 13.949}, "system": {"cpu_percent": 4.0, "ram_percent": 63.3, "ram_used_mb": 7214.7, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:49:20.356742+00
238	1	t	\N	online	\N	\N	5.6	63.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 711.43, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.5, "download_speed_kbps": 1.36, "session_sent_mb": 5.516, "session_received_mb": 8.492, "session_total_mb": 14.008}, "system": {"cpu_percent": 5.6, "ram_percent": 63.3, "ram_used_mb": 7216.2, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:49:40.733599+00
246	1	t	\N	online	\N	\N	4.9	63.4	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 711.9, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.18, "download_speed_kbps": 36.97, "session_sent_mb": 5.665, "session_received_mb": 8.986, "session_total_mb": 14.651}, "system": {"cpu_percent": 4.9, "ram_percent": 63.4, "ram_used_mb": 7237.4, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:51:02.177729+00
249	1	t	\N	online	\N	\N	5.3	63.4	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 1.5, "adspower_ram_mb": 722.44, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.39, "download_speed_kbps": 1.36, "session_sent_mb": 5.708, "session_received_mb": 9.027, "session_total_mb": 14.735}, "system": {"cpu_percent": 5.3, "ram_percent": 63.4, "ram_used_mb": 7230.9, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:51:32.723304+00
250	1	t	\N	online	\N	\N	4.6	63.5	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 1.0, "adspower_ram_mb": 712.27, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.94, "download_speed_kbps": 1.54, "session_sent_mb": 5.727, "session_received_mb": 9.043, "session_total_mb": 14.77}, "system": {"cpu_percent": 4.6, "ram_percent": 63.5, "ram_used_mb": 7242.6, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:51:42.909058+00
251	1	t	\N	online	\N	\N	3.9	63.6	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.5, "adspower_ram_mb": 712.38, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 3.35, "download_speed_kbps": 2.8, "session_sent_mb": 5.761, "session_received_mb": 9.07, "session_total_mb": 14.831}, "system": {"cpu_percent": 3.9, "ram_percent": 63.6, "ram_used_mb": 7260.1, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:51:53.099455+00
252	1	t	\N	online	\N	\N	4.9	63.6	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 712.46, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.41, "download_speed_kbps": 1.16, "session_sent_mb": 5.775, "session_received_mb": 9.082, "session_total_mb": 14.857}, "system": {"cpu_percent": 4.9, "ram_percent": 63.6, "ram_used_mb": 7257.0, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:52:03.278489+00
253	1	t	\N	online	\N	\N	16.4	63.5	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.1, "adspower_ram_mb": 712.48, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.27, "download_speed_kbps": 1.2, "session_sent_mb": 5.787, "session_received_mb": 9.094, "session_total_mb": 14.881}, "system": {"cpu_percent": 16.4, "ram_percent": 63.5, "ram_used_mb": 7241.0, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:52:13.462542+00
254	1	t	\N	online	\N	\N	4.6	63.5	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 712.49, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.81, "download_speed_kbps": 2.03, "session_sent_mb": 5.805, "session_received_mb": 9.114, "session_total_mb": 14.92}, "system": {"cpu_percent": 4.6, "ram_percent": 63.5, "ram_used_mb": 7239.9, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:52:23.652772+00
255	1	t	\N	online	\N	\N	3.1	63.5	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 712.5, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.37, "download_speed_kbps": 1.28, "session_sent_mb": 5.819, "session_received_mb": 9.127, "session_total_mb": 14.946}, "system": {"cpu_percent": 3.1, "ram_percent": 63.5, "ram_used_mb": 7240.4, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:52:33.838293+00
256	1	t	\N	online	\N	\N	4.1	63.4	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 712.52, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.92, "download_speed_kbps": 1.52, "session_sent_mb": 5.838, "session_received_mb": 9.142, "session_total_mb": 14.98}, "system": {"cpu_percent": 4.1, "ram_percent": 63.4, "ram_used_mb": 7224.8, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:52:44.021031+00
257	1	t	\N	online	\N	\N	4.9	63.8	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 712.66, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.58, "download_speed_kbps": 1.65, "session_sent_mb": 5.854, "session_received_mb": 9.158, "session_total_mb": 15.012}, "system": {"cpu_percent": 4.9, "ram_percent": 63.8, "ram_used_mb": 7289.6, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:52:54.201578+00
258	1	t	\N	online	\N	\N	5	63.9	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 712.67, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.98, "download_speed_kbps": 9.19, "session_sent_mb": 5.874, "session_received_mb": 9.25, "session_total_mb": 15.123}, "system": {"cpu_percent": 5.0, "ram_percent": 63.9, "ram_used_mb": 7320.0, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:53:04.378766+00
259	1	t	\N	online	\N	\N	3.8	63.8	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.1, "adspower_ram_mb": 712.68, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.29, "download_speed_kbps": 1.19, "session_sent_mb": 5.886, "session_received_mb": 9.262, "session_total_mb": 15.148}, "system": {"cpu_percent": 3.8, "ram_percent": 63.8, "ram_used_mb": 7303.6, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:53:14.568278+00
260	1	t	\N	online	\N	\N	5.5	63.7	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 712.7, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.73, "download_speed_kbps": 1.51, "session_sent_mb": 5.904, "session_received_mb": 9.277, "session_total_mb": 15.18}, "system": {"cpu_percent": 5.5, "ram_percent": 63.7, "ram_used_mb": 7302.1, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:53:24.754183+00
261	1	t	\N	online	\N	\N	5.4	63.4	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 712.77, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.33, "download_speed_kbps": 1.26, "session_sent_mb": 5.917, "session_received_mb": 9.289, "session_total_mb": 15.206}, "system": {"cpu_percent": 5.4, "ram_percent": 63.4, "ram_used_mb": 7249.0, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:53:34.940451+00
262	1	t	\N	online	\N	\N	4.7	63.4	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 713.34, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.58, "download_speed_kbps": 1.43, "session_sent_mb": 5.932, "session_received_mb": 9.304, "session_total_mb": 15.236}, "system": {"cpu_percent": 4.7, "ram_percent": 63.4, "ram_used_mb": 7250.3, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:53:45.123853+00
263	1	t	\N	online	\N	\N	3.1	63.4	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 713.35, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.72, "download_speed_kbps": 1.82, "session_sent_mb": 5.95, "session_received_mb": 9.322, "session_total_mb": 15.271}, "system": {"cpu_percent": 3.1, "ram_percent": 63.4, "ram_used_mb": 7251.6, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:53:55.307195+00
274	1	t	\N	online	\N	\N	21.4	72.7	39.4	1	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 8.1, "adspower_ram_mb": 534.08, "active_browsers_count": 1, "active_sessions": [3], "network": {"upload_speed_kbps": 9.53, "download_speed_kbps": 15.15, "session_sent_mb": 0.565, "session_received_mb": 1.985, "session_total_mb": 2.55}, "system": {"cpu_percent": 21.4, "ram_percent": 72.7, "ram_used_mb": 8112.5, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:55:48.437771+00
276	1	t	\N	online	\N	\N	19.8	70.7	39.4	1	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 7.9, "adspower_ram_mb": 536.64, "active_browsers_count": 1, "active_sessions": [3], "network": {"upload_speed_kbps": 8.45, "download_speed_kbps": 15.32, "session_sent_mb": 0.74, "session_received_mb": 2.284, "session_total_mb": 3.024}, "system": {"cpu_percent": 19.8, "ram_percent": 70.7, "ram_used_mb": 7823.6, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:56:09.14897+00
290	1	t	\N	online	\N	\N	12	69.5	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 7.3, "adspower_ram_mb": 596.35, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 5.06, "download_speed_kbps": 4.97, "session_sent_mb": 2.266, "session_received_mb": 7.198, "session_total_mb": 9.464}, "system": {"cpu_percent": 12.0, "ram_percent": 69.5, "ram_used_mb": 7717.1, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:58:33.162244+00
264	1	t	\N	online	\N	\N	4.6	63.4	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 713.37, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.45, "download_speed_kbps": 1.62, "session_sent_mb": 5.964, "session_received_mb": 9.338, "session_total_mb": 15.302}, "system": {"cpu_percent": 4.6, "ram_percent": 63.4, "ram_used_mb": 7251.4, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:54:05.486044+00
278	1	t	\N	online	\N	\N	12.5	71.1	39.4	1	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 10.0, "adspower_ram_mb": 541.13, "active_browsers_count": 1, "active_sessions": [3], "network": {"upload_speed_kbps": 12.59, "download_speed_kbps": 15.62, "session_sent_mb": 0.994, "session_received_mb": 2.615, "session_total_mb": 3.609}, "system": {"cpu_percent": 12.5, "ram_percent": 71.1, "ram_used_mb": 7895.1, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:56:29.819061+00
289	1	t	\N	online	\N	\N	22.4	70.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 11.2, "adspower_ram_mb": 596.25, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 12.3, "download_speed_kbps": 14.2, "session_sent_mb": 2.216, "session_received_mb": 7.149, "session_total_mb": 9.364}, "system": {"cpu_percent": 22.4, "ram_percent": 70.3, "ram_used_mb": 7844.7, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:58:22.968437+00
265	1	t	\N	online	\N	\N	32.8	63.6	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.1, "adspower_ram_mb": 713.38, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 2.14, "download_speed_kbps": 4.5, "session_sent_mb": 5.985, "session_received_mb": 9.382, "session_total_mb": 15.368}, "system": {"cpu_percent": 32.8, "ram_percent": 63.6, "ram_used_mb": 7283.1, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:54:15.683938+00
271	1	t	\N	online	\N	\N	25.8	71.5	39.4	1	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 12.4, "adspower_ram_mb": 733.09, "active_browsers_count": 1, "active_sessions": [3], "network": {"upload_speed_kbps": 36.64, "download_speed_kbps": 43.95, "session_sent_mb": 0.011, "session_received_mb": 0.009, "session_total_mb": 0.02}, "system": {"cpu_percent": 25.8, "ram_percent": 71.5, "ram_used_mb": 8311.6, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:55:17.121628+00
273	1	t	\N	online	\N	\N	12.3	72.9	39.4	1	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 11.7, "adspower_ram_mb": 534.57, "active_browsers_count": 1, "active_sessions": [3], "network": {"upload_speed_kbps": 11.81, "download_speed_kbps": 62.37, "session_sent_mb": 0.467, "session_received_mb": 1.831, "session_total_mb": 2.298}, "system": {"cpu_percent": 12.3, "ram_percent": 72.9, "ram_used_mb": 8138.1, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:55:38.006494+00
280	1	t	\N	online	\N	\N	12.9	71.2	39.4	1	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 8.0, "adspower_ram_mb": 565.67, "active_browsers_count": 1, "active_sessions": [3], "network": {"upload_speed_kbps": 10.79, "download_speed_kbps": 20.27, "session_sent_mb": 1.222, "session_received_mb": 3.02, "session_total_mb": 4.242}, "system": {"cpu_percent": 12.9, "ram_percent": 71.2, "ram_used_mb": 7910.5, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:56:50.514453+00
292	1	t	\N	online	\N	\N	22.8	70.1	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.3, "adspower_ram_mb": 597.71, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.88, "download_speed_kbps": 1.47, "session_sent_mb": 2.33, "session_received_mb": 7.266, "session_total_mb": 9.595}, "system": {"cpu_percent": 22.8, "ram_percent": 70.1, "ram_used_mb": 7885.4, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:58:53.538258+00
266	1	t	\N	online	\N	\N	6.2	63.8	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 0.2, "adspower_ram_mb": 713.52, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 1.8, "download_speed_kbps": 1.72, "session_sent_mb": 6.003, "session_received_mb": 9.399, "session_total_mb": 15.403}, "system": {"cpu_percent": 6.2, "ram_percent": 63.8, "ram_used_mb": 7303.3, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:54:25.872422+00
282	1	t	\N	online	\N	\N	17.1	70.1	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 16.9, "adspower_ram_mb": 591.32, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 40.69, "download_speed_kbps": 40.56, "session_sent_mb": 1.7, "session_received_mb": 6.549, "session_total_mb": 8.249}, "system": {"cpu_percent": 17.1, "ram_percent": 70.1, "ram_used_mb": 7746.2, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:57:11.41003+00
284	1	t	\N	online	\N	\N	14.3	70	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 7.9, "adspower_ram_mb": 593.91, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 14.57, "download_speed_kbps": 14.59, "session_sent_mb": 1.901, "session_received_mb": 6.741, "session_total_mb": 8.642}, "system": {"cpu_percent": 14.3, "ram_percent": 70.0, "ram_used_mb": 7732.1, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:57:31.864675+00
286	1	t	\N	online	\N	\N	9	69.8	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 9.4, "adspower_ram_mb": 594.32, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 5.44, "download_speed_kbps": 6.13, "session_sent_mb": 2.006, "session_received_mb": 6.848, "session_total_mb": 8.854}, "system": {"cpu_percent": 9.0, "ram_percent": 69.8, "ram_used_mb": 7748.0, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:57:52.264526+00
267	1	t	\N	online	\N	\N	81	75.1	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 4.8, "adspower_ram_mb": 725.43, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 5.56, "download_speed_kbps": 7.36, "session_sent_mb": 6.059, "session_received_mb": 9.474, "session_total_mb": 15.533}, "system": {"cpu_percent": 81.0, "ram_percent": 75.1, "ram_used_mb": 8960.5, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:54:36.206092+00
268	1	t	\N	online	\N	\N	11.6	69.4	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 9.3, "adspower_ram_mb": 702.88, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 3.97, "download_speed_kbps": 3.83, "session_sent_mb": 6.099, "session_received_mb": 9.512, "session_total_mb": 15.611}, "system": {"cpu_percent": 11.6, "ram_percent": 69.4, "ram_used_mb": 7951.9, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:54:46.402378+00
270	1	t	\N	online	\N	\N	12.3	69.6	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 10.6, "adspower_ram_mb": 712.44, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 3.8, "download_speed_kbps": 3.53, "session_sent_mb": 6.202, "session_received_mb": 9.645, "session_total_mb": 15.847}, "system": {"cpu_percent": 12.3, "ram_percent": 69.6, "ram_used_mb": 7987.2, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:55:06.859855+00
272	1	t	\N	online	\N	\N	56.1	72.1	39.4	1	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 10.0, "adspower_ram_mb": 537.73, "active_browsers_count": 1, "active_sessions": [3], "network": {"upload_speed_kbps": 33.07, "download_speed_kbps": 117.95, "session_sent_mb": 0.346, "session_received_mb": 1.199, "session_total_mb": 1.545}, "system": {"cpu_percent": 56.1, "ram_percent": 72.1, "ram_used_mb": 8106.2, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:55:27.552492+00
277	1	t	\N	online	\N	\N	19.8	71.1	39.4	1	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 8.0, "adspower_ram_mb": 536.93, "active_browsers_count": 1, "active_sessions": [3], "network": {"upload_speed_kbps": 12.5, "download_speed_kbps": 16.09, "session_sent_mb": 0.867, "session_received_mb": 2.446, "session_total_mb": 3.313}, "system": {"cpu_percent": 19.8, "ram_percent": 71.1, "ram_used_mb": 7888.0, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:56:19.479295+00
269	1	t	\N	online	\N	\N	10	69.1	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 10.5, "adspower_ram_mb": 712.07, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 6.48, "download_speed_kbps": 9.81, "session_sent_mb": 6.164, "session_received_mb": 9.61, "session_total_mb": 15.774}, "system": {"cpu_percent": 10.0, "ram_percent": 69.1, "ram_used_mb": 7906.7, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:54:56.624748+00
279	1	t	\N	online	\N	\N	17.5	70.9	39.4	1	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 10.2, "adspower_ram_mb": 565.22, "active_browsers_count": 1, "active_sessions": [3], "network": {"upload_speed_kbps": 11.72, "download_speed_kbps": 19.99, "session_sent_mb": 1.113, "session_received_mb": 2.816, "session_total_mb": 3.928}, "system": {"cpu_percent": 17.5, "ram_percent": 70.9, "ram_used_mb": 7864.8, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:56:40.153162+00
283	1	t	\N	online	\N	\N	14.4	69.8	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 10.4, "adspower_ram_mb": 592.07, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 5.55, "download_speed_kbps": 4.61, "session_sent_mb": 1.755, "session_received_mb": 6.595, "session_total_mb": 8.351}, "system": {"cpu_percent": 14.4, "ram_percent": 69.8, "ram_used_mb": 7692.6, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:57:21.625387+00
287	1	t	\N	online	\N	\N	11.7	70.8	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 7.5, "adspower_ram_mb": 595.32, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 4.31, "download_speed_kbps": 5.2, "session_sent_mb": 2.049, "session_received_mb": 6.9, "session_total_mb": 8.949}, "system": {"cpu_percent": 11.7, "ram_percent": 70.8, "ram_used_mb": 7922.7, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:58:02.477285+00
275	1	t	\N	online	\N	\N	22.6	72.3	39.4	1	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 9.8, "adspower_ram_mb": 536.16, "active_browsers_count": 1, "active_sessions": [3], "network": {"upload_speed_kbps": 8.76, "download_speed_kbps": 14.21, "session_sent_mb": 0.654, "session_received_mb": 2.129, "session_total_mb": 2.783}, "system": {"cpu_percent": 22.6, "ram_percent": 72.3, "ram_used_mb": 8081.4, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:55:58.77667+00
281	1	t	\N	online	\N	\N	42.5	71.1	39.4	1	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 9.9, "adspower_ram_mb": 566.0, "active_browsers_count": 1, "active_sessions": [3], "network": {"upload_speed_kbps": 20.0, "download_speed_kbps": 173.98, "session_sent_mb": 1.424, "session_received_mb": 4.76, "session_total_mb": 6.185}, "system": {"cpu_percent": 42.5, "ram_percent": 71.1, "ram_used_mb": 7904.1, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:57:00.886767+00
285	1	t	\N	online	\N	\N	9.9	69.3	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 12.1, "adspower_ram_mb": 594.33, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 5.13, "download_speed_kbps": 4.58, "session_sent_mb": 1.952, "session_received_mb": 6.787, "session_total_mb": 8.739}, "system": {"cpu_percent": 9.9, "ram_percent": 69.3, "ram_used_mb": 7629.6, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:57:42.059587+00
291	1	t	\N	online	\N	\N	9.1	69.8	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 5.6, "adspower_ram_mb": 597.53, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 4.51, "download_speed_kbps": 5.31, "session_sent_mb": 2.311, "session_received_mb": 7.251, "session_total_mb": 9.562}, "system": {"cpu_percent": 9.1, "ram_percent": 69.8, "ram_used_mb": 7808.2, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:58:43.3483+00
288	1	t	\N	online	\N	\N	19	70.1	39.4	0	{"computer_id": 1, "adspower_running": true, "adspower_cpu_percent": 14.2, "adspower_ram_mb": 596.02, "active_browsers_count": 0, "active_sessions": [], "network": {"upload_speed_kbps": 4.34, "download_speed_kbps": 10.68, "session_sent_mb": 2.093, "session_received_mb": 7.007, "session_total_mb": 9.099}, "system": {"cpu_percent": 19.0, "ram_percent": 70.1, "ram_used_mb": 7809.8, "ram_total_mb": 16384.0, "disk_percent": 39.4}}	[]	2026-03-30 14:58:12.729509+00
\.


--
-- TOC entry 3644 (class 0 OID 16634)
-- Dependencies: 237
-- Data for Name: profile_assignments; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.profile_assignments (id, profile_id, agent_id, target_url, assignment_name, is_active, requires_auth, notes, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 3642 (class 0 OID 16610)
-- Dependencies: 235
-- Data for Name: profile_metrics; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.profile_metrics (id, profile_id, proxy_id, proxy_latency_ms, proxy_country, proxy_city, proxy_session_id, creation_duration_seconds, creation_success, device_type, device_brand, device_os, adspower_response_time_ms, cookies_count, created_at) FROM stdin;
\.


--
-- TOC entry 3632 (class 0 OID 16520)
-- Dependencies: 225
-- Data for Name: profiles; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.profiles (id, adspower_id, proxy_id, name, age, gender, country, city, timezone, language, device_type, device_name, os, user_agent, screen_resolution, viewport, pixel_ratio, hardware_concurrency, device_memory, platform, owner, bookie, sport, rotation_minutes, browser_score, fingerprint_score, cookie_status, health_score, trust_score, last_action, memory_mb, warmup_urls, interests, browsing_history, status, is_warmed, warmup_completed_at, last_opened_at, total_sessions, total_duration_seconds, tags, meta_data, notes, created_at, updated_at) FROM stdin;
3	pending-470b5c4fc1	3	OmarNuevo2	\N	\N	ES	\N	Europe/Madrid	es-ES	DESKTOP	MacBook Pro 14-inch (M3)	Windows	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36	3024x1964	1512x982	2	12	16	MacIntel	FInal	Bet365	Fútbol	30	0	0	MISSING	100	100	CREATE	0	["https://www.google.com", "https://www.youtube.com"]	["food", "entertainment", "anime", "streetwear", "golf", "nutrition", "books", "football"]	[]	CREATING	f	\N	\N	0	0	[]	{"auto_fingerprint": true, "open_on_create": false}	\N	2026-03-30 14:16:02.049205+00	2026-03-30 14:16:02.056441+00
1	k1ay9rb9	1	NuevoPerfil	\N	\N	EC	quito	America/Guayaquil	es-EC	DESKTOP	MacBook Air 15-inch (M2)	Windows	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36	2880x1864	1440x932	2	8	16	MacIntel	Final	Bet365	Fútbol	30	0	0	OK	100	100	OPEN	0	["https://www.google.com", "https://www.youtube.com"]	["photography", "physics", "online_shopping", "space", "tennis"]	[]	READY	f	\N	2026-03-30 14:17:25.126782+00	1	11	[]	{"auto_fingerprint": true, "open_on_create": false}	\N	2026-03-30 14:13:59.211329+00	2026-03-30 14:18:06.949611+00
2	k1ay9smc	2	OmarNuevo	\N	\N	EC	pasaje	America/Guayaquil	es-EC	TABLET	iPad Pro 11-inch	Android	Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1	1668x2388	834x1194	2	8	8	iPad	Final	Bet365	Fútbol	30	0	0	OK	100	100	OPEN	0	["https://www.google.com", "https://www.youtube.com"]	["movies", "business", "investing", "dogs", "cinema", "online_learning", "pop", "electric_vehicles", "tv_series", "biographies", "machine_learning", "cycling"]	[]	READY	f	\N	2026-03-30 14:55:10.194745+00	1	109	[]	{"auto_fingerprint": true, "open_on_create": false}	\N	2026-03-30 14:15:07.95051+00	2026-03-30 14:57:06.300079+00
\.


--
-- TOC entry 3624 (class 0 OID 16458)
-- Dependencies: 217
-- Data for Name: proxies; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.proxies (id, proxy_type, host, port, username, password, country, region, city, session_id, session_lifetime, sticky_session, status, is_available, last_check_at, last_success_at, success_rate, avg_response_time, total_checks, failed_checks, detected_ip, detected_country, detected_city, detected_isp, profiles_count, last_used_at, tags, meta_data, created_at, updated_at) FROM stdin;
1	RESIDENTIAL	proxy.soax.com	5000	package-291185-country-ec-city-quito-sessionid-d417c63f54a7453a-sessionlength-1800-opt-lookalike	cUohoUq59MXWY6aT	EC	\N	quito	\N	3600	t	ACTIVE	t	\N	\N	100	\N	0	0	\N	\N	\N	\N	0	\N	[]	{}	2026-03-30 14:13:59.1987+00	\N
2	RESIDENTIAL	proxy.soax.com	5000	package-291185-country-ec-city-pasaje-sessionid-8ecc16c128d04c4a-sessionlength-1800-opt-lookalike	cUohoUq59MXWY6aT	EC	\N	pasaje	\N	3600	t	ACTIVE	t	\N	\N	100	\N	0	0	\N	\N	\N	\N	0	\N	[]	{}	2026-03-30 14:15:07.947847+00	\N
3	RESIDENTIAL	proxy.soax.com	5000	package-291185-country-es-sessionid-9df2175240174d4a-sessionlength-1800-opt-lookalike	cUohoUq59MXWY6aT	ES	\N	\N	\N	3600	t	ACTIVE	t	\N	\N	100	\N	0	0	\N	\N	\N	\N	0	\N	[]	{}	2026-03-30 14:16:02.046658+00	\N
\.


--
-- TOC entry 3636 (class 0 OID 16560)
-- Dependencies: 229
-- Data for Name: proxy_health_checks; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.proxy_health_checks (id, proxy_id, status, check_type, latency_ms, download_speed_mbps, upload_speed_mbps, detected_ip, detected_country, detected_city, detected_isp, geo_match, is_available, response_code, error_message, session_id, session_test_result, test_urls, raw_response, checked_at) FROM stdin;
\.


--
-- TOC entry 3648 (class 0 OID 16682)
-- Dependencies: 241
-- Data for Name: proxy_rotation_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.proxy_rotation_logs (id, proxy_id, profile_id, computer_id, old_proxy_display, new_proxy_display, trigger, success, error_message, latency_ms, ip_address, created_at) FROM stdin;
\.


--
-- TOC entry 3638 (class 0 OID 16579)
-- Dependencies: 231
-- Data for Name: proxy_scores; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.proxy_scores (id, proxy_id, overall_score, speed_score, availability_score, geo_accuracy_score, stability_score, total_checks, successful_checks, failed_checks, timeout_checks, avg_latency, min_latency, max_latency, uptime_percentage, geo_mismatch_count, is_blacklisted, blacklist_reason, blacklisted_at, consecutive_failures, last_recovery_attempt, last_check_at, score_updated_at) FROM stdin;
\.


--
-- TOC entry 3640 (class 0 OID 16597)
-- Dependencies: 233
-- Data for Name: proxy_usage_stats; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.proxy_usage_stats (id, proxy_id, total_profiles_created, total_sessions, avg_latency_ms, min_latency_ms, max_latency_ms, success_rate, total_rotations, last_rotation_at, estimated_data_usage_gb, first_used_at, last_used_at, updated_at) FROM stdin;
\.


--
-- TOC entry 3671 (class 0 OID 0)
-- Dependencies: 238
-- Name: agent_sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.agent_sessions_id_seq', 3, true);


--
-- TOC entry 3672 (class 0 OID 0)
-- Dependencies: 218
-- Name: agent_tokens_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.agent_tokens_id_seq', 1, false);


--
-- TOC entry 3673 (class 0 OID 0)
-- Dependencies: 220
-- Name: alerts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.alerts_id_seq', 1, false);


--
-- TOC entry 3674 (class 0 OID 0)
-- Dependencies: 242
-- Name: browser_events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.browser_events_id_seq', 7, true);


--
-- TOC entry 3675 (class 0 OID 0)
-- Dependencies: 222
-- Name: computer_tokens_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.computer_tokens_id_seq', 1, false);


--
-- TOC entry 3676 (class 0 OID 0)
-- Dependencies: 214
-- Name: computers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.computers_id_seq', 1, true);


--
-- TOC entry 3677 (class 0 OID 0)
-- Dependencies: 226
-- Name: health_checks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.health_checks_id_seq', 292, true);


--
-- TOC entry 3678 (class 0 OID 0)
-- Dependencies: 236
-- Name: profile_assignments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.profile_assignments_id_seq', 1, false);


--
-- TOC entry 3679 (class 0 OID 0)
-- Dependencies: 234
-- Name: profile_metrics_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.profile_metrics_id_seq', 1, false);


--
-- TOC entry 3680 (class 0 OID 0)
-- Dependencies: 224
-- Name: profiles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.profiles_id_seq', 3, true);


--
-- TOC entry 3681 (class 0 OID 0)
-- Dependencies: 216
-- Name: proxies_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.proxies_id_seq', 3, true);


--
-- TOC entry 3682 (class 0 OID 0)
-- Dependencies: 228
-- Name: proxy_health_checks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.proxy_health_checks_id_seq', 1, false);


--
-- TOC entry 3683 (class 0 OID 0)
-- Dependencies: 240
-- Name: proxy_rotation_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.proxy_rotation_logs_id_seq', 1, false);


--
-- TOC entry 3684 (class 0 OID 0)
-- Dependencies: 230
-- Name: proxy_scores_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.proxy_scores_id_seq', 1, false);


--
-- TOC entry 3685 (class 0 OID 0)
-- Dependencies: 232
-- Name: proxy_usage_stats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.proxy_usage_stats_id_seq', 1, false);


--
-- TOC entry 3445 (class 2606 OID 16664)
-- Name: agent_sessions agent_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_sessions
    ADD CONSTRAINT agent_sessions_pkey PRIMARY KEY (id);


--
-- TOC entry 3391 (class 2606 OID 16484)
-- Name: agent_tokens agent_tokens_agent_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_tokens
    ADD CONSTRAINT agent_tokens_agent_name_key UNIQUE (agent_name);


--
-- TOC entry 3393 (class 2606 OID 16482)
-- Name: agent_tokens agent_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_tokens
    ADD CONSTRAINT agent_tokens_pkey PRIMARY KEY (id);


--
-- TOC entry 3396 (class 2606 OID 16496)
-- Name: alerts alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_pkey PRIMARY KEY (id);


--
-- TOC entry 3458 (class 2606 OID 16718)
-- Name: browser_events browser_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.browser_events
    ADD CONSTRAINT browser_events_pkey PRIMARY KEY (id);


--
-- TOC entry 3401 (class 2606 OID 16511)
-- Name: computer_tokens computer_tokens_computer_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.computer_tokens
    ADD CONSTRAINT computer_tokens_computer_id_key UNIQUE (computer_id);


--
-- TOC entry 3403 (class 2606 OID 16509)
-- Name: computer_tokens computer_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.computer_tokens
    ADD CONSTRAINT computer_tokens_pkey PRIMARY KEY (id);


--
-- TOC entry 3405 (class 2606 OID 16513)
-- Name: computer_tokens computer_tokens_token_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.computer_tokens
    ADD CONSTRAINT computer_tokens_token_key UNIQUE (token);


--
-- TOC entry 3379 (class 2606 OID 16454)
-- Name: computers computers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.computers
    ADD CONSTRAINT computers_pkey PRIMARY KEY (id);


--
-- TOC entry 3416 (class 2606 OID 16550)
-- Name: health_checks health_checks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.health_checks
    ADD CONSTRAINT health_checks_pkey PRIMARY KEY (id);


--
-- TOC entry 3443 (class 2606 OID 16642)
-- Name: profile_assignments profile_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.profile_assignments
    ADD CONSTRAINT profile_assignments_pkey PRIMARY KEY (id);


--
-- TOC entry 3439 (class 2606 OID 16618)
-- Name: profile_metrics profile_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.profile_metrics
    ADD CONSTRAINT profile_metrics_pkey PRIMARY KEY (id);


--
-- TOC entry 3414 (class 2606 OID 16528)
-- Name: profiles profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.profiles
    ADD CONSTRAINT profiles_pkey PRIMARY KEY (id);


--
-- TOC entry 3387 (class 2606 OID 16466)
-- Name: proxies proxies_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxies
    ADD CONSTRAINT proxies_pkey PRIMARY KEY (id);


--
-- TOC entry 3389 (class 2606 OID 16468)
-- Name: proxies proxies_session_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxies
    ADD CONSTRAINT proxies_session_id_key UNIQUE (session_id);


--
-- TOC entry 3425 (class 2606 OID 16568)
-- Name: proxy_health_checks proxy_health_checks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxy_health_checks
    ADD CONSTRAINT proxy_health_checks_pkey PRIMARY KEY (id);


--
-- TOC entry 3456 (class 2606 OID 16690)
-- Name: proxy_rotation_logs proxy_rotation_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxy_rotation_logs
    ADD CONSTRAINT proxy_rotation_logs_pkey PRIMARY KEY (id);


--
-- TOC entry 3430 (class 2606 OID 16587)
-- Name: proxy_scores proxy_scores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxy_scores
    ADD CONSTRAINT proxy_scores_pkey PRIMARY KEY (id);


--
-- TOC entry 3433 (class 2606 OID 16602)
-- Name: proxy_usage_stats proxy_usage_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxy_usage_stats
    ADD CONSTRAINT proxy_usage_stats_pkey PRIMARY KEY (id);


--
-- TOC entry 3446 (class 1259 OID 16676)
-- Name: ix_agent_sessions_adspower_profile_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_sessions_adspower_profile_id ON public.agent_sessions USING btree (adspower_profile_id);


--
-- TOC entry 3447 (class 1259 OID 16677)
-- Name: ix_agent_sessions_computer_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_sessions_computer_id ON public.agent_sessions USING btree (computer_id);


--
-- TOC entry 3448 (class 1259 OID 16680)
-- Name: ix_agent_sessions_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_sessions_id ON public.agent_sessions USING btree (id);


--
-- TOC entry 3449 (class 1259 OID 16679)
-- Name: ix_agent_sessions_profile_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_sessions_profile_id ON public.agent_sessions USING btree (profile_id);


--
-- TOC entry 3450 (class 1259 OID 16675)
-- Name: ix_agent_sessions_requested_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_sessions_requested_at ON public.agent_sessions USING btree (requested_at);


--
-- TOC entry 3451 (class 1259 OID 16678)
-- Name: ix_agent_sessions_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_sessions_status ON public.agent_sessions USING btree (status);


--
-- TOC entry 3394 (class 1259 OID 16485)
-- Name: ix_agent_tokens_token; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_agent_tokens_token ON public.agent_tokens USING btree (token);


--
-- TOC entry 3397 (class 1259 OID 16498)
-- Name: ix_alerts_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_alerts_created_at ON public.alerts USING btree (created_at);


--
-- TOC entry 3398 (class 1259 OID 16497)
-- Name: ix_alerts_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_alerts_id ON public.alerts USING btree (id);


--
-- TOC entry 3399 (class 1259 OID 16499)
-- Name: ix_alerts_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_alerts_status ON public.alerts USING btree (status);


--
-- TOC entry 3459 (class 1259 OID 16724)
-- Name: ix_browser_events_event_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_browser_events_event_type ON public.browser_events USING btree (event_type);


--
-- TOC entry 3460 (class 1259 OID 16727)
-- Name: ix_browser_events_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_browser_events_id ON public.browser_events USING btree (id);


--
-- TOC entry 3461 (class 1259 OID 16725)
-- Name: ix_browser_events_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_browser_events_session_id ON public.browser_events USING btree (session_id);


--
-- TOC entry 3462 (class 1259 OID 16726)
-- Name: ix_browser_events_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_browser_events_timestamp ON public.browser_events USING btree ("timestamp");


--
-- TOC entry 3380 (class 1259 OID 16455)
-- Name: ix_computers_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_computers_id ON public.computers USING btree (id);


--
-- TOC entry 3381 (class 1259 OID 16456)
-- Name: ix_computers_name; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_computers_name ON public.computers USING btree (name);


--
-- TOC entry 3417 (class 1259 OID 16557)
-- Name: ix_health_checks_checked_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_health_checks_checked_at ON public.health_checks USING btree (checked_at);


--
-- TOC entry 3418 (class 1259 OID 16558)
-- Name: ix_health_checks_computer_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_health_checks_computer_id ON public.health_checks USING btree (computer_id);


--
-- TOC entry 3419 (class 1259 OID 16556)
-- Name: ix_health_checks_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_health_checks_id ON public.health_checks USING btree (id);


--
-- TOC entry 3440 (class 1259 OID 16654)
-- Name: ix_profile_assignments_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_profile_assignments_agent_id ON public.profile_assignments USING btree (agent_id);


--
-- TOC entry 3441 (class 1259 OID 16653)
-- Name: ix_profile_assignments_profile_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_profile_assignments_profile_id ON public.profile_assignments USING btree (profile_id);


--
-- TOC entry 3434 (class 1259 OID 16632)
-- Name: ix_profile_metrics_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_profile_metrics_created_at ON public.profile_metrics USING btree (created_at);


--
-- TOC entry 3435 (class 1259 OID 16631)
-- Name: ix_profile_metrics_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_profile_metrics_id ON public.profile_metrics USING btree (id);


--
-- TOC entry 3436 (class 1259 OID 16630)
-- Name: ix_profile_metrics_profile_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_profile_metrics_profile_id ON public.profile_metrics USING btree (profile_id);


--
-- TOC entry 3437 (class 1259 OID 16629)
-- Name: ix_profile_metrics_proxy_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_profile_metrics_proxy_id ON public.profile_metrics USING btree (proxy_id);


--
-- TOC entry 3406 (class 1259 OID 16534)
-- Name: ix_profiles_adspower_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_profiles_adspower_id ON public.profiles USING btree (adspower_id);


--
-- TOC entry 3407 (class 1259 OID 16535)
-- Name: ix_profiles_bookie; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_profiles_bookie ON public.profiles USING btree (bookie);


--
-- TOC entry 3408 (class 1259 OID 16539)
-- Name: ix_profiles_country; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_profiles_country ON public.profiles USING btree (country);


--
-- TOC entry 3409 (class 1259 OID 16540)
-- Name: ix_profiles_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_profiles_id ON public.profiles USING btree (id);


--
-- TOC entry 3410 (class 1259 OID 16538)
-- Name: ix_profiles_owner; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_profiles_owner ON public.profiles USING btree (owner);


--
-- TOC entry 3411 (class 1259 OID 16537)
-- Name: ix_profiles_proxy_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_profiles_proxy_id ON public.profiles USING btree (proxy_id);


--
-- TOC entry 3412 (class 1259 OID 16536)
-- Name: ix_profiles_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_profiles_status ON public.profiles USING btree (status);


--
-- TOC entry 3382 (class 1259 OID 16470)
-- Name: ix_proxies_country; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proxies_country ON public.proxies USING btree (country);


--
-- TOC entry 3383 (class 1259 OID 16469)
-- Name: ix_proxies_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proxies_id ON public.proxies USING btree (id);


--
-- TOC entry 3384 (class 1259 OID 16472)
-- Name: ix_proxies_proxy_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proxies_proxy_type ON public.proxies USING btree (proxy_type);


--
-- TOC entry 3385 (class 1259 OID 16471)
-- Name: ix_proxies_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proxies_status ON public.proxies USING btree (status);


--
-- TOC entry 3420 (class 1259 OID 16577)
-- Name: ix_proxy_health_checks_checked_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proxy_health_checks_checked_at ON public.proxy_health_checks USING btree (checked_at);


--
-- TOC entry 3421 (class 1259 OID 16575)
-- Name: ix_proxy_health_checks_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proxy_health_checks_id ON public.proxy_health_checks USING btree (id);


--
-- TOC entry 3422 (class 1259 OID 16576)
-- Name: ix_proxy_health_checks_proxy_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proxy_health_checks_proxy_id ON public.proxy_health_checks USING btree (proxy_id);


--
-- TOC entry 3423 (class 1259 OID 16574)
-- Name: ix_proxy_health_checks_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proxy_health_checks_status ON public.proxy_health_checks USING btree (status);


--
-- TOC entry 3452 (class 1259 OID 16708)
-- Name: ix_proxy_rotation_logs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proxy_rotation_logs_created_at ON public.proxy_rotation_logs USING btree (created_at);


--
-- TOC entry 3453 (class 1259 OID 16706)
-- Name: ix_proxy_rotation_logs_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proxy_rotation_logs_id ON public.proxy_rotation_logs USING btree (id);


--
-- TOC entry 3454 (class 1259 OID 16707)
-- Name: ix_proxy_rotation_logs_proxy_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proxy_rotation_logs_proxy_id ON public.proxy_rotation_logs USING btree (proxy_id);


--
-- TOC entry 3426 (class 1259 OID 16595)
-- Name: ix_proxy_scores_is_blacklisted; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proxy_scores_is_blacklisted ON public.proxy_scores USING btree (is_blacklisted);


--
-- TOC entry 3427 (class 1259 OID 16594)
-- Name: ix_proxy_scores_overall_score; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proxy_scores_overall_score ON public.proxy_scores USING btree (overall_score);


--
-- TOC entry 3428 (class 1259 OID 16593)
-- Name: ix_proxy_scores_proxy_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_proxy_scores_proxy_id ON public.proxy_scores USING btree (proxy_id);


--
-- TOC entry 3431 (class 1259 OID 16608)
-- Name: ix_proxy_usage_stats_proxy_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_proxy_usage_stats_proxy_id ON public.proxy_usage_stats USING btree (proxy_id);


--
-- TOC entry 3473 (class 2606 OID 16665)
-- Name: agent_sessions agent_sessions_computer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_sessions
    ADD CONSTRAINT agent_sessions_computer_id_fkey FOREIGN KEY (computer_id) REFERENCES public.computers(id);


--
-- TOC entry 3474 (class 2606 OID 16670)
-- Name: agent_sessions agent_sessions_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_sessions
    ADD CONSTRAINT agent_sessions_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES public.profiles(id);


--
-- TOC entry 3478 (class 2606 OID 16719)
-- Name: browser_events browser_events_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.browser_events
    ADD CONSTRAINT browser_events_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.agent_sessions(id);


--
-- TOC entry 3463 (class 2606 OID 16514)
-- Name: computer_tokens computer_tokens_computer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.computer_tokens
    ADD CONSTRAINT computer_tokens_computer_id_fkey FOREIGN KEY (computer_id) REFERENCES public.computers(id);


--
-- TOC entry 3465 (class 2606 OID 16551)
-- Name: health_checks health_checks_computer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.health_checks
    ADD CONSTRAINT health_checks_computer_id_fkey FOREIGN KEY (computer_id) REFERENCES public.computers(id);


--
-- TOC entry 3471 (class 2606 OID 16648)
-- Name: profile_assignments profile_assignments_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.profile_assignments
    ADD CONSTRAINT profile_assignments_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agent_tokens(id);


--
-- TOC entry 3472 (class 2606 OID 16643)
-- Name: profile_assignments profile_assignments_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.profile_assignments
    ADD CONSTRAINT profile_assignments_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES public.profiles(id);


--
-- TOC entry 3469 (class 2606 OID 16619)
-- Name: profile_metrics profile_metrics_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.profile_metrics
    ADD CONSTRAINT profile_metrics_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES public.profiles(id);


--
-- TOC entry 3470 (class 2606 OID 16624)
-- Name: profile_metrics profile_metrics_proxy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.profile_metrics
    ADD CONSTRAINT profile_metrics_proxy_id_fkey FOREIGN KEY (proxy_id) REFERENCES public.proxies(id);


--
-- TOC entry 3464 (class 2606 OID 16529)
-- Name: profiles profiles_proxy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.profiles
    ADD CONSTRAINT profiles_proxy_id_fkey FOREIGN KEY (proxy_id) REFERENCES public.proxies(id);


--
-- TOC entry 3466 (class 2606 OID 16569)
-- Name: proxy_health_checks proxy_health_checks_proxy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxy_health_checks
    ADD CONSTRAINT proxy_health_checks_proxy_id_fkey FOREIGN KEY (proxy_id) REFERENCES public.proxies(id);


--
-- TOC entry 3475 (class 2606 OID 16701)
-- Name: proxy_rotation_logs proxy_rotation_logs_computer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxy_rotation_logs
    ADD CONSTRAINT proxy_rotation_logs_computer_id_fkey FOREIGN KEY (computer_id) REFERENCES public.computers(id) ON DELETE SET NULL;


--
-- TOC entry 3476 (class 2606 OID 16696)
-- Name: proxy_rotation_logs proxy_rotation_logs_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxy_rotation_logs
    ADD CONSTRAINT proxy_rotation_logs_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES public.profiles(id) ON DELETE SET NULL;


--
-- TOC entry 3477 (class 2606 OID 16691)
-- Name: proxy_rotation_logs proxy_rotation_logs_proxy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxy_rotation_logs
    ADD CONSTRAINT proxy_rotation_logs_proxy_id_fkey FOREIGN KEY (proxy_id) REFERENCES public.proxies(id) ON DELETE SET NULL;


--
-- TOC entry 3467 (class 2606 OID 16588)
-- Name: proxy_scores proxy_scores_proxy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxy_scores
    ADD CONSTRAINT proxy_scores_proxy_id_fkey FOREIGN KEY (proxy_id) REFERENCES public.proxies(id);


--
-- TOC entry 3468 (class 2606 OID 16603)
-- Name: proxy_usage_stats proxy_usage_stats_proxy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proxy_usage_stats
    ADD CONSTRAINT proxy_usage_stats_proxy_id_fkey FOREIGN KEY (proxy_id) REFERENCES public.proxies(id);


-- Completed on 2026-04-14 23:33:13 UTC

--
-- PostgreSQL database dump complete
--

\unrestrict HQ8kUV8GaK0AsBeeXCdebhMq5xSn9jQcwIaY7nPFnT51r3J6MCYbi81Ec9mOJT9

