#include "motor.h"

#include "stm32f1xx_hal.h"
#include "robot_config.h"

extern TIM_HandleTypeDef htim1;
extern TIM_HandleTypeDef htim3;

typedef struct {
    TIM_HandleTypeDef *htim;
    uint32_t channel;
} PwmChannel;

static const PwmChannel rpwm[4] = {
    {&htim1, TIM_CHANNEL_1},
    {&htim1, TIM_CHANNEL_2},
    {&htim1, TIM_CHANNEL_3},
    {&htim1, TIM_CHANNEL_4}
};

static const PwmChannel lpwm[4] = {
    {&htim3, TIM_CHANNEL_1},
    {&htim3, TIM_CHANNEL_2},
    {&htim3, TIM_CHANNEL_3},
    {&htim3, TIM_CHANNEL_4}
};

void motor_init(void)
{
    uint8_t index;
    for (index = 0u; index < 4u; index++) {
        HAL_TIM_PWM_Start(rpwm[index].htim, rpwm[index].channel);
        HAL_TIM_PWM_Start(lpwm[index].htim, lpwm[index].channel);
        __HAL_TIM_SET_COMPARE(rpwm[index].htim, rpwm[index].channel, 0u);
        __HAL_TIM_SET_COMPARE(lpwm[index].htim, lpwm[index].channel, 0u);
    }
}

void motor_set(uint8_t index, float command)
{
    float magnitude;
    uint32_t compare;

    if (index >= 4u) {
        return;
    }

    if (command > 1.0f) {
        command = 1.0f;
    } else if (command < -1.0f) {
        command = -1.0f;
    }

    magnitude = command < 0.0f ? -command : command;
    compare = (uint32_t)(magnitude * (float)PWM_TIM_ARR + 0.5f);
    if (compare > PWM_TIM_ARR) {
        compare = PWM_TIM_ARR;
    }

    if (compare == 0u) {
        __HAL_TIM_SET_COMPARE(rpwm[index].htim, rpwm[index].channel, 0u);
        __HAL_TIM_SET_COMPARE(lpwm[index].htim, lpwm[index].channel, 0u);
    } else if (command > 0.0f) {
        __HAL_TIM_SET_COMPARE(lpwm[index].htim, lpwm[index].channel, 0u);
        __HAL_TIM_SET_COMPARE(rpwm[index].htim, rpwm[index].channel, compare);
    } else {
        __HAL_TIM_SET_COMPARE(rpwm[index].htim, rpwm[index].channel, 0u);
        __HAL_TIM_SET_COMPARE(lpwm[index].htim, lpwm[index].channel, compare);
    }
}

void motor_stop_all(void)
{
    uint8_t index;
    for (index = 0u; index < 4u; index++) {
        __HAL_TIM_SET_COMPARE(rpwm[index].htim, rpwm[index].channel, 0u);
        __HAL_TIM_SET_COMPARE(lpwm[index].htim, lpwm[index].channel, 0u);
    }
}
