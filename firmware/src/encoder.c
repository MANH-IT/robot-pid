#include "encoder.h"

static const int8_t quadrature_table[16] = {
    0, -1, 1, 0,
    1, 0, 0, -1,
    -1, 0, 0, 1,
    0, 1, -1, 0
};

static uint8_t read_state(Encoder *encoder)
{
    uint8_t a = HAL_GPIO_ReadPin(encoder->port_a, encoder->pin_a) == GPIO_PIN_SET ? 1u : 0u;
    uint8_t b = HAL_GPIO_ReadPin(encoder->port_b, encoder->pin_b) == GPIO_PIN_SET ? 1u : 0u;
    return (uint8_t)((a << 1) | b);
}

void encoder_init(Encoder *encoder, GPIO_TypeDef *port_a, uint16_t pin_a,
                  GPIO_TypeDef *port_b, uint16_t pin_b, uint8_t invert)
{
    encoder->port_a = port_a;
    encoder->pin_a = pin_a;
    encoder->port_b = port_b;
    encoder->pin_b = pin_b;
    encoder->count = 0;
    encoder->invert = invert;
    encoder->prev_state = read_state(encoder);
}

void encoder_handle_edge(Encoder *encoder)
{
    uint8_t state = read_state(encoder);
    uint8_t index = (uint8_t)((encoder->prev_state << 2) | state);
    int8_t delta = quadrature_table[index & 0x0Fu];
    encoder->count += delta;
    encoder->prev_state = state;
}

int32_t encoder_take_delta(Encoder *encoder)
{
    int32_t delta;
    uint32_t primask = __get_PRIMASK();
    __disable_irq();
    delta = encoder->count;
    encoder->count = 0;
    if (primask == 0u) {
        __enable_irq();
    }
    return encoder->invert ? -delta : delta;
}
