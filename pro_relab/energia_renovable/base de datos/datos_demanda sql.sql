--Excedente
SELECT DATE(created_at),SUM(dat_dem) FROM dato_demanda GROUP BY DATE(created_at) ORDER BY DATE(created_at);
--Consumo
SELECT DATE(datetime),SUM(total_dem) 
FROM (SELECT to_char(created_at, 'YYYY-MM-DD HH24:00:00') AS datetime, SUM(dat_dem) AS total_dem
	FROM dato_demanda 
	GROUP BY to_char(created_at, 'YYYY-MM-DD HH24:00:00')
	ORDER BY to_char(created_at, 'YYYY-MM-DD HH24:00:00')) AS datos
WHERE total_dem>0 GROUP BY DATE(datetime) ORDER BY DATE(datetime);
--Energia Perdida
SELECT DATE(datetime),SUM(total_dem) 
FROM (SELECT to_char(created_at, 'YYYY-MM-DD HH24:00:00') AS datetime, SUM(dat_dem) AS total_dem
	FROM dato_demanda 
	GROUP BY to_char(created_at, 'YYYY-MM-DD HH24:00:00')
	ORDER BY to_char(created_at, 'YYYY-MM-DD HH24:00:00')) AS datos
WHERE total_dem<0  GROUP BY DATE(datetime) ORDER BY DATE(datetime);

