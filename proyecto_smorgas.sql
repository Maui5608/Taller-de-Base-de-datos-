-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 30-01-2026 a las 21:44:11
-- Versión del servidor: 10.4.32-MariaDB
-- Versión de PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de datos: `proyecto_smorgas`
--

DELIMITER $$
--
-- Procedimientos
--
CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_obtener_id_fecha` (IN `p_dia` TINYINT UNSIGNED, IN `p_mes` TINYINT UNSIGNED, IN `p_anio` SMALLINT UNSIGNED)   BEGIN
    DECLARE v_id INT;

    SELECT ID_Fecha
      INTO v_id
      FROM tbl_fecha
     WHERE Dia = p_dia
       AND Mes = p_mes
       AND Anio = p_anio;

    IF v_id IS NULL THEN
        INSERT INTO tbl_fecha (Dia, Mes, Anio)
        VALUES (p_dia, p_mes, p_anio);
        SET v_id = LAST_INSERT_ID();
    END IF;

    -- Devolver el valor
    SELECT v_id AS ID_Fecha;
END$$

--
-- Funciones
--
CREATE DEFINER=`root`@`localhost` FUNCTION `fn_modo_entrega_nombre` (`p_id` INT) RETURNS VARCHAR(40) CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci DETERMINISTIC BEGIN
    DECLARE v_nombre VARCHAR(40);

    SELECT Modo_Entrega
      INTO v_nombre
      FROM tbl_modo_entrega
     WHERE ID_Modo_Entrega = p_id;

    RETURN COALESCE(v_nombre, '—');
END$$

DELIMITER ;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `tbl_compra`
--

CREATE TABLE `tbl_compra` (
  `Folio` int(10) UNSIGNED NOT NULL,
  `Importe_Total` decimal(12,2) NOT NULL DEFAULT 0.00,
  `Cantidad_Total` int(10) UNSIGNED NOT NULL DEFAULT 0,
  `Hora` datetime NOT NULL,
  `ID_Modo_Entrega` int(10) UNSIGNED NOT NULL,
  `ID_Fecha` int(10) UNSIGNED NOT NULL,
  `ID_Mesa` int(10) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `tbl_compra`
--

INSERT INTO `tbl_compra` (`Folio`, `Importe_Total`, `Cantidad_Total`, `Hora`, `ID_Modo_Entrega`, `ID_Fecha`, `ID_Mesa`) VALUES
(1, 64.08, 6, '2025-11-12 08:00:00', 2, 1, 101),
(5, 100.86, 1, '2025-11-12 08:00:00', 1, 1, 107),
(6, 900.00, 12, '2025-11-12 08:00:00', 1, 1, 105),
(7, 20.00, 1, '2025-11-12 08:00:00', 2, 1, 105),
(8, 20.00, 1, '2025-11-12 08:00:00', 1, 1, 105),
(9, 20.00, 1, '2025-11-12 08:00:00', 1, 1, 100),
(25, 120.00, 6, '0000-00-00 00:00:00', 1, 1, 104),
(26, 140.09, 7, '0000-00-00 00:00:00', 1, 2, 100),
(28, 3004.22, 112, '0000-00-00 00:00:00', 1, 3, 101),
(30, 1580.00, 10, '0000-00-00 00:00:00', 1, 3, 104);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `tbl_detalle`
--

CREATE TABLE `tbl_detalle` (
  `ID_Detalle` int(10) UNSIGNED NOT NULL,
  `Folio` int(10) UNSIGNED NOT NULL,
  `ID_Producto` int(10) UNSIGNED NOT NULL,
  `Cantidad` int(10) UNSIGNED NOT NULL DEFAULT 1,
  `Precio_Unit` decimal(10,2) NOT NULL DEFAULT 0.00,
  `Subtotal` decimal(12,2) NOT NULL DEFAULT 0.00
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `tbl_detalle`
--

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
(47, 30, 1030, 1, 20.00, 0.00),
(48, 30, 1019, 1, 180.00, 0.00),
(49, 30, 1000, 1, 120.00, 0.00),
(50, 30, 1019, 7, 180.00, 0.00);

--
-- Disparadores `tbl_detalle`
--
DELIMITER $$
CREATE TRIGGER `trg_compra_totales_au` AFTER UPDATE ON `tbl_detalle` FOR EACH ROW BEGIN
    DECLARE v_cant INT;
    DECLARE v_importe DECIMAL(12,2);

    SELECT
        COALESCE(SUM(Cantidad),0),
        COALESCE(SUM(Cantidad * Precio_Unit),0)
    INTO v_cant, v_importe
    FROM tbl_detalle
    WHERE Folio = NEW.Folio;

    UPDATE tbl_compra
    SET Cantidad_Total = v_cant,
        Importe_Total  = v_importe
    WHERE Folio = NEW.Folio;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `tbl_fecha`
--

CREATE TABLE `tbl_fecha` (
  `ID_Fecha` int(10) UNSIGNED NOT NULL,
  `Dia` tinyint(3) UNSIGNED NOT NULL,
  `Mes` tinyint(3) UNSIGNED NOT NULL,
  `Anio` smallint(5) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `tbl_fecha`
--

INSERT INTO `tbl_fecha` (`ID_Fecha`, `Dia`, `Mes`, `Anio`) VALUES
(1, 12, 11, 2025),
(2, 26, 11, 2025),
(3, 5, 12, 2025);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `tbl_mesa`
--

CREATE TABLE `tbl_mesa` (
  `ID_Mesa` int(10) UNSIGNED NOT NULL,
  `Mesa` varchar(10) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `tbl_mesa`
--

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

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `tbl_modo_entrega`
--

CREATE TABLE `tbl_modo_entrega` (
  `ID_Modo_Entrega` int(10) UNSIGNED NOT NULL,
  `Modo_Entrega` varchar(40) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `tbl_modo_entrega`
--

INSERT INTO `tbl_modo_entrega` (`ID_Modo_Entrega`, `Modo_Entrega`) VALUES
(1, 'Comedor'),
(2, 'Llevar');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `tbl_producto`
--

CREATE TABLE `tbl_producto` (
  `ID_Producto` int(10) UNSIGNED NOT NULL,
  `Nombre_Producto` varchar(120) NOT NULL,
  `Precio_Producto` decimal(10,2) NOT NULL DEFAULT 0.00,
  `Categoria` varchar(120) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `tbl_producto`
--

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

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `tbl_usuarios`
--

CREATE TABLE `tbl_usuarios` (
  `ID_Usuario` int(10) UNSIGNED NOT NULL,
  `Nombre_Usuario` varchar(50) NOT NULL,
  `Nombre_Usuario_norm` varchar(50) GENERATED ALWAYS AS (lcase(`Nombre_Usuario`)) STORED,
  `Rol_Usuario` varchar(20) NOT NULL,
  `Contrasenia_hash` varchar(255) NOT NULL,
  `Fecha_Creacion` datetime NOT NULL DEFAULT current_timestamp(),
  `Session_Token` varchar(64) DEFAULT NULL,
  `Session_Expira` datetime DEFAULT NULL,
  `Ultimo_Visto` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `tbl_usuarios`
--

INSERT INTO `tbl_usuarios` (`ID_Usuario`, `Nombre_Usuario`, `Rol_Usuario`, `Contrasenia_hash`, `Fecha_Creacion`, `Session_Token`, `Session_Expira`, `Ultimo_Visto`) VALUES
(1, 'David', 'admin', 'scrypt:32768:8:1$h79DzQeUOmZsTtRH$824965f36dd076eb56db8e34edabc683fdeb89fef96101df14ff56a7b6ba8ad1a8a83a71910a714d890ff2393a6f910b4f4429b55375b80658934d0c9bdf1345', '2025-11-12 08:17:09', NULL, NULL, '2025-12-05 14:38:54'),
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
(21, 'dani', 'admin', 'scrypt:32768:8:1$th9qB3WYbNSre9Zs$944bf82972500ebf8e5831801275afa04c00a3bdf08ccc1749348f4c4f6f945f29ba66112caa1bf8bc9a50c1896df16ef8adf5bcdc5d01559e89c65575367db1', '2025-12-05 15:25:12', '579f1e94b54895ca984824fa8b010f8c', '2025-12-05 15:55:19', '2025-12-05 15:25:19');

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `tbl_compra`
--
ALTER TABLE `tbl_compra`
  ADD PRIMARY KEY (`Folio`),
  ADD KEY `idx_compra_modo` (`ID_Modo_Entrega`),
  ADD KEY `idx_compra_fecha` (`ID_Fecha`),
  ADD KEY `idx_compra_mesa` (`ID_Mesa`);

--
-- Indices de la tabla `tbl_detalle`
--
ALTER TABLE `tbl_detalle`
  ADD PRIMARY KEY (`ID_Detalle`),
  ADD KEY `idx_detalle_folio` (`Folio`),
  ADD KEY `idx_detalle_producto` (`ID_Producto`);

--
-- Indices de la tabla `tbl_fecha`
--
ALTER TABLE `tbl_fecha`
  ADD PRIMARY KEY (`ID_Fecha`),
  ADD KEY `idx_fecha` (`Anio`,`Mes`,`Dia`);

--
-- Indices de la tabla `tbl_mesa`
--
ALTER TABLE `tbl_mesa`
  ADD PRIMARY KEY (`ID_Mesa`),
  ADD UNIQUE KEY `ux_mesa` (`Mesa`);

--
-- Indices de la tabla `tbl_modo_entrega`
--
ALTER TABLE `tbl_modo_entrega`
  ADD PRIMARY KEY (`ID_Modo_Entrega`),
  ADD UNIQUE KEY `ux_modo` (`Modo_Entrega`);

--
-- Indices de la tabla `tbl_producto`
--
ALTER TABLE `tbl_producto`
  ADD PRIMARY KEY (`ID_Producto`),
  ADD UNIQUE KEY `ux_producto_nombre` (`Nombre_Producto`);

--
-- Indices de la tabla `tbl_usuarios`
--
ALTER TABLE `tbl_usuarios`
  ADD PRIMARY KEY (`ID_Usuario`),
  ADD UNIQUE KEY `ux_usuarios_nombre_norm` (`Nombre_Usuario_norm`),
  ADD KEY `idx_session_token` (`Session_Token`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `tbl_compra`
--
ALTER TABLE `tbl_compra`
  MODIFY `Folio` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=31;

--
-- AUTO_INCREMENT de la tabla `tbl_detalle`
--
ALTER TABLE `tbl_detalle`
  MODIFY `ID_Detalle` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=51;

--
-- AUTO_INCREMENT de la tabla `tbl_fecha`
--
ALTER TABLE `tbl_fecha`
  MODIFY `ID_Fecha` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT de la tabla `tbl_mesa`
--
ALTER TABLE `tbl_mesa`
  MODIFY `ID_Mesa` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=109;

--
-- AUTO_INCREMENT de la tabla `tbl_modo_entrega`
--
ALTER TABLE `tbl_modo_entrega`
  MODIFY `ID_Modo_Entrega` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de la tabla `tbl_producto`
--
ALTER TABLE `tbl_producto`
  MODIFY `ID_Producto` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=1037;

--
-- AUTO_INCREMENT de la tabla `tbl_usuarios`
--
ALTER TABLE `tbl_usuarios`
  MODIFY `ID_Usuario` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=22;

--
-- Restricciones para tablas volcadas
--

--
-- Filtros para la tabla `tbl_compra`
--
ALTER TABLE `tbl_compra`
  ADD CONSTRAINT `fk_compra_fecha` FOREIGN KEY (`ID_Fecha`) REFERENCES `tbl_fecha` (`ID_Fecha`),
  ADD CONSTRAINT `fk_compra_mesa` FOREIGN KEY (`ID_Mesa`) REFERENCES `tbl_mesa` (`ID_Mesa`),
  ADD CONSTRAINT `fk_compra_modo` FOREIGN KEY (`ID_Modo_Entrega`) REFERENCES `tbl_modo_entrega` (`ID_Modo_Entrega`);

--
-- Filtros para la tabla `tbl_detalle`
--
ALTER TABLE `tbl_detalle`
  ADD CONSTRAINT `fk_detalle_compra` FOREIGN KEY (`Folio`) REFERENCES `tbl_compra` (`Folio`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_detalle_producto` FOREIGN KEY (`ID_Producto`) REFERENCES `tbl_producto` (`ID_Producto`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
