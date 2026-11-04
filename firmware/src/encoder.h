#ifndef ENCODER_H
#define ENCODER_H

#include <stdint.h>

#include "stm32f1xx_hal.h"

typedef struct {
    GPIO_TypeDef *port_a;
    uint16_t pin_a;
    GPIO_TypeDef *port_b;
    uint16_t pin_b;
    volatile int32_t count;
    volatile uint8_t prev_state;
    uint8_t invert;
} Encoder;

void encoder_init(Encoder *encoder, GPIO_TypeDef *port_a, uint16_t pin_a,
                  GPIO_TypeDef *port_b, uint16_t pin_b, uint8_t invert);
void encoder_handle_edge(Encoder *encoder);
int32_t encoder_take_delta(Encoder *encoder);

#endif
