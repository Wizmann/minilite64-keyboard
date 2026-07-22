EESchema Schematic File Version 4
LIBS:power
LIBS:device
LIBS:Connector_Generic
EELAYER 29 0
EELAYER END
$Descr A4 11693 8268
Sheet 1 1
Title "Minilite64 RP2040-Zero carrier"
Comment1 "Castellated module carrier and 20P FFC"
$EndDescr
$Comp
L Connector_Generic:Conn_01x20 J1
U 1 1 a0e977ef
P 2900 3700
F 0 "J1" H 3080 3800 50  0000 C CNN
F 1 "Type-A FFC / pins straight" H 3150 3600 50  0000 C CNN
	1    2900 3700
	1 0 0 -1
$EndComp
$Comp
L Connector_Generic:Conn_01x23 U1
U 1 1 5afaf470
P 7200 3700
F 0 "U1" H 7380 3800 50  0000 C CNN
F 1 "Waveshare RP2040-Zero castellated" H 7450 3600 50  0000 C CNN
	1    7200 3700
	1 0 0 -1
$EndComp
Wire Wire Line
	2650 2750 2450 2750
Text Label 2450 2750 2    40   ~ 0
COL0
Wire Wire Line
	2650 2850 2450 2850
Text Label 2450 2850 2    40   ~ 0
COL1
Wire Wire Line
	2650 2950 2450 2950
Text Label 2450 2950 2    40   ~ 0
COL2
Wire Wire Line
	2650 3050 2450 3050
Text Label 2450 3050 2    40   ~ 0
COL3
Wire Wire Line
	2650 3150 2450 3150
Text Label 2450 3150 2    40   ~ 0
COL4
Wire Wire Line
	2650 3250 2450 3250
Text Label 2450 3250 2    40   ~ 0
COL5
Wire Wire Line
	2650 3350 2450 3350
Text Label 2450 3350 2    40   ~ 0
COL6
Wire Wire Line
	2650 3450 2450 3450
Text Label 2450 3450 2    40   ~ 0
COL7
Wire Wire Line
	2650 3550 2450 3550
Text Label 2450 3550 2    40   ~ 0
COL8
Wire Wire Line
	2650 3650 2450 3650
Text Label 2450 3650 2    40   ~ 0
COL9
Wire Wire Line
	2650 3750 2450 3750
Text Label 2450 3750 2    40   ~ 0
COL10
Wire Wire Line
	2650 3850 2450 3850
Text Label 2450 3850 2    40   ~ 0
COL11
Wire Wire Line
	2650 3950 2450 3950
Text Label 2450 3950 2    40   ~ 0
COL12
Wire Wire Line
	2650 4050 2450 4050
Text Label 2450 4050 2    40   ~ 0
COL13
Wire Wire Line
	2650 4150 2450 4150
Text Label 2450 4150 2    40   ~ 0
ROW0
Wire Wire Line
	2650 4250 2450 4250
Text Label 2450 4250 2    40   ~ 0
ROW1
Wire Wire Line
	2650 4350 2450 4350
Text Label 2450 4350 2    40   ~ 0
ROW2
Wire Wire Line
	2650 4450 2450 4450
Text Label 2450 4450 2    40   ~ 0
ROW3
Wire Wire Line
	2650 4550 2450 4550
Text Label 2450 4550 2    40   ~ 0
ROW4
Wire Wire Line
	2650 4650 2450 4650
Text Label 2450 4650 2    40   ~ 0
GND
Wire Wire Line
	6950 2600 6700 2600
Text Label 6700 2600 2    40   ~ 0
5V_NC
Wire Wire Line
	6950 2700 6700 2700
Text Label 6700 2700 2    40   ~ 0
GND
Wire Wire Line
	6950 2800 6700 2800
Text Label 6700 2800 2    40   ~ 0
3V3_NC
Wire Wire Line
	6950 2900 6700 2900
Text Label 6700 2900 2    40   ~ 0
ROW0
Wire Wire Line
	6950 3000 6700 3000
Text Label 6700 3000 2    40   ~ 0
ROW1
Wire Wire Line
	6950 3100 6700 3100
Text Label 6700 3100 2    40   ~ 0
ROW2
Wire Wire Line
	6950 3200 6700 3200
Text Label 6700 3200 2    40   ~ 0
ROW3
Wire Wire Line
	6950 3300 6700 3300
Text Label 6700 3300 2    40   ~ 0
ROW4
Wire Wire Line
	6950 3400 6700 3400
Text Label 6700 3400 2    40   ~ 0
GP14_NC
Wire Wire Line
	6950 3500 6700 3500
Text Label 6700 3500 2    40   ~ 0
COL13
Wire Wire Line
	6950 3600 6700 3600
Text Label 6700 3600 2    40   ~ 0
COL12
Wire Wire Line
	6950 3700 6700 3700
Text Label 6700 3700 2    40   ~ 0
COL11
Wire Wire Line
	6950 3800 6700 3800
Text Label 6700 3800 2    40   ~ 0
COL10
Wire Wire Line
	6950 3900 6700 3900
Text Label 6700 3900 2    40   ~ 0
COL9
Wire Wire Line
	6950 4000 6700 4000
Text Label 6700 4000 2    40   ~ 0
COL8
Wire Wire Line
	6950 4100 6700 4100
Text Label 6700 4100 2    40   ~ 0
COL7
Wire Wire Line
	6950 4200 6700 4200
Text Label 6700 4200 2    40   ~ 0
COL6
Wire Wire Line
	6950 4300 6700 4300
Text Label 6700 4300 2    40   ~ 0
COL5
Wire Wire Line
	6950 4400 6700 4400
Text Label 6700 4400 2    40   ~ 0
COL0
Wire Wire Line
	6950 4500 6700 4500
Text Label 6700 4500 2    40   ~ 0
COL1
Wire Wire Line
	6950 4600 6700 4600
Text Label 6700 4600 2    40   ~ 0
COL2
Wire Wire Line
	6950 4700 6700 4700
Text Label 6700 4700 2    40   ~ 0
COL3
Wire Wire Line
	6950 4800 6700 4800
Text Label 6700 4800 2    40   ~ 0
COL4
Text Notes 1800 6500 0    80   ~ 12
GP16 is reserved for the onboard WS2812 and is not used. GP14 remains spare.
$EndSCHEMATC
