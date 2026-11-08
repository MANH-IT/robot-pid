#include "motor.h"

#include "stm32f1xx_hal.h"
#include "board.h"
#include "robot_config.h"

extern TIM_HandleTypeDef htim1;

typedef struct {
    uint32_t pwm_channel;
    GPIO_TypeDef *dir_port;
    uint16_t dir_pin;
} MotorChannel;

static const MotorChannel motors[4] = {
    { TIM_CHANNEL_1, MOTOR1_DIR_PORT, MOTOR1_DIR_PIN },
    { TIM_CHANNEL_2, MOTOR2_DIR_PORT, MOTOR2_DIR_PIN },
    { TIM_CHANNEL_3, MOTOR3_DIR_PORT, MOTOR3_DIR_PIN },
    { TIM_CHANNEL_4, MOTOR4_DIR_PORT, MOTOR4_DIR_PIN }
};

void motor_init(void)
{
    uint8_t i;
    for (i = 0u; i < 4u; i++) {
        HAL_TIM_PWM_Start(&htim1, motors[i].pwm_channel);
        __HAL_TIM_SET_COMPARE(&htim1, motors[i].pwm_channel, 0u);
        HAL_GPIO_WritePin(motors[i].dir_port, motors[i].dir_pin, GPIO_PIN_RESET);
    }
}

void motor_set(uint8_t index, float command)
{
    float magnitude;
    uint32_t compare;
    GPIO_PinState dir;

    if (index >= 4u) return;

    if (command > 1.0f) command = 1.0f;
    else if (command < -1.0f) command = -1.0f;

    magnitude = (command < 0.0f) ? -command : command;
    compare = (uint32_t)(magnitude * (float)PWM_TIM_ARR + 0.5f);
    if (compare > PWM_TIM_ARR) compare = PWM_TIM_ARR;

    dir = (command < 0.0f) ? GPIO_PIN_SET : GPIO_PIN_RESET;

    HAL_GPIO_WritePin(motors[index].dir_port, motors[index].dir_pin, dir);
    __HAL_TIM_SET_COMPARE(&htim1, motors[index].pwm_channel, compare);
}

void motor_stop_all(void)
{
    uint8_t i;
    for (i = 0u; i < 4u; i++) {
        __HAL_TIM_SET_COMPARE(&htim1, motors[i].pwm_channel, 0u);
        HAL_GPIO_WritePin(motors[i].dir_port, motors[i].dir_pin, GPIO_PIN_RESET);
    }
}

void motor_brake_all(void)
{
    uint8_t i;
    for (i = 0u; i < 4u; i++) {
        HAL_GPIO_WritePin(motors[i].dir_port, motors[i].dir_pin, GPIO_PIN_SET);
        __HAL_TIM_SET_COMPARE(&htim1, motors[i].pwm_channel, PWM_TIM_ARR);
    }
}