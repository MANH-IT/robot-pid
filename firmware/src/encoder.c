#include "encoder.h"
#include "board.h"

/* Khai báo extern các timer handle từ main.c */
extern TIM_HandleTypeDef htim2;
extern TIM_HandleTypeDef htim3;
extern TIM_HandleTypeDef htim4;

/* Bảng chuyển trạng thái quadrature x4 */
static const int8_t quadrature_table[16] = {
     0, -1,  1,  0,
     1,  0,  0, -1,
    -1,  0,  0,  1,
     0,  1, -1,  0
};

static uint8_t read_state(Encoder *enc)
{
    uint8_t a = (HAL_GPIO_ReadPin(enc->port_a, enc->pin_a) == GPIO_PIN_SET) ? 1u : 0u;
    uint8_t b = (HAL_GPIO_ReadPin(enc->port_b, enc->pin_b) == GPIO_PIN_SET) ? 1u : 0u;
    return (uint8_t)((a << 1) | b);
}

void encoder_init(Encoder *enc, EncoderId id,
                  TIM_HandleTypeDef *timer,
                  GPIO_TypeDef *port_a, uint16_t pin_a,
                  GPIO_TypeDef *port_b, uint16_t pin_b,
                  uint8_t invert)
{
    enc->id          = id;
    enc->timer       = timer;
    enc->port_a      = port_a;
    enc->pin_a       = pin_a;
    enc->port_b      = port_b;
    enc->pin_b       = pin_b;
    enc->invert      = invert;
    enc->sw_count    = 0;
    enc->last_count  = 0;
    enc->prev_state  = read_state(enc);

    if (timer != NULL) {
        HAL_TIM_Encoder_Start(timer, TIM_CHANNEL_ALL);
        __HAL_TIM_SET_COUNTER(timer, 0);
    }
}

int32_t encoder_take_delta(Encoder *enc)
{
    int32_t current_count = 0;
    int32_t delta;

    if (enc->timer != NULL) {
        current_count = (int32_t)__HAL_TIM_GET_COUNTER(enc->timer);
    } else {
        uint32_t primask = __get_PRIMASK();
        __disable_irq();
        current_count = enc->sw_count;
        if (primask == 0u) {
            __enable_irq();
        }
    }

    delta = current_count - enc->last_count;

    if (enc->timer != NULL) {
        if (delta > 32767)  delta -= 65536;
        if (delta < -32768) delta += 65536;
    }

    enc->last_count = current_count;

    return enc->invert ? -delta : delta;
}

float encoder_get_rpm(Encoder *enc, int32_t delta, float cpr, float dt_sec)
{
    (void)enc;
    if (dt_sec <= 0.0f || cpr <= 0.0f) {
        return 0.0f;
    }
    return ((float)delta / cpr / dt_sec) * 60.0f;
}

void encoder_handle_edge(Encoder *enc)
{
    uint8_t state;
    uint8_t index;
    int8_t delta;

    if (enc->timer != NULL) {
        return;
    }

    state = read_state(enc);
    index = (uint8_t)((enc->prev_state << 2) | state);
    delta = quadrature_table[index & 0x0Fu];

    enc->sw_count += delta;
    enc->prev_state = state;
}

void encoder_reset(Encoder *enc)
{
    if (enc->timer != NULL) {
        __HAL_TIM_SET_COUNTER(enc->timer, 0);
    } else {
        uint32_t primask = __get_PRIMASK();
        __disable_irq();
        enc->sw_count = 0;
        if (primask == 0u) {
            __enable_irq();
        }
    }
    enc->last_count = 0;
}