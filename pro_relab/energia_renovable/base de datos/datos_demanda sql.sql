SELECT to_char(created_at, 'YYYY-MM-DD HH24:00:00') AS datetime, SUM(dat_dem) AS total_dem
	FROM dato_demanda 
	GROUP BY to_char(created_at, 'YYYY-MM-DD HH24:00:00')
	ORDER BY to_char(created_at, 'YYYY-MM-DD HH24:00:00');

--Excedente
SELECT DATE(created_at),SUM(dat_dem) FROM dato_demanda GROUP BY DATE(created_at) ORDER BY DATE(created_at);

--Consumo
SELECT DATE(datetime),SUM(total_dem) 
FROM (SELECT to_char(created_at, 'YYYY-MM-DD HH24:00:00') AS datetime, SUM(dat_dem) AS total_dem
	FROM dato_demanda 
	GROUP BY to_char(created_at, 'YYYY-MM-DD HH24:00:00')
	ORDER BY to_char(created_at, 'YYYY-MM-DD HH24:00:00')) AS datos
WHERE total_dem>=0 GROUP BY DATE(datetime) ORDER BY DATE(datetime);
--Energia Perdida
SELECT DATE(datetime),SUM(total_dem) 
FROM (SELECT to_char(created_at, 'YYYY-MM-DD HH24:00:00') AS datetime, SUM(dat_dem) AS total_dem
	FROM dato_demanda 
	GROUP BY to_char(created_at, 'YYYY-MM-DD HH24:00:00')
	ORDER BY to_char(created_at, 'YYYY-MM-DD HH24:00:00')) AS datos
WHERE total_dem<=0  GROUP BY DATE(datetime) ORDER BY DATE(datetime);


-----------------------------------------------------
--Promedio consumo neto
SELECT 'Promedio consumo neto' as nom_adem, AVG(exc_adem) FROM analisis_demanda WHERE per_adem < -2500 AND per_adem IS NOT NULL;
--Promedio actual neto
SELECT 'Promedio actual neto' as nom_adem, AVG(con_adem) FROM analisis_demanda WHERE per_adem < -2500 AND per_adem IS NOT NULL;
--Energía perdida
SELECT 'Energía perdida' as nom_adem, AVG(per_adem) FROM analisis_demanda WHERE per_adem < -2500 AND per_adem IS NOT NULL;
-- Pagaría a full
SELECT 'Pagaría a full' as nom_adem, AVG(con_adem) FROM analisis_demanda WHERE per_adem IS NULL;

-----------------------------------------------------
--consumo neto
SELECT 'Consumo neto' as nom_adem, SUM(exc_adem)*1,5 FROM analisis_demanda;
--consumo actual neto
SELECT 'Consumo actual neto' as nom_adem, SUM(con_adem)*1,5 FROM analisis_demanda;
--Energía perdida
SELECT 'Energía perdida' as nom_adem, SUM(per_adem)*1,5 FROM analisis_demanda;
-- Pagaría a full
SELECT 'Pagaría a full' as nom_adem, SUM(con_adem)*10 FROM analisis_demanda WHERE per_adem IS NULL;

---tabla analisis demanda
SELECT fec_adem, exc_adem, con_adem, per_adem FROM analisis_demanda ORDER BY fec_adem ASC;

--MODELO DE PREDICCION
select * from dato_irradiancia where created_at >= '2024-08-13' and created_at < '2024-08-18' order by created_at desc;






