#ifndef STM32F1xx_HAL_CONF_H
#define STM32F1xx_HAL_CONF_H

/* ============================================================
 * STM32F1xx HAL CONFIGURATION
 * - Cấu hình module HAL được bật cho STM32F103
 * - Clock dùng HSI nội 64 MHz (HSI/2 × PLL16); HSE_VALUE chỉ giữ để tham khảo
 * ============================================================ */

#ifdef __cplusplus
extern "C" {
#endif

#define HAL_MODULE_ENABLED
#define HAL_CORTEX_MODULE_ENABLED
#define HAL_GPIO_MODULE_ENABLED
#define HAL_RCC_MODULE_ENABLED
#define HAL_FLASH_MODULE_ENABLED
#define HAL_PWR_MODULE_ENABLED
#define HAL_TIM_MODULE_ENABLED
#define HAL_UART_MODULE_ENABLED
#define HAL_IWDG_MODULE_ENABLED

#if !defined(HSE_VALUE)
#define HSE_VALUE 8000000U
#endif

#if !defined(HSE_STARTUP_TIMEOUT)
#define HSE_STARTUP_TIMEOUT 100U
#endif

#if !defined(HSI_VALUE)
#define HSI_VALUE 8000000U
#endif

#if !defined(HSI_STARTUP_TIMEOUT)
#define HSI_STARTUP_TIMEOUT 5000U
#endif

#if !defined(LSI_VALUE)
#define LSI_VALUE 40000U
#endif

#if !defined(LSE_VALUE)
#define LSE_VALUE 32768U
#endif

#if !defined(LSE_STARTUP_TIMEOUT)
#define LSE_STARTUP_TIMEOUT 5000U
#endif

#define VDD_VALUE 3300U
#define TICK_INT_PRIORITY 0U
#define USE_RTOS 0U
#define PREFETCH_ENABLE 1U
#define USE_HAL_ADC_REGISTER_CALLBACKS 0U
#define USE_HAL_CAN_REGISTER_CALLBACKS 0U
#define USE_HAL_CEC_REGISTER_CALLBACKS 0U
#define USE_HAL_DAC_REGISTER_CALLBACKS 0U
#define USE_HAL_ETH_REGISTER_CALLBACKS 0U
#define USE_HAL_HCD_REGISTER_CALLBACKS 0U
#define USE_HAL_I2C_REGISTER_CALLBACKS 0U
#define USE_HAL_I2S_REGISTER_CALLBACKS 0U
#define USE_HAL_MMC_REGISTER_CALLBACKS 0U
#define USE_HAL_NAND_REGISTER_CALLBACKS 0U
#define USE_HAL_NOR_REGISTER_CALLBACKS 0U
#define USE_HAL_PCCARD_REGISTER_CALLBACKS 0U
#define USE_HAL_PCD_REGISTER_CALLBACKS 0U
#define USE_HAL_RTC_REGISTER_CALLBACKS 0U
#define USE_HAL_SD_REGISTER_CALLBACKS 0U
#define USE_HAL_SMARTCARD_REGISTER_CALLBACKS 0U
#define USE_HAL_IRDA_REGISTER_CALLBACKS 0U
#define USE_HAL_SRAM_REGISTER_CALLBACKS 0U
#define USE_HAL_SPI_REGISTER_CALLBACKS 0U
#define USE_HAL_TIM_REGISTER_CALLBACKS 0U
#define USE_HAL_UART_REGISTER_CALLBACKS 0U
#define USE_HAL_USART_REGISTER_CALLBACKS 0U
#define USE_HAL_WWDG_REGISTER_CALLBACKS 0U

#define assert_param(expr) ((void)0U)

#ifdef HAL_RCC_MODULE_ENABLED
#include "stm32f1xx_hal_rcc.h"
#include "stm32f1xx_hal_rcc_ex.h"
#endif

#ifdef HAL_GPIO_MODULE_ENABLED
#include "stm32f1xx_hal_gpio.h"
#endif

#ifdef HAL_CORTEX_MODULE_ENABLED
#include "stm32f1xx_hal_cortex.h"
#endif

#ifdef HAL_FLASH_MODULE_ENABLED
#include "stm32f1xx_hal_flash.h"
#include "stm32f1xx_hal_flash_ex.h"
#endif

#ifdef HAL_PWR_MODULE_ENABLED
#include "stm32f1xx_hal_pwr.h"
#endif

#ifdef HAL_TIM_MODULE_ENABLED
#include "stm32f1xx_hal_tim.h"
#include "stm32f1xx_hal_tim_ex.h"
#endif

#ifdef HAL_IWDG_MODULE_ENABLED
#include "stm32f1xx_hal_iwdg.h"
#endif

#ifdef HAL_UART_MODULE_ENABLED
#include "stm32f1xx_hal_uart.h"
#endif

#ifdef __cplusplus
}
#endif

#endif
