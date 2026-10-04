# Core1106 pinout — vendor table, with this board's net on every pad

Source: `Core1106-PinOut.xls` from Luckfox's Core1106 footprint package
(<https://wiki.luckfox.com/Core1106/Pinout/>). The vendor columns are reproduced
verbatim; the **Net** column is what LocalCam-1 connects, and blank means the pad is
deliberately left unconnected.

112 castellated pads, 1.0 mm pitch, pad 1 at the arrow, numbered counter-clockwise.

| Pad | Vendor pin name | IO domain | Net on this board | Vendor remark |
|----:|---|:--:|---|---|
| 1 | `VI_CIF_D2_M0/MIPI_CSI_RX_CK1N/LVDS_RX_CK1N/GPI3_B2_d` | 1.8V | — |  |
| 2 | `VI_CIF_D3_M0/MIPI_CSI_RX_CK1P/LVDS_RX_CK1P/GPI3_B3_d` | 1.8V | — |  |
| 3 | `VI_CIF_D0_M0/MIPI_CSI_RX_D3N/LVDS_RX_D3N/GPI3_B0_d` | 1.8V | — |  |
| 4 | `VI_CIF_D1_M0/MIPI_CSI_RX_D3P/LVDS_RX_D3P/GPI3_B1_d` | 1.8V | — |  |
| 5 | `VI_CIF_D4_M0/MIPI_CSI_RX_D2N/LVDS_RX_D2N/GPI3_B4_d` | 1.8V | — |  |
| 6 | `VI_CIF_D5_M0/MIPI_CSI_RX_D2P/LVDS_RX_D2P/GPI3_B5_d` | 1.8V | — |  |
| 7 | `VI_CIF_D6_M0/MIPI_CSI_RX_D1N/LVDS_RX_D1N/GPI3_B6_d` | 1.8V | **CSI_D1_N** |  |
| 8 | `VI_CIF_D7_M0/MIPI_CSI_RX_D1P/LVDS_RX_D1P/GPI3_B7_d` | 1.8V | **CSI_D1_P** |  |
| 9 | `VI_CIF_D8_M0/MIPI_CSI_RX_CK0N/LVDS_RX_CK0N/GPI3_C0_d` | 1.8V | **CSI_CLK_N** |  |
| 10 | `VI_CIF_D9_M0/MIPI_CSI_RX_CK0P/LVDS_RX_CK0P/GPI3_C1_d` | 1.8V | **CSI_CLK_P** |  |
| 11 | `VI_CIF_CLKI_M0/MIPI_CSI_RX_D0N/LVDS_RX_D0N/GPI3_C2_d` | 1.8V | **CSI_D0_N** |  |
| 12 | `VI_CIF_HREF_M0/MIPI_CSI_RX_D0P/LVDS_RX_D0P/GPI3_C3_d` | 1.8V | **CSI_D0_P** |  |
| 13 | `VI_CIF_D15/PWM1_M2/GPIO3_D3_d` | 1.8V | **CAM_PWDN** |  |
| 14 | `VI_CIF_D14/UART5_CTS_M2/I2C3_SDA_M2/GPIO3_D2_d` | 1.8V | — |  |
| 15 | `VI_CIF_D13/UART5_RTS_M2/I2C3_SCL_M2/GPIO3_D1_d` | 1.8V | — |  |
| 16 | `VI_CIF_D11/UART5_TX_M2/I2C4_SCL_M2/GPIO3_C7_d` | 1.8V | **CAM_SCL** |  |
| 17 | `VI_CIF_D12/UART5_RX_M2/I2C4_SDA_M2/GPIO3_D0_d` | 1.8V | **CAM_SDA** |  |
| 18 | `VI_CIF_VSYNC_M0/GPIO3_C5_d` | 1.8V | **CAM_RST** |  |
| 19 | `VI_CIF_CLKO_M0/MIPI_CLK0_OUT/GPIO3_C4_d` | 1.8V | **MCLK0** |  |
| 20 | `VI_CIF_D10/PWM7_IR_M2/MIPI_CLK1_OUT/GPIO3_C6_d` | 1.8V | — |  |
| 21 | `GND` | - | **GND** |  |
| 22 | `USB_N` | - | **USB_DM** |  |
| 23 | `USB_P` | - | **USB_DP** |  |
| 24 | `USB_VBUSDET` | 3.3V | **VBUS_DET** |  |
| 25 | `GND` | - | **GND** |  |
| 26 | `SARADC_IN0/GPIO4_C0_z` | 1.8V | **ADC0_RECOV** |  |
| 27 | `SARADC_IN1/PWM1_M1/GPIO4_C1_z` | 1.8V | — |  |
| 28 | `GND` | - | **GND** |  |
| 29 | `GND` | - | **GND** |  |
| 30 | `CODEC_LINEOUT` | 1.8V | — |  |
| 31 | `CODEC_MICBIAS` | 1.8V | — |  |
| 32 | `CODEC_MIC0N` | 1.8V | — |  |
| 33 | `CODEC_MIC0P` | 1.8V | — |  |
| 34 | `CODEC_MIC1N` | 1.8V | — |  |
| 35 | `CODEC_MIC1P` | 1.8V | — |  |
| 36 | `GND` | - | **GND** |  |
| 37 | `EMMC_D0/FSPI_D0/GPIO4_A4_u` | 3.3V | — | When EMMC is installed, it will be disconnected. |
| 38 | `EMMC_D1/FSPI_D1/GPIO4_A3_u` | 3.3V | — |  |
| 39 | `EMMC_D2/FSPI_D2/GPIO4_A2_u` | 3.3V | — |  |
| 40 | `EMMC_D3/FSPI_D3/GPIO4_A6_u` | 3.3V | — |  |
| 41 | `EMMC_D4/SPI1_CS0_M0/UART1_TX_M2/I2C2_SDA_M1/GPIO4_A5_u` | 3.3V | — |  |
| 42 | `EMMC_D5/SPI1_CLK_M0/UART1_RX_M2/I2C2_SCL_M1/GPIO4_A7_u` | 3.3V | — |  |
| 43 | `EMMC_D6/SPI1_MOSI_M0/UART0_TX_M2/I2C0_SCL_M1/GPIO4_A1_u` | 3.3V | — |  |
| 44 | `EMMC_D7/SPI1_MISO_M0/UART0_RX_M2/I2C0_SDA_M1/GPIO4_A0_u` | 3.3V | — |  |
| 45 | `EMMC_CMD/FSPI_CS0/GPIO4_B0_u` | 3.3V | — |  |
| 46 | `EMMC_CLK/FSPI_CLK/GPIO4_B1_d` | 3.3V | — |  |
| 47 | `GND` | - | **GND** |  |
| 48 | `SDMMC_DET/GPIO3_A1_u` | 3.3V | — | When Wifi Module is installed, it will be disconnected. |
| 49 | `SDMMC_D0/UART2_RX_M0/PWM8_M0/GPIO3_A3_u` | 3.3V | **SD_D0** |  |
| 50 | `SDMMC_D1/UART2_TX_M0/PWM9_M0/GPIO3_A2_u` | 3.3V | **SD_D1** |  |
| 51 | `SDMMC_D2/UART5_RX_M0/JTAG_CPU_TCK_M0/JTAG_HPMCU_TCK_M1/GPIO3_A7_u` | 3.3V | **SD_D2** |  |
| 52 | `SDMMC_D3/UART5_TX_M0/JTAG_CPU_TMS_M0/JTAG_HPMCU_TMS_M1/GPIO3_A6_u` | 3.3V | **SD_D3** |  |
| 53 | `SDMMC_CMD/UART5_CTS_M0/I2C0_SDA_M2/JTAG_LPMCU_TMS_M1/PWM11_IR_M0/GPIO3_A5_u` | 3.3V | **SD_CMD** |  |
| 54 | `SDMMC_CLK/UART5_RTS_M0/I2C0_SCL_M2/JTAG_LPMCU_TCK_M1/PWM10_M0/GPIO3_A4_d` | 3.3V | **SD_CLK** |  |
| 55 | `GND` | - | **GND** |  |
| 56 | `GND` | - | **GND** |  |
| 57 | `GND` | - | **GND** |  |
| 58 | `UART0_RX_M0/CLK_32K/CLK_REFOUT/RTC_CLKO/GPIO0_A0_z` | 3.3V | **LED_STAT** |  |
| 59 | `UART0_TX_M0/PWM2_M0/GPIO0_A1_d` | 3.3V | — |  |
| 60 | `PWM3_IR_M0/GPIO0_A2_d` | 3.3V | — |  |
| 61 | `PWR_CTRL_M1/GPIO0_A3_u` | 3.3V | — |  |
| 62 | `PWR_CTRL_M0/PWM1_M0/GPIO0_A4_d` | 3.3V | — |  |
| 63 | `I2C1_SCL_M0/UART1_RTS_M0/PWM5_M0/GPIO0_A5_d` | 3.3V | — | When Wifi Module is installed, it will be disconnected. |
| 64 | `I2C1_SDA_M0/UART1_CTS_M0/PWM6_M0/GPIO0_A6_d` | 3.3V | — |  |
| 65 | `UART3_TX_M0/I2C2_SCL_M0/PWM7_IR_M0/GPIO1_A0_d` | 3.3V | — |  |
| 66 | `UART3_RX_M0/I2C2_SDA_M0/PMU_DEBUG/PWM4_M0/GPIO1_A1_d` | 3.3V | — |  |
| 67 | `PWM0_M0/CPU_AVS/VI_CIF_D0_M1/GPIO1_A2_d` | 3.3V | — |  |
| 68 | `UART1_TX_M0/I2C0_SCL_M0/GPIO1_A3_d` | 3.3V | — | When Wifi Module is installed, it will be disconnected. |
| 69 | `UART1_RX_M0/I2C0_SDA_M0/GPIO1_A4_d` | 3.3V | — |  |
| 70 | `UART4_RX_M0/PWM3_IR_M1/GPIO1_B0_d` | 3.3V | — |  |
| 71 | `UART4_TX_M0/PWM7_IR_M1/SPI1_CS1_M0/VI_CIF_D1_M1/GPIO1_B1_d` | 3.3V | — |  |
| 72 | `JTAG_CPU_TCK_M1/UART2_TX_M1/JTAG_HPMCU_TCK_M0/JTAG_LPMCU_TCK_M0/GPIO1_B2_d` | 3.3V | **UART2_TX** |  |
| 73 | `JTAG_CPU_TMS_M1/UART2_RX_M1/JTAG_HPMCU_TMS_M0/JTAG_LPMCU_TMS_M0/GPIO1_B3_u` | 3.3V | **UART2_RX** |  |
| 74 | `NPOR` | - | **NPOR_RST** |  |
| 75 | `GND` | - | **GND** |  |
| 76 | `VCC3V3_RTC` | - | — |  |
| 77 | `VCC_1V8` | - | **+1V8** |  |
| 78 | `VCC_3V3` | - | **+3V3** |  |
| 79 | `VCC5V0_SYS` | - | **+5V** |  |
| 80 | `VCC5V0_SYS` | - | **+5V** |  |
| 81 | `VCC5V0_SYS` | - | **+5V** |  |
| 82 | `GND` | - | **GND** |  |
| 83 | `GND` | - | **GND** |  |
| 84 | `GND` | - | **GND** |  |
| 85 | `FEPHY_RXN` | - | — |  |
| 86 | `FEPHY_RXP` | - | — |  |
| 87 | `FEPHY_TXN` | - | — |  |
| 88 | `FEPHY_TXP` | - | — |  |
| 89 | `GND` | - | **GND** |  |
| 90 | `VO_LCDC_CLK/VI_CIF_CLKO_M1/I2C3_SCL_M1/UART5_TX_M1/PWM11_IR_M2/AUD_DSM_N/GPIO1_D3_d` | 3.3V | — |  |
| 91 | `VO_LCDC_VSYNC/VI_CIF_VSYNC_M1/I2C3_SDA_M1/UART5_RX_M1/SPI0_CS1_M0/PWM0_M1/AUD_DSM_P/GPIO1_D2_d` | 3.3V | — |  |
| 92 | `VO_LCDC_HSYNC/VI_CIF_HREF_M1/PWM10_M2/UART5_CTS_M1/UART3_RX_M1/GPIO1_D1_d` | 3.3V | — |  |
| 93 | `VO_LCDC_DEN/VI_CIF_CLKI_M1/PWM3_IR_M2/UART5_RTS_M1/UART3_TX_M1/GPIO1_D0_d` | 3.3V | — |  |
| 94 | `VO_LCDC_D0/VI_CIF_D9_M1/PWM11_IR_M1/UART4_CTS_M1/GPIO1_C7_d` | 3.3V | — |  |
| 95 | `VO_LCDC_D1/VI_CIF_D8_M1/PWM10_M1/UART4_RTS_M1/GPIO1_C6_d` | 3.3V | — |  |
| 96 | `VO_LCDC_D2/VI_CIF_D7_M1/PWM9_M1/UART4_TX_M1/SDIO_D2_M1/GPIO1_C5_d` | 3.3V | — |  |
| 97 | `VO_LCDC_D3/VI_CIF_D6_M1/PWM8_M1/UART4_RX_M1/SDIO_D3_M1/GPIO1_C4_d` | 3.3V | — |  |
| 98 | `VO_LCDC_D4/VI_CIF_D5_M1/PWM6_M2/I2C4_SDA_M1/SDIO_CMD_M1/SPI0_MISO_M0/GPIO1_C3_d` | 3.3V | — |  |
| 99 | `VO_LCDC_D5/VI_CIF_D4_M1/PWM5_M2/I2C4_SCL_M1/SDIO_CLK_M1/SPI0_MOSI_M0/GPIO1_C2_d` | 3.3V | — |  |
| 100 | `VO_LCDC_D6/VI_CIF_D3_M1/PWM4_M2/SPI0_CLK_M0/SDIO_D0_M1/GPIO1_C1_d` | 3.3V | — |  |
| 101 | `VO_LCDC_D7/VI_CIF_D2_M1/PWM2_M2/SPI0_CS0_M0/SDIO_D1_M1/GPIO1_C0_d` | 3.3V | — |  |
| 102 | `SDIO_D1_M0/I2S0_SCLK/VO_LCDC_D8/UART1_CTS_M1/I2C4_SDA_M0/GPIO2_A0_d` | 3.3V | — |  |
| 103 | `SDIO_D0_M0/I2S0_LRCK/VO_LCDC_D9/UART1_RTS_M1/I2C4_SCL_M0/GPIO2_A1_d` | 3.3V | — |  |
| 104 | `SDIO_CLK_M0/I2S0_MCLK/VO_LCDC_D10/GPIO2_A2_d` | 3.3V | — |  |
| 105 | `SDIO_CMD_M0/I2S0_SDO3_SDI1/VO_LCDC_D11/GPIO2_A3_d` | 3.3V | — |  |
| 106 | `SDIO_D3_M0/I2S0_SDO0/VO_LCDC_D12/UART1_TX_M1/GPIO2_A4_d` | 3.3V | — |  |
| 107 | `SDIO_D2_M0/I2S0_SDI0/VO_LCDC_D13/UART1_RX_M1/GPIO2_A5_d` | 3.3V | — |  |
| 108 | `UART0_RTS_M1/I2S0_SDO2_SDI2/VO_LCDC_D14/PWM2_M1/I2C3_SCL_M0/FLASH_TRIG_OUT/GPIO2_A6_d` | 3.3V | — |  |
| 109 | `UART0_CTS_M1/I2S0_SDO1_SDI3/VO_LCDC_D15/PWM4_M1/I2C3_SDA_M0/PRELIGHT_TRIG_OUT/GPIO2_A7_d` | 3.3V | — |  |
| 110 | `UART0_RX_M1/I2C1_SCL_M1/VO_LCDC_D16/PWM5_M1/GPIO2_B0_d` | 3.3V | — |  |
| 111 | `UART0_TX_M1/I2C1_SDA_M1/VO_LCDC_D17/PWM6_M1/GPIO2_B1_d` | 3.3V | — |  |
| 112 | `GND` | - | **GND** |  |
