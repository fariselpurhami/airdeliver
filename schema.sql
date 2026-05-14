--
-- PostgreSQL database dump
--

\restrict tKQC92k73qfxqwJeCRU5kygWN60v1b5gCEiqhh3RDdojeB2ROyi3MdUeFdgH7wO

-- Dumped from database version 16.11 (Debian 16.11-1.pgdg12+1)
-- Dumped by pg_dump version 16.11 (Debian 16.11-1.pgdg12+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ai_memory; Type: TABLE; Schema: public; Owner: airdeliver
--

CREATE TABLE public.ai_memory (
    id integer NOT NULL,
    user_id integer NOT NULL,
    context_data json,
    last_updated timestamp without time zone NOT NULL
);


ALTER TABLE public.ai_memory OWNER TO airdeliver;

--
-- Name: ai_memory_id_seq; Type: SEQUENCE; Schema: public; Owner: airdeliver
--

CREATE SEQUENCE public.ai_memory_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ai_memory_id_seq OWNER TO airdeliver;

--
-- Name: ai_memory_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: airdeliver
--

ALTER SEQUENCE public.ai_memory_id_seq OWNED BY public.ai_memory.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: airdeliver
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO airdeliver;

--
-- Name: audit_trails; Type: TABLE; Schema: public; Owner: airdeliver
--

CREATE TABLE public.audit_trails (
    id integer NOT NULL,
    order_id integer NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    event_description character varying NOT NULL,
    changed_by integer
);


ALTER TABLE public.audit_trails OWNER TO airdeliver;

--
-- Name: audit_trails_id_seq; Type: SEQUENCE; Schema: public; Owner: airdeliver
--

CREATE SEQUENCE public.audit_trails_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.audit_trails_id_seq OWNER TO airdeliver;

--
-- Name: audit_trails_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: airdeliver
--

ALTER SEQUENCE public.audit_trails_id_seq OWNED BY public.audit_trails.id;


--
-- Name: badges; Type: TABLE; Schema: public; Owner: airdeliver
--

CREATE TABLE public.badges (
    id integer NOT NULL,
    name character varying NOT NULL,
    description character varying NOT NULL,
    icon_url character varying NOT NULL
);


ALTER TABLE public.badges OWNER TO airdeliver;

--
-- Name: badges_id_seq; Type: SEQUENCE; Schema: public; Owner: airdeliver
--

CREATE SEQUENCE public.badges_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.badges_id_seq OWNER TO airdeliver;

--
-- Name: badges_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: airdeliver
--

ALTER SEQUENCE public.badges_id_seq OWNED BY public.badges.id;


--
-- Name: drone_events; Type: TABLE; Schema: public; Owner: airdeliver
--

CREATE TABLE public.drone_events (
    id integer NOT NULL,
    drone_id integer NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    mission_id_str character varying,
    event_type character varying(17) NOT NULL,
    details json
);


ALTER TABLE public.drone_events OWNER TO airdeliver;

--
-- Name: drone_events_id_seq; Type: SEQUENCE; Schema: public; Owner: airdeliver
--

CREATE SEQUENCE public.drone_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.drone_events_id_seq OWNER TO airdeliver;

--
-- Name: drone_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: airdeliver
--

ALTER SEQUENCE public.drone_events_id_seq OWNED BY public.drone_events.id;


--
-- Name: drone_telemetry; Type: TABLE; Schema: public; Owner: airdeliver
--

CREATE TABLE public.drone_telemetry (
    id integer NOT NULL,
    drone_id integer NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    mission_id_str character varying,
    lat double precision NOT NULL,
    lon double precision NOT NULL,
    alt_m double precision NOT NULL,
    speed_m_s double precision NOT NULL,
    battery_pct integer NOT NULL,
    flight_mode character varying
);


ALTER TABLE public.drone_telemetry OWNER TO airdeliver;

--
-- Name: drone_telemetry_id_seq; Type: SEQUENCE; Schema: public; Owner: airdeliver
--

CREATE SEQUENCE public.drone_telemetry_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.drone_telemetry_id_seq OWNER TO airdeliver;

--
-- Name: drone_telemetry_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: airdeliver
--

ALTER SEQUENCE public.drone_telemetry_id_seq OWNED BY public.drone_telemetry.id;


--
-- Name: drones; Type: TABLE; Schema: public; Owner: airdeliver
--

CREATE TABLE public.drones (
    id integer NOT NULL,
    drone_id_str character varying NOT NULL,
    model character varying,
    home_base_lat double precision,
    home_base_lon double precision,
    meta json,
    status character varying(11) NOT NULL,
    current_battery_pct integer,
    last_seen timestamp without time zone,
    current_lat double precision,
    current_lon double precision
);


ALTER TABLE public.drones OWNER TO airdeliver;

--
-- Name: drones_id_seq; Type: SEQUENCE; Schema: public; Owner: airdeliver
--

CREATE SEQUENCE public.drones_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.drones_id_seq OWNER TO airdeliver;

--
-- Name: drones_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: airdeliver
--

ALTER SEQUENCE public.drones_id_seq OWNED BY public.drones.id;


--
-- Name: missions; Type: TABLE; Schema: public; Owner: airdeliver
--

CREATE TABLE public.missions (
    id integer NOT NULL,
    mission_id_str character varying NOT NULL,
    order_id integer NOT NULL,
    assigned_drone_id integer,
    status character varying(24) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    failure_reason character varying,
    waypoints json
);


ALTER TABLE public.missions OWNER TO airdeliver;

--
-- Name: missions_id_seq; Type: SEQUENCE; Schema: public; Owner: airdeliver
--

CREATE SEQUENCE public.missions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.missions_id_seq OWNER TO airdeliver;

--
-- Name: missions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: airdeliver
--

ALTER SEQUENCE public.missions_id_seq OWNED BY public.missions.id;


--
-- Name: notification_subscriptions; Type: TABLE; Schema: public; Owner: airdeliver
--

CREATE TABLE public.notification_subscriptions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    subscription_info_json json
);


