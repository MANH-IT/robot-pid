#ifndef ENCODER_H
#define ENCODER_H

#include "stm32f1xx_hal.h"
#include <stdint.h>

/* ============================================================
 * ENCODER.H – API CHO 4 ENCODER JGB37-520
 * - Encoder 1–3: TIM2/3/4 encoder mode (phần cứng)
 * - Encoder 4:   EXTI8 + software quadrature decode
 * ============================================================ */

typedef enum {
    ENCODER_1 = 0,
    ENCODER_2 = 1,
    ENCODER_3 = 2,
    ENCODER_4 = 3
} EncoderId;

typedef struct {
    EncoderId id;
    TIM_HandleTypeDef *timer;   /* NULL nếu dùng software (ENC4) */
    GPIO_TypeDef *port_a;
    uint16_t pin_a;
    GPIO_TypeDef *port_b;
    uint16_t pin_b;
    uint8_t invert;
    volatile int32_t sw_count;
    volatile uint8_t prev_state;
    int32_t last_count;
} Encoder;

void encoder_init(Encoder *enc, EncoderId id,
                  TIM_HandleTypeDef *timer,
                  GPIO_TypeDef *port_a, uint16_t pin_a,
                  GPIO_TypeDef *port_b, uint16_t pin_b,
                  uint8_t invert);

int32_t encoder_take_delta(Encoder *enc);
float encoder_get_rpm(Encoder *enc, int32_t delta, float cpr, float dt_sec);
void encoder_handle_edge(Encoder *enc);
void encoder_reset(Encoder *enc);

#endif /* ENCODER_H */