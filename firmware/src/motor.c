#include "motor.h"

#include "stm32f1xx_hal.h"
#include "board.h"
#include "robot_config.h"

extern TIM_HandleTypeDef htim1;

/* Cấu trúc channel cho mỗi motor: PWM channel + DIR port/pin */
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

/* Khởi tạo 4 motor:
 * - Bật PWM TIM1 cho mỗi bánh
 * - Đặt compare = 0 (dừng)
 * - Đặt DIR = RESET (tiến) */
void motor_init(void)
{
    uint8_t i;
    for (i = 0u; i < 4u; i++) {
        HAL_TIM_PWM_Start(&htim1, motors[i].pwm_channel);
        __HAL_TIM_SET_COMPARE(&htim1, motors[i].pwm_channel, 0u);
        HAL_GPIO_WritePin(motors[i].dir_port, motors[i].dir_pin, GPIO_PIN_RESET);
    }
}

/* Đặt duty cho motor index (0..3):
 * - command > 0: tiến (DIR=RESET, PWM = duty)
 * - command < 0: lùi (DIR=SET, PWM = |duty|)
 * - command = 0: dừng (PWM = 0)
 * duty được clamp trong [-1,1] và map sang compare 0..PWM_TIM_ARR */
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

/* Dừng tất cả motor: PWM = 0, DIR = RESET (coast) */
void motor_stop_all(void)
{
    uint8_t i;
    for (i = 0u; i < 4u; i++) {
        __HAL_TIM_SET_COMPARE(&htim1, motors[i].pwm_channel, 0u);
        HAL_GPIO_WritePin(motors[i].dir_port, motors[i].dir_pin, GPIO_PIN_RESET);
    }
}

/* Phanh tất cả motor: DIR = SET + PWM = 100%
 * **Lưu ý:** với sơ đồ PWM+DIR, đây thực chất là chạy lùi hết ga,
 * không phải phanh thật. Chỉ dùng khi chắc chắn. */
void motor_brake_all(void)
{
    uint8_t i;
    for (i = 0u; i < 4u; i++) {
        HAL_GPIO_WritePin(motors[i].dir_port, motors[i].dir_pin, GPIO_PIN_SET);
        __HAL_TIM_SET_COMPARE(&htim1, motors[i].pwm_channel, PWM_TIM_ARR);
    }
}