ALTER TABLE public.notification_subscriptions OWNER TO airdeliver;

--
-- Name: notification_subscriptions_id_seq; Type: SEQUENCE; Schema: public; Owner: airdeliver
--

CREATE SEQUENCE public.notification_subscriptions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notification_subscriptions_id_seq OWNER TO airdeliver;

--
-- Name: notification_subscriptions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: airdeliver
--

ALTER SEQUENCE public.notification_subscriptions_id_seq OWNED BY public.notification_subscriptions.id;


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: airdeliver
--

CREATE TABLE public.notifications (
    title character varying NOT NULL,
    body character varying NOT NULL,
    type character varying(12) NOT NULL,
    read boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    id integer NOT NULL,
    user_id integer NOT NULL,
    related_order_id integer,
    related_drone_id integer,
    meta json
);


ALTER TABLE public.notifications OWNER TO airdeliver;

--
-- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: airdeliver
--

CREATE SEQUENCE public.notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notifications_id_seq OWNER TO airdeliver;

--
-- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: airdeliver
--

ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


--
-- Name: order_items; Type: TABLE; Schema: public; Owner: airdeliver
--

CREATE TABLE public.order_items (
    id integer NOT NULL,
    order_id integer NOT NULL,
    product_id integer NOT NULL,
    quantity integer NOT NULL,
    price_per_unit double precision NOT NULL
);


ALTER TABLE public.order_items OWNER TO airdeliver;

--
-- Name: order_items_id_seq; Type: SEQUENCE; Schema: public; Owner: airdeliver
--

CREATE SEQUENCE public.order_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.order_items_id_seq OWNER TO airdeliver;

--
-- Name: order_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: airdeliver
--

ALTER SEQUENCE public.order_items_id_seq OWNED BY public.order_items.id;


--
-- Name: orders; Type: TABLE; Schema: public; Owner: airdeliver
--

CREATE TABLE public.orders (
    id integer NOT NULL,
    user_id integer NOT NULL,
    status character varying(15) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    delivery_address character varying NOT NULL,
    delivery_lat double precision NOT NULL,
    delivery_lon double precision NOT NULL,
    drone_id integer,
    cancellation_reason character varying(14),
    recovery_token character varying,
    total_price double precision NOT NULL,
    is_paid boolean NOT NULL,
    paid_at timestamp without time zone,
    stripe_payment_id character varying
);


ALTER TABLE public.orders OWNER TO airdeliver;

--
-- Name: orders_id_seq; Type: SEQUENCE; Schema: public; Owner: airdeliver
--

CREATE SEQUENCE public.orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.orders_id_seq OWNER TO airdeliver;

