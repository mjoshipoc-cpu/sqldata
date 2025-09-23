. Highest selling Product of the month
(`productCode` varchar(15) NOT NULL,
  `productName` varchar(70) NOT NULL,
  `productVendor` varchar(50) NOT NULL,
  `productDescription` text NOT NULL,
  `quantityInStock` smallint(6) NOT NULL,
  `buyPrice` decimal(10,2) NOT NULL,
  `MSRP` decimal(10,2) NOT NULL)
  `month` varchar(50) NOT NULL)
 
2. Highest spending Customer of the month
(`customerNumber` int(11) NOT NULL,
  `customerName` varchar(50) NOT NULL,
  `contactLastName` varchar(50) NOT NULL,
  `contactFirstName` varchar(50) NOT NULL,
  `phone` varchar(50) NOT NULL,
  `addressLine1` varchar(50) NOT NULL,
  `addressLine2` varchar(50) DEFAULT NULL,
  `month` varchar(50) NOT NULL)
  
3. Highest orders recived from City for the month
(`city` varchar(50) NOT NULL,
  `state` varchar(50) DEFAULT NULL,
  `amount` decimal(10,2) NOT NULL,
  `month` varchar(50) NOT NULL)
