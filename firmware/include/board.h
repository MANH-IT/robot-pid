#ifndef BOARD_H
#define BOARD_H

#include "stm32f1xx_hal.h"

/* ============================================================
 * BOARD.H – ĐỊNH NGHĨA CHÂN CHO ROBOT MECANUM 4 BÁNH
 * - Encoder: 3 timer phần cứng (TIM2/3/4) + 1 software (EXTI8)
 * - Motor: TIM1 PWM 20 kHz + 4 DIR pins
 * - UART: USART2 115200 bps
 * - E-STOP: EXTI0 PB0
 * - LED: PC13 (onboard, active low)
 * ============================================================ */

/* ------------------------------------------------------------
 * 1. ENCODER – 3 TIMER PHẦN CỨNG + 1 EXTI SOFTWARE
 * ------------------------------------------------------------ */

/* --- Encoder M1 (Front Left) – TIM2 --- */
#define ENC1_A_PORT         GPIOA
#define ENC1_A_PIN          GPIO_PIN_0
#define ENC1_B_PORT         GPIOA
#define ENC1_B_PIN          GPIO_PIN_1
#define ENC1_INVERT         0u

/* --- Encoder M2 (Front Right) – TIM3 --- */
#define ENC2_A_PORT         GPIOA
#define ENC2_A_PIN          GPIO_PIN_6
#define ENC2_B_PORT         GPIOA
#define ENC2_B_PIN          GPIO_PIN_7
#define ENC2_INVERT         0u

/* --- Encoder M3 (Rear Left) – TIM4 --- */
#define ENC3_A_PORT         GPIOB
#define ENC3_A_PIN          GPIO_PIN_6
#define ENC3_B_PORT         GPIOB
#define ENC3_B_PIN          GPIO_PIN_7
#define ENC3_INVERT         0u

/* --- Encoder M4 (Rear Right) – EXTI8 + software --- */
#define ENC4_A_PORT         GPIOB
#define ENC4_A_PIN          GPIO_PIN_8
#define ENC4_B_PORT         GPIOB
#define ENC4_B_PIN          GPIO_PIN_9
#define ENC4_INVERT         0u

/* ------------------------------------------------------------
 * 2. MOTOR PWM – TIM1_CH1..CH4 (20 kHz)
 * ------------------------------------------------------------ */
#define MOTOR1_PWM_PORT     GPIOA
#define MOTOR1_PWM_PIN      GPIO_PIN_8
#define MOTOR2_PWM_PORT     GPIOA
#define MOTOR2_PWM_PIN      GPIO_PIN_9
#define MOTOR3_PWM_PORT     GPIOA
#define MOTOR3_PWM_PIN      GPIO_PIN_10
#define MOTOR4_PWM_PORT     GPIOA
#define MOTOR4_PWM_PIN      GPIO_PIN_11

/* ------------------------------------------------------------
 * 3. MOTOR DIR – GPIO OUT (BTS7960 LPWM)
 * ------------------------------------------------------------ */
#define MOTOR1_DIR_PORT     GPIOB
#define MOTOR1_DIR_PIN      GPIO_PIN_12
#define MOTOR2_DIR_PORT     GPIOB
#define MOTOR2_DIR_PIN      GPIO_PIN_13
#define MOTOR3_DIR_PORT     GPIOB
#define MOTOR3_DIR_PIN      GPIO_PIN_14
#define MOTOR4_DIR_PORT     GPIOB
#define MOTOR4_DIR_PIN      GPIO_PIN_15

/* ------------------------------------------------------------
 * 4. UART2 – GIAO TIẾP NODEMCU V3
 * ------------------------------------------------------------ */
#define UART_TX_PORT        GPIOA
#define UART_TX_PIN         GPIO_PIN_2
#define UART_RX_PORT        GPIOA
#define UART_RX_PIN         GPIO_PIN_3
#define UART_BAUDRATE       115200u

/* ------------------------------------------------------------
 * 5. E-STOP – NGẮT KHẨN CẤP VẬT LÝ
 * ------------------------------------------------------------ */
#define ESTOP_PORT          GPIOB
#define ESTOP_PIN           GPIO_PIN_0
#define ESTOP_EXTI_IRQn     EXTI0_IRQn

/* ------------------------------------------------------------
 * 6. LED STATUS
 * ------------------------------------------------------------ */
#define LED_PORT            GPIOC
#define LED_PIN             GPIO_PIN_13

#endif /* BOARD_H */