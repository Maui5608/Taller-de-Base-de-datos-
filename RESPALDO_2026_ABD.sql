-- --------------------------------------------------------
-- Host:                         127.0.0.1
-- Versión del servidor:         12.2.2-MariaDB - MariaDB Server
-- SO del servidor:              Win64
-- HeidiSQL Versión:             12.14.0.7165
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


-- Volcando estructura de base de datos para proyecto_smorgas
CREATE DATABASE IF NOT EXISTS `proyecto_smorgas` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */;
USE `proyecto_smorgas`;

-- Volcando estructura para tabla proyecto_smorgas.tbl_compra
CREATE TABLE IF NOT EXISTS `tbl_compra` (
  `Folio` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `Importe_Total` decimal(12,2) NOT NULL DEFAULT 0.00,
  `Cantidad_Total` int(10) unsigned NOT NULL DEFAULT 0,
  `Hora` datetime NOT NULL,
  `ID_Modo_Entrega` int(10) unsigned NOT NULL,
  `ID_Fecha` int(10) unsigned NOT NULL,
  `ID_Mesa` int(10) unsigned NOT NULL,
  PRIMARY KEY (`Folio`),
  KEY `idx_compra_modo` (`ID_Modo_Entrega`),
  KEY `idx_compra_fecha` (`ID_Fecha`),
  KEY `idx_compra_mesa` (`ID_Mesa`),
  CONSTRAINT `fk_compra_fecha` FOREIGN KEY (`ID_Fecha`) REFERENCES `tbl_fecha` (`ID_Fecha`),
  CONSTRAINT `fk_compra_mesa` FOREIGN KEY (`ID_Mesa`) REFERENCES `tbl_mesa` (`ID_Mesa`),
  CONSTRAINT `fk_compra_modo` FOREIGN KEY (`ID_Modo_Entrega`) REFERENCES `tbl_modo_entrega` (`ID_Modo_Entrega`)
) ENGINE=InnoDB AUTO_INCREMENT=33 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla proyecto_smorgas.tbl_compra: ~11 rows (aproximadamente)
INSERT INTO `tbl_compra` (`Folio`, `Importe_Total`, `Cantidad_Total`, `Hora`, `ID_Modo_Entrega`, `ID_Fecha`, `ID_Mesa`) VALUES
	(1, 64.08, 6, '2025-11-12 08:00:00', 2, 1, 101),
	(5, 100.86, 1, '2025-11-12 08:00:00', 1, 1, 107),
	(6, 900.00, 12, '2025-11-12 08:00:00', 1, 1, 105),
	(7, 20.00, 1, '2025-11-12 08:00:00', 2, 1, 105),
	(8, 20.00, 1, '2025-11-12 08:00:00', 1, 1, 105),
	(9, 20.00, 1, '2025-11-12 08:00:00', 1, 1, 100),
	(25, 120.00, 6, '2025-11-12 08:00:00', 1, 1, 104),
	(26, 140.09, 7, '2025-11-26 08:00:00', 1, 2, 100),
	(28, 3004.22, 112, '2025-12-05 08:00:00', 1, 3, 101),
	(31, 20.00, 1, '2026-03-12 12:09:54', 1, 6, 102),
	(32, 120.00, 1, '2026-03-12 12:12:37', 1, 6, 103);