--
-- Name: orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: airdeliver
--

ALTER SEQUENCE public.orders_id_seq OWNED BY public.orders.id;


--
-- Name: products; Type: TABLE; Schema: public; Owner: airdeliver
--

CREATE TABLE public.products (
    id integer NOT NULL,
    name character varying NOT NULL,
    description character varying NOT NULL,
    price numeric(10,2) NOT NULL,
    inventory integer NOT NULL,
    category character varying NOT NULL,
    tags json NOT NULL,
    rating double precision,
    sku character varying NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    image character varying(1024),
    currency character varying(10) NOT NULL
);


ALTER TABLE public.products OWNER TO airdeliver;

--
-- Name: products_id_seq; Type: SEQUENCE; Schema: public; Owner: airdeliver
--

CREATE SEQUENCE public.products_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.products_id_seq OWNER TO airdeliver;

--
-- Name: products_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: airdeliver
--

ALTER SEQUENCE public.products_id_seq OWNED BY public.products.id;


--
-- Name: user_activities; Type: TABLE; Schema: public; Owner: airdeliver
--

CREATE TABLE public.user_activities (
    id integer NOT NULL,
    user_id integer NOT NULL,
    activity_type character varying NOT NULL,
    points_awarded integer NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.user_activities OWNER TO airdeliver;

--
-- Name: user_activities_id_seq; Type: SEQUENCE; Schema: public; Owner: airdeliver
--

CREATE SEQUENCE public.user_activities_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_activities_id_seq OWNER TO airdeliver;

--
-- Name: user_activities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: airdeliver
--

ALTER SEQUENCE public.user_activities_id_seq OWNED BY public.user_activities.id;


--
-- Name: user_badges; Type: TABLE; Schema: public; Owner: airdeliver
--

CREATE TABLE public.user_badges (
    user_id integer NOT NULL,
    badge_id integer NOT NULL,
    awarded_at timestamp without time zone NOT NULL
);


ALTER TABLE public.user_badges OWNER TO airdeliver;

--
-- Name: users; Type: TABLE; Schema: public; Owner: airdeliver
--

CREATE TABLE public.users (
    id integer NOT NULL,
    full_name character varying,
    email character varying NOT NULL,
    hashed_password character varying NOT NULL,
    is_active boolean NOT NULL,
    role character varying(8) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    phone_number character varying,
    address character varying,
    city character varying,
    country character varying,
    avatar_url character varying,
    stripe_customer_id character varying,
    is_verified boolean NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    last_login timestamp without time zone
);


ALTER TABLE public.users OWNER TO airdeliver;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: airdeliver
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO airdeliver;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: airdeliver
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: ai_memory id; Type: DEFAULT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.ai_memory ALTER COLUMN id SET DEFAULT nextval('public.ai_memory_id_seq'::regclass);


--
-- Name: audit_trails id; Type: DEFAULT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.audit_trails ALTER COLUMN id SET DEFAULT nextval('public.audit_trails_id_seq'::regclass);


--
-- Name: badges id; Type: DEFAULT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.badges ALTER COLUMN id SET DEFAULT nextval('public.badges_id_seq'::regclass);


--
-- Name: drone_events id; Type: DEFAULT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.drone_events ALTER COLUMN id SET DEFAULT nextval('public.drone_events_id_seq'::regclass);


--
-- Name: drone_telemetry id; Type: DEFAULT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.drone_telemetry ALTER COLUMN id SET DEFAULT nextval('public.drone_telemetry_id_seq'::regclass);


--
-- Name: drones id; Type: DEFAULT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.drones ALTER COLUMN id SET DEFAULT nextval('public.drones_id_seq'::regclass);


--
-- Name: missions id; Type: DEFAULT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.missions ALTER COLUMN id SET DEFAULT nextval('public.missions_id_seq'::regclass);


--
-- Name: notification_subscriptions id; Type: DEFAULT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.notification_subscriptions ALTER COLUMN id SET DEFAULT nextval('public.notification_subscriptions_id_seq'::regclass);


--
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


--
-- Name: order_items id; Type: DEFAULT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.order_items ALTER COLUMN id SET DEFAULT nextval('public.order_items_id_seq'::regclass);


--
-- Name: orders id; Type: DEFAULT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.orders ALTER COLUMN id SET DEFAULT nextval('public.orders_id_seq'::regclass);


--
-- Name: products id; Type: DEFAULT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.products ALTER COLUMN id SET DEFAULT nextval('public.products_id_seq'::regclass);


--
-- Name: user_activities id; Type: DEFAULT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.user_activities ALTER COLUMN id SET DEFAULT nextval('public.user_activities_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: ai_memory ai_memory_pkey; Type: CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.ai_memory
    ADD CONSTRAINT ai_memory_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: audit_trails audit_trails_pkey; Type: CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.audit_trails
    ADD CONSTRAINT audit_trails_pkey PRIMARY KEY (id);


--
-- Name: badges badges_pkey; Type: CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.badges
    ADD CONSTRAINT badges_pkey PRIMARY KEY (id);


--
-- Name: drone_events drone_events_pkey; Type: CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.drone_events
    ADD CONSTRAINT drone_events_pkey PRIMARY KEY (id);


--
-- Name: drone_telemetry drone_telemetry_pkey; Type: CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.drone_telemetry
    ADD CONSTRAINT drone_telemetry_pkey PRIMARY KEY (id);


--
-- Name: drones drones_pkey; Type: CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.drones
    ADD CONSTRAINT drones_pkey PRIMARY KEY (id);


--
-- Name: missions missions_order_id_key; Type: CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.missions
    ADD CONSTRAINT missions_order_id_key UNIQUE (order_id);


--
-- Name: missions missions_pkey; Type: CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.missions
    ADD CONSTRAINT missions_pkey PRIMARY KEY (id);


--
-- Name: notification_subscriptions notification_subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.notification_subscriptions
    ADD CONSTRAINT notification_subscriptions_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: order_items order_items_pkey; Type: CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_pkey PRIMARY KEY (id);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: user_activities user_activities_pkey; Type: CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.user_activities
    ADD CONSTRAINT user_activities_pkey PRIMARY KEY (id);


--
-- Name: user_badges user_badges_pkey; Type: CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.user_badges
    ADD CONSTRAINT user_badges_pkey PRIMARY KEY (user_id, badge_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_ai_memory_user_id; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE UNIQUE INDEX ix_ai_memory_user_id ON public.ai_memory USING btree (user_id);


--
-- Name: ix_audit_trails_order_id; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_audit_trails_order_id ON public.audit_trails USING btree (order_id);


--
-- Name: ix_badges_name; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE UNIQUE INDEX ix_badges_name ON public.badges USING btree (name);


--
-- Name: ix_drone_events_drone_id; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_drone_events_drone_id ON public.drone_events USING btree (drone_id);


--
-- Name: ix_drone_events_mission_id_str; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_drone_events_mission_id_str ON public.drone_events USING btree (mission_id_str);


--
-- Name: ix_drone_events_timestamp; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_drone_events_timestamp ON public.drone_events USING btree ("timestamp");


--
-- Name: ix_drone_telemetry_drone_id; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_drone_telemetry_drone_id ON public.drone_telemetry USING btree (drone_id);


--
-- Name: ix_drone_telemetry_mission_id_str; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_drone_telemetry_mission_id_str ON public.drone_telemetry USING btree (mission_id_str);


--
-- Name: ix_drone_telemetry_timestamp; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_drone_telemetry_timestamp ON public.drone_telemetry USING btree ("timestamp");


--
-- Name: ix_drones_drone_id_str; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE UNIQUE INDEX ix_drones_drone_id_str ON public.drones USING btree (drone_id_str);


--
-- Name: ix_drones_status; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_drones_status ON public.drones USING btree (status);


--
-- Name: ix_missions_assigned_drone_id; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_missions_assigned_drone_id ON public.missions USING btree (assigned_drone_id);


--
-- Name: ix_missions_mission_id_str; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE UNIQUE INDEX ix_missions_mission_id_str ON public.missions USING btree (mission_id_str);


--
-- Name: ix_missions_status; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_missions_status ON public.missions USING btree (status);


--
-- Name: ix_notification_subscriptions_user_id; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE UNIQUE INDEX ix_notification_subscriptions_user_id ON public.notification_subscriptions USING btree (user_id);


--
-- Name: ix_notifications_title; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_notifications_title ON public.notifications USING btree (title);


--
-- Name: ix_notifications_user_id; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_notifications_user_id ON public.notifications USING btree (user_id);


--
-- Name: ix_notifications_user_read_created; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_notifications_user_read_created ON public.notifications USING btree (user_id, read, created_at);


--
-- Name: ix_order_items_order_id; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_order_items_order_id ON public.order_items USING btree (order_id);


--
-- Name: ix_order_items_product_id; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_order_items_product_id ON public.order_items USING btree (product_id);


--
-- Name: ix_orders_drone_id; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_orders_drone_id ON public.orders USING btree (drone_id);


--
-- Name: ix_orders_recovery_token; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_orders_recovery_token ON public.orders USING btree (recovery_token);


--
-- Name: ix_orders_status; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_orders_status ON public.orders USING btree (status);


--
-- Name: ix_orders_user_id; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_orders_user_id ON public.orders USING btree (user_id);


--
-- Name: ix_products_category; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_products_category ON public.products USING btree (category);


--
-- Name: ix_products_is_active; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_products_is_active ON public.products USING btree (is_active);


--
-- Name: ix_products_name; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_products_name ON public.products USING btree (name);


--
-- Name: ix_products_rating; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_products_rating ON public.products USING btree (rating);


--
-- Name: ix_products_sku; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE UNIQUE INDEX ix_products_sku ON public.products USING btree (sku);


--
-- Name: ix_user_activities_activity_type; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_user_activities_activity_type ON public.user_activities USING btree (activity_type);


--
-- Name: ix_user_activities_user_id; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_user_activities_user_id ON public.user_activities USING btree (user_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_full_name; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_users_full_name ON public.users USING btree (full_name);


--
-- Name: ix_users_phone_number; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_users_phone_number ON public.users USING btree (phone_number);


--
-- Name: ix_users_role; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_users_role ON public.users USING btree (role);


--
-- Name: ix_users_stripe_customer_id; Type: INDEX; Schema: public; Owner: airdeliver
--

CREATE INDEX ix_users_stripe_customer_id ON public.users USING btree (stripe_customer_id);


--
-- Name: ai_memory ai_memory_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.ai_memory
    ADD CONSTRAINT ai_memory_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: audit_trails audit_trails_changed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.audit_trails
    ADD CONSTRAINT audit_trails_changed_by_fkey FOREIGN KEY (changed_by) REFERENCES public.users(id);


--
-- Name: audit_trails audit_trails_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.audit_trails
    ADD CONSTRAINT audit_trails_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id);


--
-- Name: drone_events drone_events_drone_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.drone_events
    ADD CONSTRAINT drone_events_drone_id_fkey FOREIGN KEY (drone_id) REFERENCES public.drones(id);


--
-- Name: drone_telemetry drone_telemetry_drone_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.drone_telemetry
    ADD CONSTRAINT drone_telemetry_drone_id_fkey FOREIGN KEY (drone_id) REFERENCES public.drones(id);


--
-- Name: missions missions_assigned_drone_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.missions
    ADD CONSTRAINT missions_assigned_drone_id_fkey FOREIGN KEY (assigned_drone_id) REFERENCES public.drones(id);


--
-- Name: missions missions_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.missions
    ADD CONSTRAINT missions_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id);


--
-- Name: notification_subscriptions notification_subscriptions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.notification_subscriptions
    ADD CONSTRAINT notification_subscriptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: notifications notifications_related_drone_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_related_drone_id_fkey FOREIGN KEY (related_drone_id) REFERENCES public.drones(id);


--
-- Name: notifications notifications_related_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_related_order_id_fkey FOREIGN KEY (related_order_id) REFERENCES public.orders(id);


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: order_items order_items_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id);


--
-- Name: order_items order_items_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: orders orders_drone_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_drone_id_fkey FOREIGN KEY (drone_id) REFERENCES public.drones(id);


--
-- Name: orders orders_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_activities user_activities_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.user_activities
    ADD CONSTRAINT user_activities_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_badges user_badges_badge_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.user_badges
    ADD CONSTRAINT user_badges_badge_id_fkey FOREIGN KEY (badge_id) REFERENCES public.badges(id);


--
-- Name: user_badges user_badges_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: airdeliver
--

ALTER TABLE ONLY public.user_badges
    ADD CONSTRAINT user_badges_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--

\unrestrict tKQC92k73qfxqwJeCRU5kygWN60v1b5gCEiqhh3RDdojeB2ROyi3MdUeFdgH7wO

