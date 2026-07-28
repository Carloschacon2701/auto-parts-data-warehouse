-- El pipeline reconstruye core por completo en cada ejecución (todos los archivos
-- hacen DROP + CREATE + INSERT). Se recrea el esquema entero para que la corrida
-- sea idempotente: si solo se hiciera DROP TABLE, las dimensiones no podrían
-- borrarse mientras las tablas de hechos mantengan sus claves foráneas.
DROP SCHEMA IF EXISTS core CASCADE;
CREATE SCHEMA core;
