#ifndef BOARD_H
#define BOARD_H

#include "stm32f1xx_hal.h"

#define ENC1_A_PORT GPIOB
#define ENC1_A_PIN GPIO_PIN_6
#define ENC1_B_PORT GPIOB
#define ENC1_B_PIN GPIO_PIN_7
#define ENC1_INVERT 0u

#define ENC2_A_PORT GPIOB
#define ENC2_A_PIN GPIO_PIN_8
#define ENC2_B_PORT GPIOB
#define ENC2_B_PIN GPIO_PIN_9
#define ENC2_INVERT 0u

#define ENC3_A_PORT GPIOB
#define ENC3_A_PIN GPIO_PIN_10
#define ENC3_B_PORT GPIOB
#define ENC3_B_PIN GPIO_PIN_11
#define ENC3_INVERT 0u

#define ENC4_A_PORT GPIOB
#define ENC4_A_PIN GPIO_PIN_12
#define ENC4_B_PORT GPIOB
#define ENC4_B_PIN GPIO_PIN_13
#define ENC4_INVERT 0u

#define LED_PORT GPIOC
#define LED_PIN GPIO_PIN_13

#endif
