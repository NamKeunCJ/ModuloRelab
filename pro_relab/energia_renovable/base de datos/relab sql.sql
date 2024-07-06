CREATE TABLE roles (
    id_rol SERIAL PRIMARY KEY, -- identificador rol
    tip_rol VARCHAR(30) NOT NULL, -- tipo de rol Estudiante, Docente, Egresados, Administrativos
    status BOOLEAN NOT NULL DEFAULT true, -- estado del rol
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, -- fecha de la creacion del rol
    update_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, -- fecha de actualizacion del rol
    deleted_at TIMESTAMP NULL -- fecha de eliminacion del rol
);
-- Insertar tipos de roles
INSERT INTO roles (tip_rol) VALUES
('Estudiante'),('Docente'),('Egresado'),('Administrativo');

CREATE TABLE usuario (
    id_usu SERIAL PRIMARY KEY, -- identificador usuario
    nom_usu VARCHAR(50) NOT NULL, -- nombre del usuario
    ape_usu VARCHAR(50) NOT NULL, -- apellido del usuario 
    cor_usu VARCHAR(100) UNIQUE NOT NULL, -- correo del usuario
    per_usu VARCHAR(15) NOT NULL DEFAULT 'Cliente', -- perfil del usuario Cliente - Administrador
    doc_usu VARCHAR(10) UNIQUE NOT NULL, -- documento del usuario
    con_usu VARCHAR(35) NOT NULL, -- contraseña del usuario
    status BOOLEAN NOT NULL DEFAULT true, -- estado del usuario
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, -- fecha de creacion del usuario
    update_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, -- fecha de actualizacion de datos
    deleted_at TIMESTAMP NULL, -- fecha en la cual fue eliminado el usuario
    id_rol INTEGER REFERENCES roles(id_rol) NOT NULL DEFAULT 1 -- id del rol al que corresponde
);

CREATE TABLE dato_demanda(
    id_dem SERIAL PRIMARY KEY, -- identificador demanda
    dat_dem FLOAT NOT NULL, -- dato demanda
    status BOOLEAN NOT NULL DEFAULT true, -- estado del dato
    created_at TIMESTAMP NOT NULL, -- fecha que se creo el dato en el Hioki
    update_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, -- fecha en la que se actualizo el dato en la base de datos
    deleted_at TIMESTAMP NULL, -- fecha en la cual se elimino el dato
    id_usu INTEGER REFERENCES usuario(id_usu) NOT NULL -- 1 usuario varios datos
);

CREATE TABLE dato_irradiancia(
    id_irr SERIAL PRIMARY KEY, -- identificador
    prom_irr FLOAT NOT NULL, -- promedio irradiancia
    max_irr FLOAT NOT NULL, -- maxima irradiancia
    status BOOLEAN NOT NULL DEFAULT true, -- estado del dato
    created_at TIMESTAMP NOT NULL, -- fecha que se creo el dato en estacion meteorologica
    update_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, -- fecha en la que se actualizo el dato en la base de datos
    deleted_at TIMESTAMP NULL, -- fecha en la cual se elimino el dato
    id_usu INTEGER REFERENCES usuario(id_usu) NOT NULL -- 1 usuario varios datos
);

delete from dato_irradiancia;
SELECT setval(pg_get_serial_sequence('dato_irradiancia', 'id_irr'), 1, false);