-- Volcando estructura para tabla proyecto_smorgas.tbl_detalle
CREATE TABLE IF NOT EXISTS `tbl_detalle` (
  `ID_Detalle` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `Folio` int(10) unsigned NOT NULL,
  `ID_Producto` int(10) unsigned NOT NULL,
  `Cantidad` int(10) unsigned NOT NULL DEFAULT 1,
  `Precio_Unit` decimal(10,2) NOT NULL DEFAULT 0.00,
  `Subtotal` decimal(12,2) NOT NULL DEFAULT 0.00,
  PRIMARY KEY (`ID_Detalle`),
  KEY `idx_detalle_folio` (`Folio`),
  KEY `idx_detalle_producto` (`ID_Producto`),
  CONSTRAINT `fk_detalle_compra` FOREIGN KEY (`Folio`) REFERENCES `tbl_compra` (`Folio`) ON DELETE CASCADE,
  CONSTRAINT `fk_detalle_producto` FOREIGN KEY (`ID_Producto`) REFERENCES `tbl_producto` (`ID_Producto`)
) ENGINE=InnoDB AUTO_INCREMENT=53 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla proyecto_smorgas.tbl_detalle: ~19 rows (aproximadamente)
INSERT INTO `tbl_detalle` (`ID_Detalle`, `Folio`, `ID_Producto`, `Cantidad`, `Precio_Unit`, `Subtotal`) VALUES
	(1, 1, 1030, 6, 10.68, 64.08),
	(8, 5, 1013, 1, 100.86, 100.86),
	(9, 6, 1036, 6, 20.00, 0.00),
	(10, 6, 1008, 6, 150.00, 900.00),
	(11, 7, 1030, 1, 20.00, 0.00),
	(12, 8, 1030, 1, 20.00, 0.00),
	(13, 9, 1030, 1, 20.00, 0.00),
	(31, 25, 1029, 4, 20.00, 80.00),
	(32, 25, 1030, 1, 20.00, 20.00),
	(33, 25, 1029, 1, 20.00, 20.00),
	(34, 26, 1030, 1, 20.09, 20.09),
	(35, 26, 1030, 6, 20.00, 120.00),
	(38, 28, 1031, 50, 30.00, 1500.00),
	(39, 28, 1008, 1, 0.01, 0.01),
	(40, 28, 1021, 1, 0.01, 0.01),
	(41, 28, 1014, 10, 0.42, 4.20),
	(42, 28, 1031, 50, 30.00, 1500.00),
	(51, 31, 1030, 1, 20.00, 0.00),
	(52, 32, 1000, 1, 120.00, 0.00);

