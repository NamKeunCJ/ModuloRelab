-- This script was generated by the ERD tool in pgAdmin 4.
-- Please log an issue at https://github.com/pgadmin-org/pgadmin4/issues/new/choose if you find any bugs, including reproduction steps.
BEGIN;


CREATE TABLE IF NOT EXISTS public.analisis_demanda
(
    id_adem serial NOT NULL,
    exc_adem double precision,
    con_adem double precision,
    per_adem double precision,
    status boolean NOT NULL DEFAULT true,
    fec_adem date NOT NULL,
    created_at timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_at timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at timestamp without time zone,
    CONSTRAINT analisis_demanda_pkey PRIMARY KEY (id_adem)
);

CREATE TABLE IF NOT EXISTS public.dato_demanda
(
    id_dem serial NOT NULL,
    dat_dem double precision NOT NULL,
    status boolean NOT NULL DEFAULT true,
    created_at timestamp without time zone NOT NULL,
    update_at timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at timestamp without time zone,
    id_usu integer NOT NULL,
    id_adem integer,
    CONSTRAINT dato_demanda_pkey PRIMARY KEY (id_dem)
);

CREATE TABLE IF NOT EXISTS public.dato_irradiancia
(
    id_irr serial NOT NULL,
    prom_irr double precision NOT NULL,
    max_irr double precision NOT NULL,
    status boolean NOT NULL DEFAULT true,
    created_at timestamp without time zone NOT NULL,
    update_at timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at timestamp without time zone,
    ubi_irr character varying(100) COLLATE pg_catalog."default" NOT NULL DEFAULT 'Estación Laboratorio Sede Centro CESMAG'::character varying,
    CONSTRAINT dato_irradiancia_pkey PRIMARY KEY (id_irr),
    CONSTRAINT dato_irradiancia_created_at_key UNIQUE (created_at)
);

CREATE TABLE IF NOT EXISTS public.roles
(
    id_rol serial NOT NULL,
    tip_rol character varying(30) COLLATE pg_catalog."default" NOT NULL,
    status boolean NOT NULL DEFAULT true,
    created_at timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_at timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at timestamp without time zone,
    CONSTRAINT roles_pkey PRIMARY KEY (id_rol)
);

CREATE TABLE IF NOT EXISTS public.usuario
(
    id_usu serial NOT NULL,
    nom_usu character varying(50) COLLATE pg_catalog."default" NOT NULL,
    ape_usu character varying(50) COLLATE pg_catalog."default" NOT NULL,
    cor_usu character varying(100) COLLATE pg_catalog."default" NOT NULL,
    per_usu character varying(15) COLLATE pg_catalog."default" NOT NULL DEFAULT 'Cliente'::character varying,
    doc_usu character varying(10) COLLATE pg_catalog."default" NOT NULL,
    con_usu character varying(35) COLLATE pg_catalog."default" NOT NULL,
    status boolean NOT NULL DEFAULT true,
    created_at timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_at timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at timestamp without time zone,
    id_rol integer NOT NULL DEFAULT 1,
    CONSTRAINT usuario_pkey PRIMARY KEY (id_usu),
    CONSTRAINT usuario_cor_usu_key UNIQUE (cor_usu),
    CONSTRAINT usuario_doc_usu_key UNIQUE (doc_usu)
);

ALTER TABLE IF EXISTS public.dato_demanda
    ADD CONSTRAINT dato_demanda_id_adem_fkey FOREIGN KEY (id_adem)
    REFERENCES public.analisis_demanda (id_adem) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS public.dato_demanda
    ADD CONSTRAINT dato_demanda_id_usu_fkey FOREIGN KEY (id_usu)
    REFERENCES public.usuario (id_usu) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS public.usuario
    ADD CONSTRAINT usuario_id_rol_fkey FOREIGN KEY (id_rol)
    REFERENCES public.roles (id_rol) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;

END;