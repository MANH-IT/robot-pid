#ifndef BOARD_H
#define BOARD_H

#include "stm32f1xx_hal.h"

/* ============================================================
 * BOARD.H – ĐỊNH NGHĨA CHÂN CHO ROBOT MECANUM 4 BÁNH
 * - Encoder: 2 timer phần cứng (TIM2/TIM4) + 2 software (EXTI8, EXTI10)
 * - Motor: RPWM (TIM1) + LPWM (TIM3) 20 kHz — BTS7960
 * - UART: USART2 115200 bps
 * - E-STOP: EXTI0 PC0
 * - LED: PC13 (onboard, active low)
 * ============================================================ */

/* ------------------------------------------------------------
 * 1. ĐẢO CHIỀU BÁNH (khi đấu dây motor/encoder bị ngược)
 * ------------------------------------------------------------
 * Bit 0..3 tương ứng bánh M1..M4.
 * - Nếu MỘT bánh quay ngược chiều tiến: đảo bit của bánh đó ở CẢ HAI mask.
 * - Ví dụ bánh phải (M2, M4) ngược: 0x0A. Cả 4 bánh ngược: 0x0F.
 * - Chỉ đảo MOTOR mà không đảo ENCODER sẽ làm PID hồi tiếp sai dấu
 *   (xe chạy full-speed ngược) — luôn đảo cặp mask cùng bánh.
 * Kiểm tra nhanh: gửi "M,1,0.2" (PWM thủ công) và xem bánh 1 quay tới.
 */
#define MOTOR_INVERT_MASK   0x0u
#define ENCODER_INVERT_MASK 0x0u

/* ------------------------------------------------------------
 * 2. ENCODER – 2 TIMER PHẦN CỨNG (TIM2/TIM4) + 2 EXTI SOFTWARE (EXTI10/EXTI8)
 * ------------------------------------------------------------ */

/* --- Encoder M1 (Front Left) – TIM2 --- */
#define ENC1_A_PORT         GPIOA
#define ENC1_A_PIN          GPIO_PIN_0
#define ENC1_B_PORT         GPIOA
#define ENC1_B_PIN          GPIO_PIN_1
#define ENC1_INVERT         (((ENCODER_INVERT_MASK) >> 0u) & 1u)

/* --- Encoder M2 (Front Right) – EXTI10/11 + software (giống bánh 4) --- */
#define ENC2_A_PORT         GPIOB
#define ENC2_A_PIN          GPIO_PIN_10
#define ENC2_B_PORT         GPIOB
#define ENC2_B_PIN          GPIO_PIN_11
#define ENC2_INVERT         (((ENCODER_INVERT_MASK) >> 1u) & 1u)

/* --- Encoder M3 (Rear Left) – TIM4 --- */
#define ENC3_A_PORT         GPIOB
#define ENC3_A_PIN          GPIO_PIN_6
#define ENC3_B_PORT         GPIOB
#define ENC3_B_PIN          GPIO_PIN_7
#define ENC3_INVERT         (((ENCODER_INVERT_MASK) >> 2u) & 1u)

/* --- Encoder M4 (Rear Right) – EXTI8 + software --- */
#define ENC4_A_PORT         GPIOB
#define ENC4_A_PIN          GPIO_PIN_8
#define ENC4_B_PORT         GPIOB
#define ENC4_B_PIN          GPIO_PIN_9
#define ENC4_INVERT         (((ENCODER_INVERT_MASK) >> 3u) & 1u)

/* ------------------------------------------------------------
 * 3. MOTOR RPWM – TIM1_CH1..CH4 (20 kHz) – BTS7960
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
 * 4. MOTOR LPWM – TIM3_CH1..CH4 (20 kHz) – BTS7960
 * ------------------------------------------------------------ */
#define MOTOR1_LPWM_PORT    GPIOA
#define MOTOR1_LPWM_PIN     GPIO_PIN_6    /* TIM3_CH1 */
#define MOTOR2_LPWM_PORT    GPIOA
#define MOTOR2_LPWM_PIN     GPIO_PIN_7    /* TIM3_CH2 */
#define MOTOR3_LPWM_PORT    GPIOB
#define MOTOR3_LPWM_PIN     GPIO_PIN_0    /* TIM3_CH3 */
#define MOTOR4_LPWM_PORT    GPIOB
#define MOTOR4_LPWM_PIN     GPIO_PIN_1    /* TIM3_CH4 */

/* ------------------------------------------------------------
 * 5. UART2 – GIAO TIẾP NODEMCU V3
 * ------------------------------------------------------------ */
#define UART_TX_PORT        GPIOA
#define UART_TX_PIN         GPIO_PIN_2
#define UART_RX_PORT        GPIOA
#define UART_RX_PIN         GPIO_PIN_3
#define UART_BAUDRATE       115200u

/* ------------------------------------------------------------
 * 6. E-STOP – NGẮT KHẨN CẤP VẬT LÝ
 * ------------------------------------------------------------ */
#define ESTOP_PORT          GPIOC
#define ESTOP_PIN           GPIO_PIN_0
#define ESTOP_EXTI_IRQn     EXTI0_IRQn

/* ------------------------------------------------------------
 * 7. LED STATUS
 * ------------------------------------------------------------ */
#define LED_PORT            GPIOC
#define LED_PIN             GPIO_PIN_13

#endif /* BOARD_H */