-- Volcando estructura para tabla proyecto_smorgas.tbl_fecha
CREATE TABLE IF NOT EXISTS `tbl_fecha` (
  `ID_Fecha` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `Dia` tinyint(3) unsigned NOT NULL,
  `Mes` tinyint(3) unsigned NOT NULL,
  `Anio` smallint(5) unsigned NOT NULL,
  PRIMARY KEY (`ID_Fecha`),
  KEY `idx_fecha` (`Anio`,`Mes`,`Dia`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla proyecto_smorgas.tbl_fecha: ~4 rows (aproximadamente)
INSERT INTO `tbl_fecha` (`ID_Fecha`, `Dia`, `Mes`, `Anio`) VALUES
	(1, 12, 11, 2025),
	(2, 26, 11, 2025),
	(3, 5, 12, 2025),
	(6, 12, 3, 2026);

-- Volcando estructura para tabla proyecto_smorgas.tbl_mesa
CREATE TABLE IF NOT EXISTS `tbl_mesa` (
  `ID_Mesa` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `Mesa` varchar(10) NOT NULL,
  PRIMARY KEY (`ID_Mesa`),
  UNIQUE KEY `ux_mesa` (`Mesa`)
) ENGINE=InnoDB AUTO_INCREMENT=109 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla proyecto_smorgas.tbl_mesa: ~9 rows (aproximadamente)
INSERT INTO `tbl_mesa` (`ID_Mesa`, `Mesa`) VALUES
	(100, '100'),
	(101, '101'),
	(102, '102'),
	(103, '103'),
	(104, '104'),
	(105, '105'),
	(106, '106'),
	(107, '107'),
	(108, '108');

-- Volcando estructura para tabla proyecto_smorgas.tbl_modo_entrega
CREATE TABLE IF NOT EXISTS `tbl_modo_entrega` (
  `ID_Modo_Entrega` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `Modo_Entrega` varchar(40) NOT NULL,
  PRIMARY KEY (`ID_Modo_Entrega`),
  UNIQUE KEY `ux_modo` (`Modo_Entrega`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla proyecto_smorgas.tbl_modo_entrega: ~2 rows (aproximadamente)
INSERT INTO `tbl_modo_entrega` (`ID_Modo_Entrega`, `Modo_Entrega`) VALUES
	(1, 'Comedor'),
	(2, 'Llevar');

-- Volcando estructura para tabla proyecto_smorgas.tbl_producto
CREATE TABLE IF NOT EXISTS `tbl_producto` (
  `ID_Producto` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `Nombre_Producto` varchar(120) NOT NULL,
  `Precio_Producto` decimal(10,2) NOT NULL DEFAULT 0.00,
  `Categoria` varchar(120) DEFAULT NULL,
  PRIMARY KEY (`ID_Producto`),
  UNIQUE KEY `ux_producto_nombre` (`Nombre_Producto`)
) ENGINE=InnoDB AUTO_INCREMENT=1037 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla proyecto_smorgas.tbl_producto: ~37 rows (aproximadamente)
INSERT INTO `tbl_producto` (`ID_Producto`, `Nombre_Producto`, `Precio_Producto`, `Categoria`) VALUES
	(1000, 'Huevo smorgas', 120.00, 'Especialidad'),
	(1001, 'Huevos criollos', 120.00, 'Especialidad'),
	(1002, 'Huevos ibericos', 120.00, 'Especialidad'),
	(1003, 'Huevos peninsulares', 120.00, 'Especialidad'),
	(1004, 'Omelette del chef', 120.00, 'Especialidad'),
	(1005, 'Omelette jamon y queso', 110.00, 'Especialidad'),
	(1006, 'Omelette papa y chorizo', 110.00, 'Especialidad'),
	(1007, 'Tortilla española', 120.00, 'Especialidad'),
	(1008, 'Huevos pyttipana', 150.00, 'Especialidad'),
	(1009, 'Huevos al gusto', 100.00, 'Especialidad'),
	(1010, 'Panini', 65.00, 'Sandwiches, Baguettes y Varios'),
	(1011, 'Sandwich pan blanco', 95.00, 'Sandwiches, Baguettes y Varios'),
	(1012, 'Sandwich integral', 100.00, 'Sandwiches, Baguettes y Varios'),
	(1013, 'Baguette', 100.00, 'Sandwiches, Baguettes y Varios'),
	(1014, 'Hotcakes', 90.00, 'Sandwiches, Baguettes y Varios'),
	(1015, 'Ensalada de la casa', 100.00, 'Sandwiches, Baguettes y Varios'),
	(1016, 'Burritas', 100.00, 'Sandwiches, Baguettes y Varios'),
	(1017, 'Burritas smorgas', 120.00, 'Sandwiches, Baguettes y Varios'),
	(1018, 'Paquete 1 desayuno sencillo', 150.00, 'Paquetes'),
	(1019, 'Paquete 2 desayuno completo', 180.00, 'Paquetes'),
	(1020, 'Paquete 3 desayuno sencillo de especialidad', 170.00, 'Paquetes'),
	(1021, 'Paquete 4 desayuno completo de especialidad', 200.00, 'Paquetes'),
	(1022, 'Café tipo veracruz', 40.00, 'Bebidas'),
	(1023, 'Café tipo americano', 40.00, 'Bebidas'),
	(1024, 'Café oscuro', 40.00, 'Bebidas'),
	(1025, 'Café descafeinado', 50.00, 'Bebidas'),
	(1026, 'Café tipo cubano', 60.00, 'Bebidas'),
	(1027, 'Café tipo espresso', 80.00, 'Bebidas'),
	(1028, 'Té', 30.00, 'Bebidas'),
	(1029, 'Agua de sandía', 20.00, 'Bebidas'),
	(1030, 'Agua de melón', 20.00, 'Bebidas'),
	(1031, 'Refresco embotellados', 30.00, 'Bebidas'),
	(1032, 'Vaso de leche', 25.00, 'Bebidas'),
	(1033, 'Vaso de leche c/plátano o chocolate', 30.00, 'Bebidas'),
	(1034, 'Postre del día', 25.00, 'Bebidas'),
	(1035, 'Botella de agua', 10.00, 'Bebidas'),
	(1036, 'Ingrediente extra', 20.00, 'Bebidas');

-- Volcando estructura para tabla proyecto_smorgas.tbl_usuarios
CREATE TABLE IF NOT EXISTS `tbl_usuarios` (
  `ID_Usuario` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `Nombre_Usuario` varchar(50) NOT NULL,
  `Nombre_Usuario_norm` varchar(50) GENERATED ALWAYS AS (lcase(`Nombre_Usuario`)) STORED,
  `Rol_Usuario` varchar(20) NOT NULL,
  `Contrasenia_hash` varchar(255) NOT NULL,
  `Fecha_Creacion` datetime NOT NULL DEFAULT current_timestamp(),
  `Session_Token` varchar(64) DEFAULT NULL,
  `Session_Expira` datetime DEFAULT NULL,
  `Ultimo_Visto` datetime DEFAULT NULL,
  PRIMARY KEY (`ID_Usuario`),
  UNIQUE KEY `ux_usuarios_nombre_norm` (`Nombre_Usuario_norm`),
  KEY `idx_session_token` (`Session_Token`)
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla proyecto_smorgas.tbl_usuarios: ~16 rows (aproximadamente)
INSERT INTO `tbl_usuarios` (`ID_Usuario`, `Nombre_Usuario`, `Rol_Usuario`, `Contrasenia_hash`, `Fecha_Creacion`, `Session_Token`, `Session_Expira`, `Ultimo_Visto`) VALUES
	(1, 'David', 'admin', 'scrypt:32768:8:1$h79DzQeUOmZsTtRH$824965f36dd076eb56db8e34edabc683fdeb89fef96101df14ff56a7b6ba8ad1a8a83a71910a714d890ff2393a6f910b4f4429b55375b80658934d0c9bdf1345', '2025-11-12 08:17:09', 'fa321d3d9a95f14a1ad36346e158c3a5', '2026-03-12 12:55:27', '2026-03-12 12:25:27'),
	(2, 'shirley', 'mesero', 'scrypt:32768:8:1$AntMIuIFRHa9HkLO$4b06af79a513e32f0e9eaebb6595a1638b9843446ad76c54373ac816f82f075df6dc6ec67ad78fa97d1751809e39f27f12efceedd167d65b85905d59e50d663f', '2025-11-12 08:28:02', NULL, NULL, '2025-11-12 08:30:38'),
	(5, 'Shir', 'mesero', 'scrypt:32768:8:1$QcVPsmKDUZXBardX$9920ad005652e850539ffcb6944fc3b91bcb05365bd474591427bcc98ca7b9b0064eb828b921ebae6a2b622b08e7664951da4450360d5d4593bf4aeb8d5046ad', '2025-11-12 08:31:19', NULL, NULL, '2025-11-12 08:35:06'),
	(7, 'LissAd', 'admin', 'scrypt:32768:8:1$YgQgADiC6rWI7pdB$4166dc2dc94cf52b88c128e9c776bd29627de3ab8618aa9c1747185917c44239eeefcd6c0f77add10954601e8c096bb98116f232f1ef615de48ca0f5207ace2c', '2025-11-12 08:35:20', NULL, NULL, '2025-11-12 08:47:04'),
	(10, 'Edelmy', 'mesero', 'scrypt:32768:8:1$6ks4wwRb2IVIDhI7$6035564de1b838b1c9a572a3dc0d58e9f982bf80e2783e5cc38d0ca210f3c3a289a7643a42dcc40f269c8464a6a8c83dd64e6466edf03131dbb37660c190c9d6', '2025-11-12 08:40:15', NULL, NULL, '2025-11-12 08:50:07'),
	(11, 'Israel', 'admin', 'scrypt:32768:8:1$Fjl7mJD3ofTrgIpd$d3c48b0e17d9328fd037d108721563e4b5fd779df69ef534dbe403505fb94505b845d5f7be745fe1186a4ea26784b603bfaa427545a22e3c2199e1e30bcb8b30', '2025-11-12 08:50:01', '871184282f139779fae849611bb4cbd5', '2025-11-12 09:20:43', '2025-11-12 08:50:43'),
	(13, 'Gabriela', 'mesero', 'scrypt:32768:8:1$OI8wC9FUS7V4kWsi$cc9470b662567bcb28fc2b8fb9d2e113ca153479ec8d8ebd3630e21d18b1d8e00aff33d052159b6c9b97948869bb14ae867a922ef6ffb917574f41e7af781026', '2025-12-05 14:00:15', NULL, NULL, '2025-12-05 14:11:30'),
	(14, 'Genesis', 'admin', 'scrypt:32768:8:1$NwM6lJhbMY84r6Hp$fe0b29ecc22923b3400ec25a466a326f4ef4072f6dccba51ea228a5e731081c63cf74eaaf5c532ff505737b0bee609e2eeeb1b43b7f641a927f31c0e9815ecbd', '2025-12-05 14:24:05', NULL, NULL, '2025-12-05 14:49:37'),
	(15, 'Fran', 'mesero', 'scrypt:32768:8:1$ZwwvGb4YLXFavnLw$65cde3ae1136c4a3227b5d3c831f3bfb34b09abebe3cfab8bd344760dc5c44d5f48858ac5525d56b9e810c01241bcad45660c12ce4d69ce4c7f66434c420e8e1', '2025-12-05 14:27:47', NULL, NULL, '2025-12-05 14:44:25'),
	(16, 'Yazmin', 'admin', 'scrypt:32768:8:1$Nx48IYlJqVY1lVVH$25c028efe0f07bf653a26fd386e422eab942536a6d9613bf6eef9a943e7d8e0cc9e6abfe918ae531ad127282d38c31e9095156c6cdb88dacafdf99140722db5c', '2025-12-05 14:50:26', NULL, NULL, '2025-12-05 14:55:25'),
	(17, 'Regina', 'mesero', 'scrypt:32768:8:1$UXdLt1ucTGZabNaj$b19238e70269b5259db1f463295948f45e91c5cb80d550bcc55b116b6f4109b73f84638d618c2f93d42b80c11ba1ecb5dba0858958d42ce218c2fa0438896364', '2025-12-05 14:55:49', NULL, NULL, NULL),
	(19, 'Nancy', 'mesero', 'scrypt:32768:8:1$xCszfbr7FW9gxj2M$9a73dead5d030fa1c967d8fa2aaf51173f762e16e85ded0572c73525a712acdf7232ebaa012bc4e03739134329f19dbc5b763659199b0fb0e700e16d61abb51a', '2025-12-05 14:56:34', NULL, NULL, '2025-12-05 15:00:53'),
	(20, 'keller', 'admin', 'scrypt:32768:8:1$0kiJixdgqLz4uNTQ$562d016694ff43268bee04a4520deffacd17471f03e8d1d45e6b1c520869f8211d7b917d5d31ff9911fee11848eaa40187b136d7358619d516645b620bffa0ba', '2025-12-05 15:03:06', NULL, NULL, '2025-12-05 15:12:46'),
	(21, 'dani', 'admin', 'scrypt:32768:8:1$th9qB3WYbNSre9Zs$944bf82972500ebf8e5831801275afa04c00a3bdf08ccc1749348f4c4f6f945f29ba66112caa1bf8bc9a50c1896df16ef8adf5bcdc5d01559e89c65575367db1', '2025-12-05 15:25:12', '579f1e94b54895ca984824fa8b010f8c', '2025-12-05 15:55:19', '2025-12-05 15:25:19'),
	(22, 'Prueba', 'admin', 'scrypt:32768:8:1$hTwKyoXl685ALatW$673681b28c786966594718ed6467a39f490e88e4fc33ec8fdf0a0065ae1951d41a2ff8a92c0659b3af28613e9ef27ffac7c3fc5e15f41fd24317d8f89e068fcf', '2026-03-12 10:21:10', NULL, NULL, NULL),
	(23, 'INTENTO', 'admin', 'scrypt:32768:8:1$mjFQS6gr7GZFhpOU$1ceca6caa943e96bd31b006226340376da58e30824d1b6ddd962ff806e97980a614f8003b7a38bdb00a363c1eac22bda398827ec2ac177b743eeefb0446e6f2e', '2026-03-12 11:54:10', NULL, NULL, NULL);

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
